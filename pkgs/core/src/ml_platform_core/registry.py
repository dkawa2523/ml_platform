from __future__ import annotations

from collections.abc import Callable
from typing import Any


class Registry:
    """Small name-to-builder registry.

    This is intentionally simple. Do not introduce a plugin system until needed.
    """

    def __init__(self) -> None:
        self._builders: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, builder: Callable[..., Any]) -> None:
        if not name:
            raise ValueError("Registry name must not be empty.")
        self._builders[name] = builder

    def get(self, name: str) -> Callable[..., Any]:
        try:
            return self._builders[name]
        except KeyError as exc:
            available = ", ".join(sorted(self._builders))
            raise KeyError(f"Unknown registry item: {name}. Available: {available}") from exc

    def build(self, name: str, params: dict[str, Any] | None = None) -> Any:
        params = params or {}
        return self.get(name)(**params)

    def names(self) -> list[str]:
        return sorted(self._builders)
