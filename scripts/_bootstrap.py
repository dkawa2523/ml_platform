from __future__ import annotations

import sys
from pathlib import Path


def add_repo_paths() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    for rel in ("pkgs/core/src", "pkgs/tabular/src", "."):
        p = str(repo_root / rel)
        if p not in sys.path:
            sys.path.insert(0, p)
