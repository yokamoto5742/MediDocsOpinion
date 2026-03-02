# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## House Rules:
- 文章ではなくパッチの差分を返す。
- コードの変更範囲は最小限に抑える。
- コードの修正は直接適用する。
- Pythonのコーディング規約はPEP8に従います。
- KISSの原則に従い、できるだけシンプルなコードにします。
- 可読性を優先します。一度読んだだけで理解できるコードが最高のコードです。
- Pythonのコードのimport文は以下の適切な順序に並べ替えてください。
標準ライブラリ
サードパーティライブラリ
カスタムモジュール 
それぞれアルファベット順に並べます。importが先でfromは後です。

## クリーンコードガイドライン
- 関数のサイズ：関数は50行以下に抑えることを目標にしてください。関数の処理が多すぎる場合は、より小さな関数に分割してください。
- 単一責任：各関数とモジュールには明確な目的が1つあるようにします。無関係なロジックをまとめないでください。
- 命名：説明的な名前を使用してください。`tmp` 、`data`、`handleStuff`のような一般的な名前は避けてください。例えば、`doCalc`よりも`calculateInvoiceTotal` の方が適しています。
- DRY原則：コードを重複させないでください。類似のロジックが2箇所に存在する場合は、共有関数にリファクタリングしてください。それぞれに独自の実装が必要な場合はその理由を明確にしてください。
- コメント:分かりにくいロジックについては説明を加えます。説明不要のコードには過剰なコメントはつけないでください。
- コメントとdocstringは必要最小限に日本語で記述します。文末に"。"や"."をつけないでください。
- このアプリのUI画面で表示するメッセージはすべて日本語にします。app/core/constants.pyで一元管理します。

## Overview

診療情報提供書を生成AIで作成するFastAPIベースのWebアプリ。Claude（AWS Bedrock）とGemini（Google Vertex AI）を統合し、入力量に応じて自動モデル切り替えを行う。

## Commands

### Backend

```bash
# 依存関係インストール
uv sync

# 開発サーバー起動
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# テスト（全件）
python -m pytest tests/ -v --tb=short

# テスト（単一ファイル）
python -m pytest tests/services/test_summary_service.py -v

# テスト（単一テスト）
python -m pytest tests/services/test_summary_service.py::test_generate_summary -v

# カバレッジ付きテスト
python -m pytest tests/ -v --tb=short --cov=app --cov-report=html

# 型チェック（app/のみ、tests/・scripts/は除外）
pyright
```

### Frontend

```bash
cd frontend

npm install       # 依存関係インストール
npm run dev       # 開発サーバー（port 5173、/apiはFastAPIにプロキシ）
npm run build     # 本番ビルド → app/static/dist/ に出力
npm run typecheck # TypeScript型チェック
```

### Database Migrations

```bash
alembic revision --autogenerate -m "説明"
alembic upgrade head
alembic downgrade -1
```

## Architecture

### Request Flow

1. Jinja2テンプレート（`app/templates/`）がAlpine.jsでインタラクティブなUIを提供
2. FastAPIルーター（`app/api/router.py` → 各エンドポイント）がリクエストを受理
3. サービス層（`app/services/`）がビジネスロジックを実行
4. `model_selector.py`が入力文字数とDB設定から使用AIを決定
5. `api_factory.create_client(APIProvider)`が適切なAPIクライアントを動的生成
6. AI生成結果を`text_processor.py`がセクション分割してJSON返却
7. 使用統計（トークン数・処理時間）をPostgreSQLに保存

### Key Design Patterns

**Factory Pattern** (`app/external/api_factory.py`):
```python
from app.external.api_factory import create_client, APIProvider
client = create_client(APIProvider.CLAUDE)  # or APIProvider.GEMINI
```

**Hierarchical Prompt Resolution** (`app/services/prompt_service.py`):
DBから以下の順でプロンプトを解決する：
1. 診療科 + 医師 + 文書タイプ
2. 診療科 + デフォルト医師 + 文書タイプ
3. デフォルト診療科 + デフォルト医師 + 文書タイプ
4. `constants.py`の`DEFAULT_SUMMARY_PROMPT`定数

**Auto Model Switching** (`app/services/model_selector.py`):
入力が`MAX_TOKEN_THRESHOLD`（デフォルト100,000文字）を超えるとClaudeからGeminiに自動切り替え。

### Constants Management

すべての定数は`app/core/constants.py`で一元管理。マジック文字列を避け、必ず定数・Enumを使用すること。
- `ModelType` Enum: `"Claude"`, `"Gemini_Pro"`
- `MESSAGES` dict: カテゴリ別の日本語メッセージ（`get_message(category, key, **kwargs)`で取得）
- 診療科・医師・文書タイプのマッピング定数

### Frontend Architecture

フロントエンドはVite + TypeScript + Alpine.js + Tailwind CSS。ビルド成果物は`app/static/dist/`に出力され、Jinja2テンプレートから参照される。Alpine.jsのロジックは`frontend/src/app.ts`に集約し、型定義は`frontend/src/types.ts`に記述する。

### Security Middleware (`app/core/security.py`)

- `SecurityHeadersMiddleware`: XSS・クリックジャッキング・MIMEスニッフィング対策ヘッダーを自動付与
- CSRFトークン: 全状態変更エンドポイント（POST/PUT/DELETE）で`X-CSRF-Token`ヘッダー検証
- `app/utils/input_sanitizer.py`: プロンプトインジェクション・XSS攻撃パターン検出

## Code Style

- すべての関数に型ヒント（パラメータ・戻り値）を付与
- インポート順: 標準ライブラリ → サードパーティ → ローカル（各グループ内で`import`が先、`from`は後、アルファベット順）
- 関数サイズは50行以下を目標
- コメントは複雑なロジックのみ日本語で記述（文末に句点不要）

## Commit Messages

従来のコミット形式を使用（絵文字プレフィックス付き）：
- `✨ feat`: 新機能
- `🐛 fix`: バグ修正
- `📝 docs`: ドキュメント
- `♻️ refactor`: リファクタリング
- `✅ test`: テスト

変更内容と理由を日本語で記述。

## Environment Variables

環境変数はOS環境変数 → AWS Secrets Manager（`AWS_SECRET_NAME`）→ `.env`ファイルの優先順で読み込まれる。主要な変数：
- `ANTHROPIC_MODEL`, `GEMINI_MODEL`: 使用するモデルID
- `MAX_TOKEN_THRESHOLD`: Gemini自動切り替えの文字数閾値（デフォルト100,000）
- `PROMPT_MANAGEMENT`: プロンプト管理UI有効化フラグ（`true`/`false`）
- `CORS_ORIGINS`: 許可するオリジンのJSON配列
