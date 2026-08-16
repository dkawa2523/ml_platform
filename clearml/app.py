"""Compatibility entrypoint for synced ClearML task templates."""

from _entrypoint_bootstrap import add_clearml_entrypoint_paths

add_clearml_entrypoint_paths()

from ml_platform_clearml.app import main

if __name__ == "__main__":
    main()
