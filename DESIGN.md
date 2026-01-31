# 🧩 Google Calendar / Notion など多プロバイダ統合

# **MCP + App Server Architecture Design Document（Phase1）**

---

# 1. 前提（Assumptions）

* **LLMクライアント（例：Gemini, ChatGPT, Claude Desktop）** が MCP プロトコルでツールを利用する。
* MCP サーバーは **fastmcp** を利用、1つのプロセスが **複数プロバイダ（Google / Notion etc）** を扱う。
* アプリケーションサーバー（App Server）は **FastAPI** を利用し、

  * OAuth 認証
  * Credential 管理
  * Provider-specific API 実行
  * MCP への backend API
    を担う。
* DB は **SQLite (sqlite3 標準ライブラリ)** で十分。
* **UI（管理画面）** は FastAPI + Jinja2 による最小 SSR（静的サイト不要）。
* ユーザー概念はなし（サービス利用者＝管理者1名想定）。
  ただし設計としては「複数 Credential を管理可能」な形にしておく（Dify/n8n準拠）。
* Provider ごとに Credential は複数持てる（一般的な標準に寄せるため）。
* 認証/セキュリティは Phase1 では以下に限定：

  * Admin UI は Dummy OAuth（App Server内蔵の擬似プロバイダ）
  * MCP → App Server は **Bearer JWT（短命トークン）**
* JWT 内に秘密情報（Google Token 等）は入れない。
* JWT はユーザーのログイン時に発行し、LLMクライアントのリクエストに付与される。
  MCP は受け取った JWT をそのまま App Server に中継し、保持しない。
* App Server は Provider-specific 実行ロジックを持ち、MCP は薄いルーター。
* MCP への接続時にも JWT を必須とし、無効なら接続を拒否する。

---

# 2. スコープじゃないこと（Out of Scope）

Phase1では以下は対象外：

* 監査ログ（Audit Logs）
  → 設計のみ、実装は Phase2 以降
* ワークスペース/ユーザー管理（ログイン / ロール / RBAC）
* フロントエンド SPA（React / Vue 等）
* Provider の増設 UI（Phase1 は Google Calendar のみでも可）
* Provider 実行のキャッシュ / レート制御
* マルチテナント（後から対応可能な構造にしつつ実装しない）
* 実際の Gemini API 呼び出しロジック
  → Phase1 で実装する（MCPデモ成立のため）
* セキュリティハードニング（Vault, KMS, HTTPS termination 等）

---

# 3. 機能要件（Functional Requirements）

### FR1. Credential 作成

* 管理UIから Provider（例：Google Calendar, Notion）用の credential を作成できる。

### FR2. OAuth 認証

* OAuth を利用する Provider（Google/Notion等）については、
  認可画面 → code callback → access/refresh token 保存が可能。

### FR3. Credential 一覧 / 詳細

* 全ての登録済み credential を一覧化できる。
* Credential のステータス（connected/draft/error）を確認できる。

### FR4. Provider 実行 API

* MCP サーバー経由で Provider の API を実行できる。

  * Google Calendar: list calendars, list events, create event など
  * Notion: search, read page, create database item 等（Phase2）

### FR5. MCP ツール実行

* MCP サーバーはツール名と引数（credential_id + args）を受け取り、
  App Server に転送し結果を返す。

### FR6. Credential 削除

* Credential を削除し、OAuth情報も完全に削除できる。

### FR7. Token Refresh

* Provider に応じて access token の refresh を App Server が自動処理。

---

# 4. 非機能要件（Non-functional Requirements）

### NFR1. シンプル性 / 運用性

* プロセス構成はシンプル（App Server + MCP Server + SQLite）。
* ローカルでも動く。

### NFR2. セキュリティ

* OAuth callback の state 検証必須
* MCP → App Server の認証は JWT
* Admin UI は Dummy OAuth で最低限保護
* Token は DB に平文保存（Phase1）。後で暗号化に対応。

### NFR3. 拡張性（Provider拡張）

* Provider はプラグインのように追加できる（Google → Notion → Slack）。

### NFR4. 可読性 / メンテ性

* Providerごとに handler を分離（`providers/google_calendar.py`など）

### NFR5. ステートレス性

* MCPサーバーはステートレス。
  すべての実行には credential_id を渡す。

---

# 5. High-level Design（全体アーキテクチャ）

```
            ┌──────────────┐
            │   LLM Client  │
            │ (Gemini etc.) │
            └──────┬───────┘
                   │ MCP Protocol
                   ▼
          ┌─────────────────────┐
          │     MCP Server      │  ← fastmcp
          │ - Tools (multiple)  │
          │ - Thin router       │
          └─────────┬──────────┘
              JWT    │
      HTTP(S)        ▼
 ┌─────────────────────────┐
 │       App Server        │  ← FastAPI
 │ - Credential CRUD       │
 │ - OAuth Handler         │
 │ - Google/Notion Exec    │
 │ - Token Refresh         │
 │ - HTML Admin UI         │
 └─────────┬──────────────┘
         SQLite
 ┌─────────────────────────┐
 │     Credential Store    │
 │ - provider              │
 │ - tokens                │
 │ - refresh tokens        │
 └─────────────────────────┘
```

