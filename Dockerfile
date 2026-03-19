# Stage 1: フロントエンドビルド
FROM node:22-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .
COPY app/templates/ /app/app/templates/
RUN npm run build

# Stage 2: Python本番イメージ
FROM python:3.13-slim

WORKDIR /app

# uvの最新バージョン
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 本番依存のみインストール
COPY requirements.lock .
RUN uv pip install --no-cache-dir --system --require-hashes -r requirements.lock

# フロントエンドビルド成果物をコピー
COPY --from=frontend-builder /app/app/static/dist app/static/dist

COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "120"]