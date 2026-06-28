from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path


def load_sync_function():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "clearml" / "templates.py"
    spec = importlib.util.spec_from_file_location("ml_platform_clearml_templates", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.sync_templates


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync ClearML template tasks.")
    parser.add_argument("--profile", required=True, help="Path to profile config YAML.")
    parser.add_argument("--dry-run", action="store_true", help="Print template definitions without requiring ClearML SDK.")
    args = parser.parse_args()
    sync_templates = load_sync_function()
    sync_templates(args.profile, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