## 設計思想

* **MCPは薄く、App Serverにロジック集中**
* **Providerはプラグイン化**
* Credentialは **Provider × N** の一般化構造
* LLMは毎回 `credential_id` を指定してツール実行（Dify/n8n準拠）

---

# 6. API Design（App Server）

## 6.1 Admin UI（HTML）

```
GET    /               → /credentials へリダイレクト
GET    /credentials    → credential一覧画面
POST   /credentials    → credential作成
GET    /credentials/{credential_id} → 詳細画面
POST   /credentials/{credential_id}/delete → 削除
POST   /credentials/{credential_id}/oauth/start → OAuth開始
GET    /auth/login     → Dummy OAuth へリダイレクト
POST   /auth/logout    → セッション破棄
```

## 6.2 OAuth（Provider-specific）

```
GET  /oauth/{provider}/callback?code=&state=
```

* state 検証
* token 交換
* credential 更新

## 6.3 Dummy OAuth（Admin UI 認証用 / App Server内蔵）

```
GET  /oauth/dummy/authorize?state=&redirect_uri=
POST /oauth/dummy/token
GET  /oauth/dummy/callback?code=&state=
```

* 認可画面は簡易フォーム（メールアドレス入力）
* メールアドレスは任意文字列でOK（検証なし）
* code 発行 → token 交換 → Admin UI セッション確立

## 6.4 Backend API（MCP用 / JWT 認証 required）

```
POST /auth/token
    body: { client_id, client_secret }
    → returns JWT(access_token, expires_in)

GET  /api/{provider}/{credential_id}/list_calendars
GET  /api/{provider}/{credential_id}/list_events
POST /api/{provider}/{credential_id}/create_event
POST /api/{provider}/{credential_id}/search (Notion)
...
```

### Payload（例）

```
POST /api/google_calendar/{credential_id}/create_event
{
  "title": "Meeting",
  "start": "...",
  "end": "...",
  ...
}
```

App Server 内部で：

* credential_id に紐づく token を取得
* refresh が必要なら実施
* Provider-specific API を実行
* 結果を返す

---

# 7. DB Design（SQLite / Phase1最小）

## 7.1 credentials

```
credentials (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,             -- google_calendar, notion...
    name TEXT NOT NULL,                 -- admin UI向けラベル
    status TEXT NOT NULL,               -- draft/connected/error
    client_id TEXT,                     -- optional (Notion workspaceなど)
    created_at INTEGER,
    updated_at INTEGER
)
```

## 7.2 oauth_tokens

```
oauth_tokens (
    credential_id TEXT PRIMARY KEY,
    access_token TEXT,
    refresh_token TEXT,
    expiry INTEGER,
    scope TEXT,
    token_type TEXT,
    extra_json TEXT,                    -- provider拡張用
    updated_at INTEGER,
    FOREIGN KEY(credential_id) REFERENCES credentials(id)
)
```

## 7.3 oauth_states

```
oauth_states (
    state TEXT PRIMARY KEY,
    credential_id TEXT,
    expires_at INTEGER,
    FOREIGN KEY (credential_id) REFERENCES credentials(id)
)
```

※ Phase1はこれで十分。
※ audit_logs は Phase2 で追加。

---

# 8. Phases（開発フェーズ）

## Phase 1（MVP / ローカル動作）

* App Server（FastAPI）

  * Credential CRUD（HTML）
  * Admin UI 認証（Dummy OAuth）
  * OAuth 開始/コールバック（Google Calendar）
  * Token refresh
  * Provider executor（Google Calendarのみ）
  * JWT発行（client credentials）
* MCP Server（fastmcp）

  * gcal.* ツール実装
  * App ServerにJWTでアクセス
* Gemini API 呼び出し（最小の実装）
* SQLite スキーマ作成（自動）
* UI（Jinja2）

  * Credential一覧・作成・接続・削除

**ゴール**：
LLM（Gemini）が MCP 経由で Google Calendar イベントを取得できる。

---

## Phase 2（Provider拡張）

* Notion OAuth + executor
* Slack OAuth + executor
* Mapped provider modules
* audit_logs table 実装
* UI改善（Credentialごとのスコープ表示・ログ表示）
* エラー表示/リトライ

---

## Phase 3（LLMエコシステム統合）

* Gemini Gateway（LLM呼び出し）をapp-serverに組み込み
* プロンプトテンプレート
* 複数Credentialの自動選択
* LLMが「credential一覧→選択→実行」できる機能
