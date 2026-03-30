# アーキテクチャ（実装済み）

このドキュメントは **現時点で実装されている構成** のみを説明します（将来設計は含めません）。

## 全体像（ASCII）

```
                 ┌──────────────────────────────┐
                 │        LLM Client UI         │
                 │  (チャットルーム + プロンプト) │
                 └──────────────┬───────────────┘
                                │ HTTP
                                ▼
                      ┌───────────────────┐
                      │    App Server     │  FastAPI
                      │  - Admin UI       │
                      │  - Google Sign-In │
                      │  - OAuth AS       │
                      │  - JWT発行        │
                      │  - Gemini呼び出し │
                      │  - Provider API   │
                      └───────┬─────┬─────┘
                              │     │
                              │     │ HTTP (JWT)
                              │     ▼
                              │  ┌───────────────────┐
                              │  │   MCP Server      │  fastmcp (HTTP)
                              │  │  - gcal.* tools   │
                              │  └───────────────────┘
                              │
                              ▼
                     ┌────────────────────┐
                     │   SQLite (App)     │
                     │ credentials        │
                     │ oauth_tokens       │
                     │ oauth_clients      │
                     │ oauth_authorization_codes │
                     │ oauth_states       │
                     │ admin_sessions     │
                     │ chat_rooms         │
                     │ chat_room_providers│
                     │ chat_messages      │
                     └────────────────────┘
```

## コンポーネントの役割

### App Server (FastAPI)
- **認証・実行の中心**。
- Admin UI + Chat UI を提供。
- OAuth トークンと Integration credential を管理。
- MCPクライアント向け OAuth Authorization Server も兼ねる。
- MCP 呼び出しに使う短命 JWT を発行。
- Gemini (LLM) と Provider API を実行。

### MCP Server (fastmcp)
- **薄いルーター**。
- ツール面を LLM に公開。
- 実処理は App Server に JWT 付きで委譲（Provider ロジックは持たない）。

### SQLite (App DB)
- credential / token / chat 履歴の **単一ソース**。

## セキュリティ

### Admin UI 認証
- Google Sign-In でログイン。
- セッションは `admin_sessions` に保存、cookie で保持。
- 未ログインは `/auth/login` にリダイレクト。

### OAuth Authorization Server
- App Server は MCP クライアント向けに以下を提供する。
  - metadata: `/.well-known/oauth-authorization-server`
  - dynamic registration: `/oauth/register`
  - authorization: `/oauth/authorize`
  - token: `/auth/token`

### Protected Resource Metadata
- MCP Server は protected resource server として振る舞う。
- そのため token 検証だけでなく、「どの authorization server を使うべきか」を返す metadata も公開する必要がある。
- 外部 MCP client はこの metadata を見て OAuth flow を開始する。

### JWT 発行
- App Server が短命 JWT を発行する。
- 署名は `JWT_SECRET`、発行者は `JWT_ISSUER`。

### JWT の適用
- App Server の backend API は **JWT 必須**。
- MCP サーバーは MCP の HTTP bearer auth を受け取り、そのまま App Server に転送する。
- **JWT 検証は App Server に集約**し、MCP は薄く保つ。

## Integration の認証情報管理

### OAuth フロー（Google Calendar）
1. Admin が credential を作成し OAuth を開始。
2. App Server が認可コードをトークンに交換。
3. access / refresh token を DB に保存し status を connected に更新。

### トークン保存とリフレッシュ
- `oauth_tokens` に `access_token / refresh_token / expiry` を保存。
- API 実行時、期限切れなら refresh を行い DB を更新。
- refresh に失敗したら再接続が必要。

### Gemini API キー
- Gemini credential の詳細画面で登録。
- DB に保存して利用。

## Credential の管理
- Admin UI で credential を作成・接続。
- Google Calendar は OAuth、Gemini は API キー。
- Chat ルーム単位で **1つの LLM credential** と **0..N の MCP provider** を選択。

### 外部 MCP client からの credential 解決
- 現在のローカル実装では、外部 MCP client から provider tool を呼ぶとき `credential_id` を明示的に渡している。
- これはローカル検証用の簡易実装であり、本番の外部向け interface としては不十分。
- 本番実装では、外部 client は `credential_id` を知るべきではない。
- 代わりに access token / JWT から user identity を取り出し、そのユーザーに紐づく default credential を application server 側で解決する必要がある。
- つまり provider 実行時の credential 選択は、room 文脈ではなく auth 文脈から行う。
- 将来的には、user ごとに provider 単位の default credential を持てる構造が必要になる。

## 実行フロー（チャット）
1. ユーザーがルームでプロンプトを送信。
2. App Server が選択済み MCP provider のツールスキーマを生成。
3. Gemini が tool calling で実行するツールを選択。
4. App Server 内の MCP client が bearer auth 付きで MCP Server を呼ぶ。
5. MCP がツール実行を App Server に委譲。
6. 結果を Gemini に渡して最終回答を生成。
7. メッセージは DB に保存。

## 実行フロー（Claude Desktop などの外部 MCP client）
1. 外部 client が MCP Server の protected resource metadata を発見する。
2. MCP Server が利用すべき authorization server として App Server を返す。
3. 外部 client が App Server の metadata endpoint を発見する。
4. 外部 client が dynamic client registration を行う。
5. ユーザーは Google Sign-In で admin login を行う。
6. App Server が authorization code を発行する。
7. 外部 client が token endpoint で access token / refresh token を取得する。
8. 外部 client が bearer auth 付きで MCP Server を呼ぶ。
9. MCP Server は受けた token を App Server backend API に転送する。
10. App Server が JWT を検証し、token の subject から user identity を特定する。
11. App Server がその user に紐づく default credential を解決する。
12. App Server が Provider API を実行する。

## MCP → App Server 集中の理由
- 認証・検証ロジックの **分散を防ぐ**。
- Provider 実行を一箇所に集約し、保守性を向上。
- 監査ログやレート制御を **集中管理**できる。
- MCP を薄いまま拡張できる。

## ツール選択の制御（ルーム単位）
- MCP サーバーは複数ツールを持つが、**ルーム設定で必要な統合だけ**を LLM に渡す。
- これにより、冗長な「全ツール提示」や不要な権限付与を避けられる。
- ワークフロー拡張時も「同一MCP内のツール群から必要なものだけ選択」が可能。

## 既存のリモートMCPサーバーを追加する方法
- リモートMCPの **エンドポイントURL** と **認証トークン** をDBに保存する。
- ルーム作成時に「使いたいMCPプロバイダ」を選ぶと、そのURL/トークンを使って呼び出す。
- Geminiに渡すツールは、選択されたMCPサーバーのものだけに限定する。

### 例: Notion MCP
- Notionの管理画面で発行したトークンを **Bearer** ヘッダに付与してアクセスする方式。
- DBに `notion_mcp_url` と `notion_mcp_token` を保存。
- ルームで Notion を選択した場合、Geminiには Notion MCP のツール群だけを渡す。
- 実行時は App Server が Notion MCP にリクエストを中継する。

## 設定ファイル
- App Server: `app_server/.env`
- MCP Server: `mcp_server/.env`
