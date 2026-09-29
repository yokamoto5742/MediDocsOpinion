---
description: テスト実行コマンドとテスト方針
---

## テスト実行コマンド

```bash
# 全件
.venv\Scripts\python.exe -m pytest tests/ -v --tb=short

# 単一ファイル
.venv\Scripts\python.exe -m pytest tests/service/test_keep_doc_merge.py -v

# 単一テスト
.venv\Scripts\python.exe -m pytest tests/service/test_keep_doc_merge.py::test_merge_memo_trashes_copy_after_merge -v

# カバレッジ付き
.venv\Scripts\python.exe -m pytest tests/ -v --tb=short --cov=app --cov-report=html
```
