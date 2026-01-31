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
                      │  - Dummy OAuth    │
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
- Dummy OAuth でログイン。
- セッションは `admin_sessions` に保存、cookie で保持。
- 未ログインは `/auth/login` にリダイレクト。

### JWT 発行
- App Server が短命 JWT を発行。
- 署名は `JWT_SECRET`、発行者は `JWT_ISSUER`。

### JWT の適用
- App Server の backend API は **JWT 必須**。
- MCP サーバーはツール呼び出し時に JWT を受け取り、そのまま App Server に転送。
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

## 実行フロー（チャット）
1. ユーザーがルームでプロンプトを送信。
2. App Server が選択済み MCP provider のツールスキーマを生成。
3. Gemini が tool calling で実行するツールを選択。
4. MCP がツール実行を App Server に委譲。
5. 結果を Gemini に渡して最終回答を生成。
6. メッセージは DB に保存。

## MCP → App Server 集中の理由
- 認証・検証ロジックの **分散を防ぐ**。
- Provider 実行を一箇所に集約し、保守性を向上。
- 監査ログやレート制御を **集中管理**できる。
- MCP を薄いまま拡張できる。

## 設定ファイル
- App Server: `app_server/.env`
- MCP Server: `mcp_server/.env`
