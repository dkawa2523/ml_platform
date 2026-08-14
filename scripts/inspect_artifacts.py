from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect manifest.json from a run directory.")
    parser.add_argument("run_dir", nargs="?", default="outputs/latest_training_pipeline")
    args = parser.parse_args()

    manifest_path = Path(args.run_dir) / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    print(json.dumps(json.loads(manifest_path.read_text(encoding="utf-8")), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
