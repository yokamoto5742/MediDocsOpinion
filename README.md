# 主治医意見書作成アプリ

このアプリケーションは、生成AIを活用して主治医意見書を効率的に作成するためのFastAPIベースのWebアプリケーションです。Claude（AWS Bedrock）とGemini（Google Vertex AI）の両方のAIプロバイダーに対応し、自動モデル切り替え機能で最適なパフォーマンスを実現します。

## 機能

### コア機能
- **複数のAIプロバイダーサポート**: Claude（AWS Bedrock経由）とGemini（Vertex AI経由）に統合
- **自動モデル切り替え**: 入力文字数が指定の閾値を超えた場合、Claudeから自動的にGeminiに切り替え
- **構造化文書生成**: 標準化されたセクションで医療文書を生成

### 文書管理
- **複数の文書タイプ**: 主治医意見書、訪問看護指示書
- **診療科別カスタマイズ**: 診療科ベースの設定に対応
- **医師別プロンプト**: 階層的プロンプトシステム（医師 → 診療科 → 文書タイプ）

### プロンプト管理
- **カスタムプロンプトテンプレート**: さまざまなシナリオ用のカスタムプロンプト作成・管理
- **階層的継承**: 診療科と医師ごとのプロンプトカスタマイズ
- **Webベース UI**: プロンプトの作成と編集のための使いやすいインターフェース

### 評価と分析
- **AI出力評価**: 生成された文書の品質をLLMで評価
- **使用統計**: API使用状況、トークン数、作成時間を追跡
- **パフォーマンスメトリクス**: レスポンス時間とモデル別パフォーマンス監視
- **日次利用制限**: リクエスト数、入力トークン、出力トークンの日次制限機能

### フロントエンド
- **Vite + TypeScript**: モダンなビルド環境と型安全性
- **Tailwind CSS**: ユーティリティファーストなスタイリング
- **Alpine.js**: 軽量なJavaScript フレームワーク

### セキュリティ
- **CSRF保護**: トークンベースの状態変更エンドポイント保護
- **プロンプトインジェクション対策**: 多層的な入力検証とサニタイゼーション
- **CORS制御**: 環境変数ベースの柔軟なクロスオリジン設定
- **セキュリティヘッダー**: XSS、クリックジャッキング、MIME スニッフィング対策
- **監査ログ**: 医療操作のセキュリティイベント記録

## 前提条件

- **Python** 3.13以上
- **PostgreSQL** 16以上
- **Node.js** 18以上（フロントエンド開発用）
- **AI APIアカウント**（以下のうち少なくとも1つ）:
  - AWS Bedrockアクセス権限（Claude API用）
  - Google Cloud PlatformアカウントにVertex AI有効化（Gemini API用）

## インストール

### 1. リポジトリのクローン
```bash
git clone <repository-url>
cd MediDocsOpinion
```

### 2\. 仮想環境の作成と有効化

 `uv` を使用して依存関係を管理します。

```bash
uv venv
# Windows
.venv\Scripts\activate
```

### 3\. Pythonの依存関係をインストール

`pyproject.toml` に定義された依存関係をインストールします。

```bash
uv sync
```

### 4. PostgreSQLデータベースのセットアップ
```bash
# データベースの作成
createdb medidocs

# テーブルは初回実行時にSQLAlchemyを介して自動作成されます
```

### 5. 環境変数の設定
プロジェクトルートに`.env`ファイルを作成します。詳細は「環境変数の設定」セクションを参照。

環境変数は以下の優先順位で読み込まれます：
1. OS環境変数（既存の値は上書きされない）
2. AWS Secrets Manager（`AWS_SECRET_NAME`で指定、デフォルト: `medidocs/prod`）
3. `.env`ファイル

## 環境変数の設定

`.env`ファイルにおける主要な設定項目です。

### データベース設定
```env
# PostgreSQL接続情報
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=medidocs
POSTGRES_SSL=false

# コネクションプール設定
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800

# または、DATABASE_URL（オプション、個別設定を上書き）
DATABASE_URL=postgresql://user:password@host:port/database
```

### Claude API設定(AWS Bedrock)
```env
# ローカル開発環境（アクセスキーを使用する場合）
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=ap-northeast-1
ANTHROPIC_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0

# EC2/ECS環境（IAMロール自動検出を使用する場合、上記は不要）
```

