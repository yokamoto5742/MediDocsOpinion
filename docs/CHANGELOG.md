# Changelog

このプロジェクトのすべての変更は、このファイルに記録されます。

フォーマットは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に基づき、
このプロジェクトは [Semantic Versioning](https://semver.org/lang/ja/) に準拠しています。

## [Unreleased]

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

[Unreleased]: https://github.com/yourusername/MediDocsOpinion/compare/v1.0.3...HEAD
[1.0.3]: https://github.com/yourusername/MediDocsOpinion/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/yourusername/MediDocsOpinion/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/yourusername/MediDocsOpinion/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/yourusername/MediDocsOpinion/releases/tag/v1.0.0
