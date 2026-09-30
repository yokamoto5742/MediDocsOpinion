# Changelog

このプロジェクトのすべての変更は、このファイルに記録されます。

フォーマットは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に基づき、
このプロジェクトは [Semantic Versioning](https://semver.org/lang/ja/) に準拠しています。

## [Unreleased]

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

[Unreleased]: https://github.com/yourusername/MediDocsOpinion/compare/v1.1.2...HEAD
[1.1.2]: https://github.com/yourusername/MediDocsOpinion/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/yourusername/MediDocsOpinion/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/yourusername/MediDocsOpinion/compare/v1.0.2...v1.1.0
[1.0.2]: https://github.com/yourusername/MediDocsOpinion/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/yourusername/MediDocsOpinion/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/yourusername/MediDocsOpinion/releases/tag/v1.0.0