### Google Vertex AI設定
```env
# Google Cloud認証情報（JSON形式）
GOOGLE_CREDENTIALS_JSON={"type":"service_account","project_id":"your-project",...}

# Vertex AI設定
GOOGLE_PROJECT_ID=your-gcp-project-id
GOOGLE_LOCATION=global
GEMINI_MODEL=gemini-2.0-flash
GEMINI_EVALUATION_MODEL=gemini-2.0-flash
GEMINI_THINKING_LEVEL=HIGH
```

### アプリケーション設定
```env
# トークン制限
MAX_INPUT_TOKENS=200000
MIN_INPUT_TOKENS=100
MAX_TOKEN_THRESHOLD=100000

# 機能設定
PROMPT_MANAGEMENT=true
APP_TYPE=default
SELECTED_AI_MODEL=Claude

# CSRF認証
CSRF_SECRET_KEY=your_secret_key
CSRF_TOKEN_EXPIRE_MINUTES=60

# CORS設定
CORS_ORIGINS=["http://localhost:8000","http://127.0.0.1:8000"]

# 日次利用制限
DAILY_REQUEST_LIMIT=100
DAILY_INPUT_TOKEN_LIMIT=5000000
DAILY_OUTPUT_TOKEN_LIMIT=100000

# AWS Secrets Manager（オプション）
AWS_SECRET_NAME=medidocs/prod
```

## 使用方法

### バックエンドの起動

**開発モード:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**本番モード:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Webインターフェースの使用

1. **メインページへのアクセス**: `http://localhost:8000` にアクセス
2. **患者情報の入力**:
   - 診療科と医師を選択
   - 文書タイプを選択
   - テキストエリアにカルテデータを入力
   - 追加情報を入力
3. **AIモデルの選択**: ClaudeまたはGeminiを選択（または自動切り替え）
4. **文書の生成**: 生成ボタンをクリック
5. **出力結果の確認**: 生成された文書が構造化されたセクションで表示

### プロンプトの管理

1. **Prompts** ページにアクセス
2. **新規プロンプトの作成**:
   - 診療科、医師、文書タイプを選択
   - カスタムプロンプトテンプレートを入力
   - プロンプトを保存
3. **既存プロンプトの編集・削除**: 各プロンプトの横のアイコンをクリック

### 統計の表示

1. **Statistics** ページにアクセス
2. 統計用の日付範囲を選択
3. メトリクスを表示:
   - 合計API呼び出し数
   - モデル別トークン使用量
   - 平均作成時間

### 出力評価

1. **Evaluation** ページにアクセス
2. 生成された文書テキストを入力
3. 評価対象の文書タイプを選択
4. **評価実行** をクリック
5. AIによる評価結果（改善提案など）を確認

## プロジェクト構造

```
app/
├── api/                    # FastAPI ルートハンドラー
│   ├── router.py          # メイン API ルーター
│   ├── summary.py         # 文書生成エンドポイント
│   ├── prompts.py         # プロンプト管理エンドポイント
│   ├── evaluation.py      # 出力評価エンドポイント
│   ├── statistics.py      # 統計エンドポイント
│   └── settings.py        # 設定エンドポイント
├── core/                  # コア設定
│   ├── config.py          # 環境設定（Settings クラス）
│   ├── constants.py       # アプリケーション定数
│   ├── database.py        # データベース接続
│   └── security.py        # API認証
├── external/              # 外部 API 連携
│   ├── api_factory.py     # APIクライアント動的生成関数
│   ├── base_api.py        # ベースAPIクライアント
│   ├── claude_api.py      # Claude/Bedrock連携
│   └── gemini_api.py      # Gemini/Vertex AI連携
├── models/                # SQLAlchemy ORM モデル
│   ├── base.py            # ベースモデル
│   ├── prompt.py          # プロンプトテンプレート
│   ├── evaluation_prompt.py      # 評価プロンプト
│   ├── usage.py           # 利用統計
│   └── setting.py         # アプリケーション設定
├── schemas/               # Pydantic スキーマ
│   ├── summary.py         # 文書生成リクエスト/レスポンス
│   ├── prompt.py          # プロンプトスキーマ
│   ├── evaluation.py      # 評価スキーマ
│   └── statistics.py      # 統計スキーマ
├── services/              # ビジネスロジック
│   ├── summary_service.py           # 文書生成ロジック
│   ├── prompt_service.py            # プロンプト管理
│   ├── evaluation_prompt_service.py # 評価プロンプト管理
│   ├── evaluation_service.py        # 出力評価
│   ├── statistics_service.py        # 統計処理
│   ├── usage_service.py             # 使用統計サービス
│   ├── model_selector.py            # モデル選択ロジック
│   └── sse_helpers.py               # Server-Sent Events ヘルパー
├── utils/                 # ユーティリティ関数
│   ├── text_processor.py       # テキスト解析
│   ├── exceptions.py           # カスタム例外
│   ├── error_handlers.py       # エラーハンドリング
│   ├── input_sanitizer.py      # プロンプトインジェクション検出とサニタイゼーション
│   └── audit_logger.py         # セキュリティ監査ログ
├── templates/             # Jinja2 テンプレート
├── static/                # 静的ファイル（フロントエンド出力）
└── main.py                # FastAPI アプリケーション本体

frontend/                  # フロントエンド（Vite + TypeScript + Tailwind CSS）
├── src/
│   ├── main.ts           # エントリーポイント
│   ├── app.ts            # Alpine.js アプリケーションロジック
│   ├── types.ts          # 型定義
│   └── styles/
│       └── main.css      # Tailwind CSS + カスタムスタイル
└── DEVELOPMENT.md        # フロントエンド開発ガイド

tests/                    # テストスイート
├── conftest.py          # 共有フィクスチャ
├── api/                 # APIエンドポイントテスト
├── core/                # コア機能テスト
├── external/            # 外部APIテスト
├── services/            # ビジネスロジックテスト
└── test_utils/          # ユーティリティテスト
```

