# Dynamic Registration Architecture

このドキュメントは、このリポジトリで次の条件を同時に満たすための構成をまとめたものです。

- アプリ自体は Google OAuth を外部 provider として使う
- 独自の remote MCP server を持つ
- 自前の application server を OAuth Authorization Server 兼用にする
- Claude Desktop のような外部 MCP client から使えるように dynamic client registration を実装する

## 1. 背景

このアプリには OAuth が 2 種類あります。

1. 外部 provider 向け OAuth
- 例: Google Calendar credential 接続
- application server が Google の authorization server に対して client として振る舞う

2. MCP client 向け OAuth
- 例: Claude Desktop がこのアプリの MCP server を使うための認可
- application server 自身が authorization server として振る舞う

この 2 つは役割がまったく違うので、同じ「OAuth」でも責務を分けて扱う必要があります。

## 2. 全体アーキテクチャ

```
Claude Desktop / External MCP Client
    -> discover metadata
    -> dynamic client registration
    -> browser login + authorization
    -> token / refresh token
    -> bearer auth
    -> MCP Server
    -> App Server backend API
    -> Google Calendar API

In-app Chat Client
    -> internal JWT issuance
    -> bearer auth
    -> MCP Server
    -> App Server backend API
    -> Google Calendar API

Admin User
    -> Google Sign-In
    -> App Server session
    -> credential management / authorization approval
```

要点は以下です。

- `app_server` は 3 つの役割を持つ
  - Admin UI / Chat UI
  - Google など外部 provider 連携の client
  - MCP client 向け OAuth Authorization Server
- `mcp_server` は薄い router に徹する
- bearer token の検証は `app_server` に集約する
- Claude Desktop と app 内 chat は同じ MCP tool surface を使う
- ただし token を得る経路は別でよい

## 3. Application Server の責務

`app_server` の責務は次の通りです。

### 3.1 Admin UI とログイン

- Google Sign-In で admin をログインさせる
- `admin_sessions` を発行して cookie に保存する
- `/credentials` と `/chat` を保護する

### 3.2 外部 provider OAuth client

- Google Calendar などの外部 provider に対して OAuth client として動く
- authorization code を token に交換する
- provider access token / refresh token を保存する
- provider access token の refresh を自動で行う

### 3.3 MCP 向け Authorization Server

- metadata endpoint を公開する
- dynamic client registration を受け付ける
- authorization code を発行する
- access token / refresh token を発行する
- refresh token rotation を行う

### 3.4 Backend API 実行と JWT 検証

- MCP server から渡された bearer token を検証する
- token が有効なら対象の provider 実行を行う
- provider-specific API 実行は application server 側に集約する

## 4. 必要なエンドポイント

この構成で必要になる endpoint は次の 4 系統です。

### 4.1 Admin login

- `GET /auth/login`
- `GET /auth/google/callback`
- `POST /auth/logout`

目的:

- admin login と app session の確立

### 4.2 外部 provider OAuth

- `POST /credentials/{credential_id}/oauth/start`
- `GET /oauth/{provider}/callback`

目的:

- Google Calendar など外部 provider credential の接続

### 4.3 Authorization Server endpoints

- `GET /.well-known/oauth-authorization-server`
- `POST /oauth/register`
- `GET /oauth/authorize`
- `POST /auth/token`

役割:

- metadata discovery
- dynamic client registration
- authorization code issuance
- `client_credentials`
- `authorization_code`
- `refresh_token`

注意:

- refresh 専用の別 URL は不要
- `POST /auth/token` の `grant_type=refresh_token` で扱う

### 4.4 Backend API endpoints

- `GET /api/google_calendar/{credential_id}/list_calendars`
- `GET /api/google_calendar/{credential_id}/list_events`
- `POST /api/google_calendar/{credential_id}/create_event`
- 他の provider execution endpoints

目的:

- bearer token を検証した上で provider 実行を受ける

## 5. DB と必要なテーブル

この構成で必要なテーブルは、役割ごとに次のように整理できます。

### 5.1 Admin login

- `admin_sessions`

用途:

- Google Sign-In 後の app session を保持する

### 5.2 外部 provider credential 管理

- `credentials`
- `oauth_tokens`
- `oauth_states`

用途:

- provider credential のメタデータ
- provider access token / refresh token
- provider OAuth 開始時の state

### 5.3 MCP Authorization Server

- `oauth_clients`
- `oauth_authorization_codes`
- `oauth_refresh_tokens`

用途:

- dynamic registration された client の保存
- authorization code の一時保存
- MCP client 向け refresh token の保存

最低限のカラム例:

`oauth_clients`
- `client_id`
- `client_secret`
- `client_name`
- `redirect_uris_json`
- `grant_types_json`
- `response_types_json`
- `scope`
- `token_endpoint_auth_method`
- `created_at`
- `updated_at`

`oauth_authorization_codes`
- `code`
- `client_id`
- `redirect_uri`
- `subject`
- `scope`
- `expires_at`
- `created_at`

`oauth_refresh_tokens`
- `refresh_token`
- `client_id`
- `subject`
- `scope`
- `expires_at`
- `created_at`

