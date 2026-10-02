# Changelog

このプロジェクトのすべての変更は、このファイルに記録されます。

フォーマットは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に基づき、
このプロジェクトは [Semantic Versioning](https://semver.org/lang/ja/) に準拠しています。

## [Unreleased]

## [1.2.1] - 2026-10-02

### 変更

- **コード品質の向上**: 複数のモジュールを改善し、エラーハンドリングとテストケースを簡素化
- **セクション検出パターンを統一**: 複数のパターン配列から単一の正規表現に統一（`SECTION_DETECTION_PATTERN`）
- **フロントエンドを TypeScript 化**: HTML テンプレートの論理をフロントエンド側に移行し、保守性と拡張性を向上

### 削除

- **未使用のメッセージ定数を削除**: Bedrock、Cloudflare Gateway、Vertex AI に関連するエラーメッセージおよび設定メッセージを削除
  - `BEDROCK_API_ERROR`、`BEDROCK_INIT_ERROR`、`CLAUDE_CLIENT_NOT_INITIALIZED`（エラーメッセージ）
  - `CLOUDFLARE_GATEWAY_API_ERROR`、`CLOUDFLARE_GATEWAY_NOT_INITIALIZED`（エラーメッセージ）
  - `GEMINI_CLIENT_NOT_INITIALIZED`、`MODEL_NAME_NOT_SPECIFIED`、`UNSUPPORTED_API_PROVIDER`（エラーメッセージ）
  - `VERTEX_AI_API_ERROR`、`VERTEX_AI_CREDENTIALS_ERROR` 等複数の Vertex AI 関連エラーメッセージ
  - `API_CREDENTIALS_MISSING`、`AWS_CREDENTIALS_MISSING` 等の認証情報関連の設定メッセージ
  - `NO_DATA_FOUND`（統計情報ページの未使用メッセージ）
  - `ANTHROPIC_MODEL_MISSING`（設定メッセージ）、`FIELD_REQUIRED`（入力検証メッセージ、`FRONTEND_MESSAGE_KEYS` のキーを含む）
- **HTML テンプレートファイルを削除**: プロンプト管理ページとして以下を削除し、フロントエンド側に機能を統合
  - `prompts.html`、`prompts_new.html`、`prompts_edit.html`
  - `evaluation_prompts.html`、`evaluation_prompts_edit.html`
- **不要なテストケースを削除**: 削除されたモジュール・機能に関連するテストを簡素化

### 追加

- **CSRF セキュリティメッセージを追加**: CSRF トークン検証機能を強化
  - `CSRF_TOKEN_INVALID`、`CSRF_TOKEN_REQUIRED`（エラーメッセージ）
  - `CSRF_SECRET_KEY_MISSING`（設定メッセージ）
- **入力検証メッセージを追加**: 疑わしい入力パターンを検出するための `SUSPICIOUS_INPUT` メッセージ

## [1.2.0] - 2026-09-30

### 変更

- **Gemini呼び出しを Interactions API に移行**: `generateContent` から `client.interactions.create` に切り替え（通常生成・ストリーミングとも）。トークン数は `usage.total_input_tokens` / `total_output_tokens` から取得
- **Gemini応答の保存を無効化**: 患者情報を含むため `store=False` を指定し、Google 側にリクエスト・応答を保存しないように変更
- **依存関係の更新**: `google-genai` の下限を 2.3.0 に引き上げ（Interactions API 対応版）

### 削除

- **未使用の依存関係**: `google-generativeai` を削除（コードから未参照で、Python 3.14 環境で `google-genai` 2.x との依存解決を妨げていたため）

## [1.1.1] - 2026-06-14

### 変更

- 依存関係を最新バージョンへアップデート
- DBプールリサイクル設定を環境変数から取得可能に変更
- Claudeモデル設定を`anthropic_model`に統合

### 削除

- 未使用のsettings を削除
- `DEFAULT_DOCTOR` 定数を削除
- `sanitize_prompt_text` 関数を削除
- `PromptUpdate` スキーマを削除
- `statistics_records_tbody.html` テンプレートを削除

### 修正

- エラーメッセージを定型化し、詳細情報を非公開に変更
- 統計レコードのID比較ロジックを修正
- 統計レコードのソート順序を修正

## [1.1.0] - 2026-05-31

### 追加

- コード品質向上のため、Ruffコードリンターを導入

### 変更

- 依存関係管理を従来のpipからUVへ移行し、パフォーマンスと再現性を向上
- 複数の依存ライブラリを最新バージョンへアップデート
- テストの構造を改善し、セクション名を統一

## [1.0.2] - 2026-03-19

### 追加

- 統計・使用量フローの統合テストを追加し、エンドツーエンドのフローを検証

### 変更

- `DailyUsageSummary`をPydanticモデルへ移行し、データ検証を強化
- APIパラメータの命名を汎用的に変更：`current_prescription`を`previous_text`にリネーム
- テストでセクション名を「治療経過」に統一

## [1.0.1] - 2026-03-10

### 追加

- 日次利用制限機能を追加し、ユーザーが1日に使用できるトークン数に上限を設定。

## [1.0.0] - 2026-03-03

安定版初回リリース

[Unreleased]: https://github.com/yourusername/MediDocsOpinion/compare/v1.2.1...HEAD
[1.2.1]: https://github.com/yourusername/MediDocsOpinion/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/yourusername/MediDocsOpinion/compare/v1.1.2...v1.2.0
[1.1.2]: https://github.com/yourusername/MediDocsOpinion/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/yourusername/MediDocsOpinion/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/yourusername/MediDocsOpinion/compare/v1.0.2...v1.1.0
[1.0.2]: https://github.com/yourusername/MediDocsOpinion/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/yourusername/MediDocsOpinion/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/yourusername/MediDocsOpinion/releases/tag/v1.0.0
