from __future__ import annotations

import importlib.util
from pathlib import Path

from _bootstrap import add_repo_paths

add_repo_paths()


def load_pipeline_main():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "clearml" / "pipelines.py"
    spec = importlib.util.spec_from_file_location("ml_platform_clearml_pipelines", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main


def main() -> None:
    load_pipeline_main()()


if __name__ == "__main__":
    main()