## アーキテクチャと設計パターン

### Factory Pattern
APIプロバイダー（Claude/Gemini）の動的インスタンス化を管理する関数を提供します：

```python
from app.external.api_factory import create_client, APIProvider

client = create_client(APIProvider.CLAUDE)
result = client.generate_summary(medical_text, additional_info, ...)
```

### Service Layer Pattern
ビジネスロジックはAPIルートから分離されています：

- `summary_service.py`: 文書生成とモデル選択ロジック
- `prompt_service.py`: プロンプト管理と階層的解決
- `evaluation_service.py`: 出力評価
- `statistics_service.py`: 統計処理

### 自動モデル切り替え

`model_selector.py`で実装：

- `determine_model()`: 入力文字数とDB設定から最適なモデルを決定
  - `model_explicitly_selected=False`の場合、DBから医師/診療科/文書タイプ別のモデル設定を取得
  - 入力が`MAX_TOKEN_THRESHOLD`（デフォルト100,000文字）を超え、Claudeが選択されている場合、自動的にGeminiに切り替え
  - Geminiが設定されていない場合はエラーを返す
- `get_provider_and_model()`: モデル名からプロバイダーとモデルのIDを取得
- 閾値は環境変数`MAX_TOKEN_THRESHOLD`で調整可能

### 階層的プロンプトシステム

プロンプトは以下の順序で解決されます（`prompt_service.get_prompt()`内）：

1. 診療科 + 医師 + 文書タイプ固有のプロンプト
2. 診療科 + デフォルト医師 + 文書タイプ固有のプロンプト
3. デフォルト診療科 + デフォルト医師 + 文書タイプのデフォルトプロンプト
4. DBにない場合は`DEFAULT_SUMMARY_PROMPT`定数を使用

これにより、診療科別・医師別のカスタマイズが可能です。

### 定数管理

`app/core/constants.py`で定数を一元管理：

- `ModelType` Enum: "Claude"、"Gemini_Pro"などのモデル名
- `APIProvider` Enum: CLAUDE、GEMINI
- 診療科・医師マッピング
- 文書タイプ
- ユーザー向けメッセージ（日本語）

マジック文字列を避け、必ず定数を使用してください。

### APIクライアント

**インスタンス化**:

- `api_factory.create_client(APIProvider)` で適切なクライアントを動的に生成
-  GeminiAPIClient/ClaudeAPIClient を使用

### データフロー

1. ユーザーがWebインターフェースからカルテデータを入力
2. FastAPIエンドポイントが入力を受信・検証
3. `SummaryService` が文書生成を調整
4. Factoryパターンが適切なAPIクライアントをインスタンス化
5. 入力文字数に基づいてモデルを自動選択
6. AIが構造化された医療文書を生成
7. テキストプロセッサーが出力をセクションに解析
8. 使用統計（トークン数、作成時間、コスト）をPostgreSQLに保存
9. 構造化された文書をユーザーインターフェースに返却

