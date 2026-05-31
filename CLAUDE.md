# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FastAPI アプリケーション。医師が紹介状などの医療文書を作成するため、Claude (AWS Bedrock) または Gemini (Vertex AI) を使用して文書を自動生成する。バックエンドは Python 3.13+、フロントエンドは Vite + TypeScript + Alpine.js + Tailwind CSS。

## 開発サーバー起動

```bash
# バックエンド
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# フロントエンド (別ターミナル)
npm run dev   # port 5173、/api は localhost:8000 へプロキシ
```

## ビルド

```bash
npm run build          # フロントエンドを app/static/dist/ へ出力
docker build .         # 本番用マルチステージビルド (Node.js → Python)
```

## 依存関係・環境

```bash
uv sync                # 依存関係インストール
uv sync --frozen       # CI/CD 用 (lock ファイル厳守)
```

`.env` ファイルが必要 (git 管理外)。最低限必要な変数: `POSTGRES_*` (DB 接続情報)、`AWS_REGION`、`GOOGLE_PROJECT_ID`。本番環境では AWS Secrets Manager から取得する。

## 型チェック

```bash
pyright    # app/ と tests/ のみ対象 (scripts/ は除外)
```
