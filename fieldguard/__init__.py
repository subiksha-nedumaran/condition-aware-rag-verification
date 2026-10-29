"""Root package bridge enabling zero-config execution of `python -m fieldguard.<module>` from repository root."""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent
_src_dir = str(_repo_root / "src")
_src_pkg_dir = str(_repo_root / "src" / "fieldguard")

if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

if _src_pkg_dir not in __path__:
    __path__.insert(0, _src_pkg_dir)

__version__ = "0.1.0"
