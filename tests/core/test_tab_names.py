#!/usr/bin/env python3
"""tab_names動作確認スクリプト"""
from app.core.constants import DEFAULT_SECTION_NAMES

print("=" * 50)
print("DEFAULT_SECTION_NAMES:")
for i, name in enumerate(DEFAULT_SECTION_NAMES, 1):
    print(f"  {i}. {name}")

tab_names = ["全文"] + list(DEFAULT_SECTION_NAMES)
print("\n生成されるtab_names:")
for i, name in enumerate(tab_names, 1):
    print(f"  {i}. {name}")

print("\nタブ数:", len(tab_names))
print("=" * 50)
