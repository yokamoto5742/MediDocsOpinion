# 変更履歴

このプロジェクトの変更履歴は[Keep a Changelog](https://keepachangelog.com/ja/1.1.0/)の仕様に従い、[セマンティック バージョニング](https://semver.org/lang/ja/)を採用しています。

## [1.0.2] - 2026-03-02

### 変更

- **プロジェクト構造ドキュメント**: プロジェクト構造ファイルを更新し、ディレクトリ構成をより正確に反映
- **README の構成**: Cloudflare 関連設定と CORS 設定の説明を削除し、README をシンプルに

---

## [1.0.1] - 2026-02-24

### 追加

- **Bedrockリソースへのアクセス権限拡張**: IAM ポリシーを更新し、AWS Bedrock リソースへのアクセス権限を拡張

### 変更

- **CORSオリジン設定の動的取得**: CORSオリジン設定を環境変数から動的に取得するように改善
- **AnthropicBedrockの初期化簡略化**: ECS タスク定義から AWS認証情報の設定を削除し、AnthropicBedrockの初期化処理を簡略化
- **監査ログのタイムゾーン設定**: 監査ログのタイムゾーンをJST（日本標準時）に統一

### 修正

- **Claude API テストの改善**: テストの修正と信頼性の向上
- **DATABASE_URLのパースロジック**: コンフィグのDATABASE_URLパースロジックを修正

---

## [1.0.0] - 2026-02-22

### 追加

- **複数のAIプロバイダーサポート**: Claude（AWS Bedrock/直接API）とGemini（Google Vertex AI）の両方に対応
- **自動モデル切り替え機能**: 入力文字数が指定の閾値（デフォルト100,000文字）を超えた場合、Claude から Gemini に自動切り替え
- **AWS Secrets Manager 統合**: AWS Secrets Manager からの環境変数読み込みと展開機能
- **診療情報提供書の生成**: 医療カルテデータからAIを使用して構造化された診療情報提供書を自動生成
- **複数の文書タイプ対応**: 他院への紹介、逆紹介、返書、最終返書の4タイプに対応
- **診療科と医師別のカスタマイズ**: 診療科と医師ごとのカスタムプロンプトテンプレート作成・管理機能
- **階層的プロンプトシステム**: 医師 → 診療科 → 文書タイプ → デフォルトの優先順位でプロンプトを解決
- **プロンプト管理UI**: Webベースのプロンプト作成・編集・削除インターフェース
- **AI出力評価機能**: 生成された文書の品質をLLMで自動評価し、改善提案を提供
- **使用統計ページ**: API呼び出し数、トークン使用量、作成時間等の詳細な統計情報を表示
- **Server-Sent Events（SSE）対応**: 文書生成の長時間処理をSSEで実装し、リアルタイム進行状況表示
- **CSRF保護**: トークンベースのCSRF対策で状態変更エンドポイント（POST/PUT/DELETE）を保護
- **プロンプトインジェクション対策**: 多層的な入力検証とサニタイゼーション機能
- **セキュリティヘッダー**: XSS、クリックジャッキング、MIMEスニッフィング対策のセキュリティヘッダー自動設定
- **監査ログ機能**: 医療操作のセキュリティイベントをJSON形式で記録
- **CORS制御**: 環境変数ベースの柔軟なクロスオリジン設定
- **PostgreSQLデータベース**: SQLAlchemy ORM を使用したRelationalデータベース統合
- **データベースマイグレーション**: Alembic を使用したスキーマ管理
- **モダンなフロントエンド**: Vite + TypeScript + Tailwind CSS + Alpine.js で構成
- **API使用統計の自動記録**: トークン数、作成時間、コスト等を自動的に追跡

### 変更

- **FastAPI アプリケーションエンジン**: Uvicorn で起動する高性能 Web サーバー
- **テンプレートエンジン**: Jinja2 テンプレートを使用したサーバーサイドレンダリング

### セキュリティ

- **AWS Bedrock 認証**: AWS アクセスキーによるセキュアな Claude API アクセス
- **Google Cloud 認証**: サービスアカウント認証によるセキュアな Gemini API アクセス
- **環境変数管理**: `.env` ファイルと AWS Secrets Manager による機密情報の安全な管理
- **入力サニタイゼーション**: プロンプトインジェクション攻撃からの多層的な保護
- **HTTPS 対応**: Strict-Transport-Security ヘッダーで HTTPS を強制

---

## リンク

[1.0.2]: https://github.com/yourusername/MediDocsReferral/releases/tag/v1.0.2
[1.0.1]: https://github.com/yourusername/MediDocsReferral/releases/tag/v1.0.1
[1.0.0]: https://github.com/yourusername/MediDocsReferral/releases/tag/v1.0.0
