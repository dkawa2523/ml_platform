"""Compatibility entrypoint for template synchronization."""

from _entrypoint_bootstrap import add_clearml_entrypoint_paths

add_clearml_entrypoint_paths()

from ml_platform_clearml.templates import sync_templates

__all__ = ["sync_templates"]
