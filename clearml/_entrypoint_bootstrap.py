from __future__ import annotations

import sys
from pathlib import Path


def _prepend_once(path: Path) -> None:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


def add_clearml_entrypoint_paths() -> None:
    """Expose workspace packages to directly executed remote wrappers."""
    clearml_dir = Path(__file__).resolve().parent
    repo_root = clearml_dir.parent
    for path in reversed(
        (
            repo_root / "pkgs/core/src",
            repo_root / "pkgs/tabular/src",
            repo_root / "pkgs/clearml/src",
        )
    ):
        _prepend_once(path)
