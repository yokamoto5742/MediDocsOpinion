---
description: データベースマイグレーションの操作方法
paths:
  - "app/models/**/*.py"
  - "alembic.ini"
  - "migrations/**/*.py"
---

## マイグレーションコマンド

```bash
alembic revision --autogenerate -m "説明"
alembic upgrade head
alembic downgrade -1
```