## テスト

### テストの実行

**すべてのテストを実行:**
```bash
python -m pytest tests/ -v --tb=short
```

**カバレッジ付きで実行:**
```bash
python -m pytest tests/ -v --tb=short --cov=app --cov-report=html
```

**特定のテストファイルを実行:**
```bash
python -m pytest tests/services/test_summary_service.py -v
```

**特定のテストを実行:**
```bash
python -m pytest tests/services/test_summary_service.py::test_generate_summary -v
```

### テスト構造

本プロジェクトは300 個以上のテストで包括的なテストカバレッジを維持：

- **API統合テスト**: エンドポイントとリクエスト/レスポンス
- **ビジネスロジック**: サービスレイヤーのユニットテスト
- **外部API**: モック使用によるプロバイダー統合テスト
- **データベース**: 操作とORM機能
- **ユーティリティ**: テキスト処理とエラーハンドリング

新機能追加時は以下の順序でテストを追加してください：

1. サービスレイヤーテスト（TDD推奨）
2. API統合テスト
3. 必要に応じて外部APIテスト（pytest-mockでモック）

## データベースマイグレーション

Alembicを使用してデータベーススキーマを管理します：

**新しいマイグレーション作成:**
```bash
alembic revision --autogenerate -m "説明"
```

**マイグレーション実行:**
```bash
alembic upgrade head
```

**マイグレーションを戻す:**
```bash
alembic downgrade -1
```

テーブルは初回実行時にSQLAlchemyを介して自動作成されます。

## フロントエンド開発

フロントエンド開発の詳細については、[frontend/DEVELOPMENT.md](frontend/DEVELOPMENT.md)を参照してください。

**開発サーバー開始:**
```bash
cd frontend
npm install
npm run dev
```

## 型チェック

```bash
# 型チェック実行（app/のみ対象、tests/と scripts/は除外）
pyright
```

## 使用技術

### バックエンド
- **FastAPI**: 高速で最新的なPython Webフレームワーク
- **Uvicorn**: ASGI Webサーバー
- **Pydantic v2**: データ検証
- **SQLAlchemy**: ORM
- **PostgreSQL**: リレーショナルデータベース
- **Alembic**: データベーススキーマ管理

### AI/ML統合
- **AWS Bedrock**: Claude API へのアクセス
- **Google Vertex AI**: Gemini API への統合

### フロントエンド
- **Vite**: 高速フロントエンドビルドツール
- **TypeScript**: 型安全なJavaScript
- **Tailwind CSS**: ユーティリティファーストCSSフレームワーク
- **Alpine.js**: 軽量なJavaScript フレームワーク
- **Jinja2**: サーバーサイドテンプレートエンジン

### 開発ツール
- **pytest**: テストフレームワーク
- **pytest-cov**: カバレッジレポート
- **pytest-mock**: モックライブラリ
- **pyright**: Python静的型チェッカー
- **python-dotenv**: 環境変数管理

## トラブルシューティング

### データベース接続エラー
- PostgreSQLが起動しているか確認
- `DATABASE_URL`または個別の`POSTGRES_*`変数が正しいか確認
- ユーザー名とパスワードを確認

### AI APIエラー
- **Claude API エラー**:
  - AWS Secrets Managerの設定確認（ローカル開発の場合）
  - IAMロール権限確認（EC2/ECS環境）
  - `ANTHROPIC_MODEL`環境変数の設定確認
- **Gemini API エラー**:
  - Google Cloud プロジェクト ID と認証情報が正しいか確認
  - `GEMINI_EVALUATION_MODEL`環境変数が設定されているか確認
  - Vertex AIが有効化されているか確認

### テスト失敗
- `.env.test`ファイルが正しく設定されているか確認
- データベースマイグレーションが完了しているか確認
- 外部API呼び出しがモックされているか確認

### セキュリティ関連エラー

**プロンプトインジェクション検出エラー**
- 医療テキストに特定のキーワード（指示、命令など）が含まれた場合、誤検出の可能性
- `app/utils/input_sanitizer.py`の検出パターンを確認してカスタマイズ可能

**CSRF トークン検証失敗**
- トークンの有効期限を確認（デフォルト60分）
- `X-CSRF-Token`ヘッダーが正しく送信されているか確認
- `CSRF_SECRET_KEY`が同じ値に設定されているか確認