### 5.4 Chat UI

- `chat_rooms`
- `chat_room_providers`
- `chat_messages`

用途:

- app 内 chat の room 設定と履歴保持

## 6. MCP Server 側で必要な変更

この構成での `mcp_server` のポイントは、「OAuth server にはならない」ことです。

`mcp_server` の責務:

- tool surface を公開する
- incoming bearer token を受け取る
- bearer token を `app_server` に転送する
- provider ロジックや token 検証は持たない

### 6.1 必要な変更

1. tool 引数に認証情報を含めない
- 認証情報を各 tool 引数に持たせる設計は避ける
- Claude Desktop のような外部 MCP client では、接続自体の認証として扱う方が自然
- 認証は MCP connection レベルで扱い、tool schema は業務引数だけにする

2. request context から接続時の認証情報を取得する
- HTTP transport の場合は `Authorization: Bearer ...` を MCP request context から読む
- 取得した認証情報をそのまま `app_server` backend API に付けて転送する

3. 認証情報の解釈はしない
- `mcp_server` では token の中身を解釈しない
- `mcp_server` は transport-level auth を受け取り、backend に渡すだけにする
- 検証や認可判断は `app_server` に一元化する

4. internal client では `fastmcp.Client` の auth を使う
- application server 内部から MCP を呼ぶ場合は、tool 引数に認証情報を入れない
- `fastmcp.Client(..., auth=...)` を使って接続単位で認証を付与する
- これにより internal client と external client で MCP tool interface を共通化できる

5. 未認証では tool discovery も通さない
- hosted MCP として使う場合、`tools/list` も含めて未認証 request は拒否する
- つまり `mcp_server` では connection-level auth を有効にし、未認証の段階で `401` にする
- Notion のような hosted MCP と同じく、「認証後に tools が見える」モデルに寄せる

### 6.2 token 取り回しの原則

- `mcp_server` は token を発行しない
- `mcp_server` は token を永続化しない
- `mcp_server` は token を bearer header として転送するだけ

この構成にすると、認証ロジックが分散しません。

## 7. Application Server 内部からの呼び出しと外部からの呼び出し

この構成では、内部呼び出しと外部呼び出しは「同じ部分」と「違ってよい部分」があります。

## 7.1 同じであるべき部分

- 同じ MCP endpoint を使う
- 同じ MCP tool names を使う
- 同じ tool arguments を使う
- 同じ bearer auth モデルで `mcp_server -> app_server` に渡る

つまり、MCP の外向き interface は共通であるべきです。

## 7.2 異なってよい部分

- token を取得するまでの経路

### 外部 client

例: Claude Desktop

- metadata discovery
- dynamic registration
- authorization code flow
- refresh token flow
- bearer auth で MCP 接続

### 内部 client

例: app 内 chat

- application server 内で短命 JWT を直接発行
- `fastmcp.Client(..., auth=<jwt>)` で MCP 接続

この内部 shortcut は許容できます。理由は:

- 同じアプリケーション内部の trusted client だから
- MCP interface 自体は外部 client と共通だから
- 複雑な self-registration を app 内 chat にまで要求しなくてよいから

## 7.3 なぜ共存できるか

共存できる理由は、MCP server が「接続時 bearer token を backend に流すだけ」だからです。

- app 内 chat も bearer token を持つ
- Claude Desktop も bearer token を持つ
- bearer token の発行経路は違っても、MCP server から見れば同じ

したがって:

- internal client path と external client path は共存できる
- registration の有無が違っても MCP tool interface は同じでよい

## 8. なぜ application server を Authorization Server 兼用にするのか

この構成の利点は次の通りです。

1. admin login と authorization approval を同じ session で扱える
- Google Sign-In した admin がそのまま authorization を承認できる

2. backend API の JWT 検証を一元化できる
- token 発行主体と token 検証主体が同じ

3. credential 管理と auth 管理が同じ DB に乗る
- provider tokens
- OAuth clients
- authorization codes
- refresh tokens

4. `mcp_server` を薄く保てる
- 認証ロジックの複雑さを背負わせない

## 9. 実装上の注意点

### 9.1 外部 provider OAuth と混同しない

- Google Calendar 用の refresh token
- MCP client 用の refresh token

これは別物です。保存先も用途も異なります。

### 9.2 refresh token は rotate する

- `refresh_token` grant で使われた token は失効させる
- 新しい refresh token を返す

### 9.3 internal shortcut は残してよい

app 内 chat まで dynamic registration に揃える必要はありません。

必要なのは:

- MCP interface の共通化
- bearer auth モデルの共通化

token 取得経路まで完全統一する必要はありません。

## 10. この構成でのまとめ

このアプリでは:

- application server が Google OAuth client でもあり
- 同時に MCP client 向け Authorization Server でもある
- MCP server は bearer token を転送する薄い router である
- Claude Desktop は dynamic registration 経由で使う
- app 内 chat は internal shortcut で使う

この分離により、外部公開用の正しい OAuth フローを保ちつつ、内部統合は過剰に複雑化させずに運用できます。
