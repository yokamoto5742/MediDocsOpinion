# フロントエンドセットアップガイド

このディレクトリには、Vite + TypeScript + Tailwind CSSを使用したフロントエンドビルド環境が含まれています。

## セットアップ

### 1. 依存関係のインストール

```bash
cd frontend && npm install
```

### 2. 開発サーバーの起動

```bash
npm run dev
```

- Vite開発サーバーがポート5173で起動します
- HMR（Hot Module Replacement）対応で、コード変更が即座に反映されます
- `/api`へのリクエストは自動的にFastAPI（http://localhost:8000）にプロキシされます

### 3. 型チェック

```bash
npm run typecheck
```

TypeScriptの型エラーをチェックします。

### 4. 本番ビルド

```bash
npm run build
```

ビルド成果物は`../app/static/dist/`に出力されます。

## ディレクトリ構造

```
frontend/
├── src/
│   ├── main.ts          # エントリーポイント
│   ├── app.ts           # Alpine.jsアプリケーションロジック
│   ├── types.ts         # 型定義
│   └── styles/
│       └── main.css     # Tailwind CSS + カスタムスタイル
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── postcss.config.js
```

## 開発フロー

1. **新機能追加時:**
   - `src/app.ts`に型付きでメソッドを追加
   - `src/types.ts`に必要な型定義を追加
   - テンプレート（`app/templates/`）でメソッドを呼び出し

2. **スタイル変更時:**
   - `src/styles/main.css`で`@apply`を使ったカスタムクラス定義
   - Tailwindの設定変更は`tailwind.config.js`

3. **型チェック:**
   - 定期的に`npm run typecheck`を実行
   - バックエンドのPydanticスキーマと型定義を同期

## トラブルシューティング

### ビルドエラー

- `vite.config.ts`のパス設定を確認
- `tsconfig.json`の設定を確認

### 型エラー

- `src/types.ts`の型定義を確認
- バックエンドのAPIレスポンス構造と一致しているか確認

### スタイルが反映されない

- `tailwind.config.js`の`content`パスを確認
- `npm run build`を再実行