**CORS エラー**
- `CORS_ORIGINS`に現在のホストが含まれているか確認
- ブラウザのデバッグツールでネットワークエラーを確認

### 利用制限エラー

**日次リクエスト制限超過**
- エラーメッセージ：「本日のリクエスト回数制限（N回）を超過しました。明日再度お試しください」
- `DAILY_REQUEST_LIMIT`環境変数を確認（デフォルト100回）
- 制限値を増やす場合は`.env`ファイルを編集

**日次入力トークン制限超過**
- エラーメッセージ：「本日の入力トークン制限（N トークン）を超過しました。明日再度お試しください」
- `DAILY_INPUT_TOKEN_LIMIT`環境変数を確認（デフォルト5,000,000トークン）

**日次出力トークン制限超過**
- エラーメッセージ：「本日の出力トークン制限（N トークン）を超過しました。明日再度お試しください」
- `DAILY_OUTPUT_TOKEN_LIMIT`環境変数を確認（デフォルト100,000トークン）

## コントリビューション

### コードスタイル
- **PEP 8** ガイドラインに従う
- すべての関数に**型ヒント**（パラメータと戻り値）を使用
- インポート順序: 標準ライブラリ → サードパーティ → ローカルモジュール
- 各グループ内でアルファベット順にソート（`import`が先、`from`は後）
- 関数サイズは**50行以下**を目標
- コメントは複雑なロジックのみ日本語で記述（文末に句点不要）

### コミットメッセージ
- 従来のコミット形式を使用：`✨ feat`, `🐛 fix`, `📝 docs`, `♻️ refactor`, `✅ test`
- 変更内容と理由を日本語で記述
- 変更範囲は最小限に

詳細は [CLAUDE.md](CLAUDE.md) を参照してください。

## セキュリティ機能

### CSRF保護

- CSRF トークンは `CSRF_SECRET_KEY` で生成
- トークン有効期限は `CSRF_TOKEN_EXPIRE_MINUTES` で設定（デフォルト60分）
- すべての状態変更エンドポイント（POST/PUT/DELETE）で検証

### CORS設定

以下の環境変数で制御可能：
- `CORS_ORIGINS`: 許可するオリジンのリスト
- `CORS_ALLOW_CREDENTIALS`: クッキー送信の許可(オプション)
- `CORS_ALLOW_METHODS`: 許可するHTTPメソッド(オプション)
- `CORS_ALLOW_HEADERS`: 許可するヘッダー(オプション)

### プロンプトインジェクション対策

入力テキストのサニタイゼーション機能：
- システムプロンプト上書き指示の検出
- ロールプレイング攻撃パターンの検出（英語・日本語両対応）
- 異常な繰り返しパターンの検出
- XSS関連パターンの除去
- 制御文字の除去

**実装:** `app/utils/input_sanitizer.py`

### セキュリティヘッダー

`SecurityHeadersMiddleware`により以下を自動設定：
- `X-Content-Type-Options: nosniff` - MIMEスニッフィング防止
- `X-Frame-Options: DENY` - クリックジャッキング防止
- `X-XSS-Protection: 1; mode=block` - XSS保護
- `Content-Security-Policy` - スクリプト/スタイル実行制御
- `Strict-Transport-Security` - HTTPS強制（HTTPS環境のみ）

### 監査ログ

セキュリティイベントをJSON形式で記録：
- 文書生成操作
- ユーザーIP
- 実行モデルと文書タイプ
- 成功/失敗状態
- 個人情報（PHI）は記録対象外

**実装:** `app/utils/audit_logger.py`

## セキュリティに関する注意事項

- 認証情報を含む`.env`ファイルをコミットしない
- APIキーを定期的にローテーション
- すべての機密設定に環境変数を使用（または AWS Secrets Manager）
- IAMロールの権限は最小限に設定
- セキュリティパッチのために依存関係を最新に保つ
- 本番医療現場で使用する前にAI生成コンテンツを専門家がレビュー
- HTTPS環境では `Strict-Transport-Security` ヘッダーが自動設定される

## 免責事項

このアプリケーションは医療文書作成を支援するツールであり、専門的な医学的判断に代わるものではありません。生成されたすべてのコンテンツは、医療専門家による確認が必須です。

## ライセンス

このプロジェクトは[Apache License 2.0](docs/LICENSE)のもとで公開されています。

## 変更履歴

バージョン履歴と更新については、[CHANGELOG.md](docs/CHANGELOG.md)を参照してください。
