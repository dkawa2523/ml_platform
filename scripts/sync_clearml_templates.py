from __future__ import annotations

import argparse

from ml_platform_clearml.templates import sync_templates


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync ClearML template tasks.")
    parser.add_argument("--profile", required=True, help="Path to profile config YAML.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print template definitions without requiring ClearML SDK."
    )
    args = parser.parse_args()
    sync_templates(args.profile, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
