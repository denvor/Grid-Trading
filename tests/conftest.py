"""pytest 共享 fixtures / path 设置。"""
import os
import sys

# 让 tests/ 能用 `from fetch_data import ...` 导入 scripts/ 下的模块
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SCRIPTS_DIR = os.path.join(_REPO_ROOT, "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
