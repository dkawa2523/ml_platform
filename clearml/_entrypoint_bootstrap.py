from __future__ import annotations

import sys
from pathlib import Path


def _prepend_once(path: Path) -> None:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


def add_clearml_entrypoint_paths() -> None:
    """Make repo-local entrypoint imports work without shadowing the SDK.

    ClearML remote templates execute files under this operations directory
    directly. Keep only the sibling operations modules and editable package
    source roots on sys.path; official ClearML SDK imports must still go
    through adapter.import_clearml_sdk().
    """
    clearml_dir = Path(__file__).resolve().parent
    repo_root = clearml_dir.parent
    for path in reversed(
        (
            clearml_dir,
            repo_root / "pkgs/core/src",
            repo_root / "pkgs/tabular/src",
        )
    ):
        _prepend_once(path)
