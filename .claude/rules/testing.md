---
description: テスト実行コマンドとテスト方針
---

## テスト実行コマンド

```bash
# 全件
python -m pytest tests/ -v --tb=short

# 単一ファイル
python -m pytest tests/services/test_summary_service.py -v

# 単一テスト
python -m pytest tests/services/test_summary_service.py::test_generate_summary -v

# カバレッジ付き
python -m pytest tests/ -v --tb=short --cov=app --cov-report=html
```
