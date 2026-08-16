"""Map product configuration paths to ClearML parameter names."""

from __future__ import annotations

from typing import Any, NamedTuple

from ml_platform_core.contracts import ParameterSpec
from ml_platform_tabular.manifest import get_tabular_manifest


class RuntimeParamBinding(NamedTuple):
    key: str
    value_type: str
    config_path: tuple[str, ...] = ()


def bindings_for_config(cfg: dict[str, Any]) -> tuple[RuntimeParamBinding, ...]:
    return _merge_bindings(_STATIC_BINDINGS, _stage_input_bindings(cfg))


def binding_map_for_config(cfg: dict[str, Any]) -> dict[str, RuntimeParamBinding]:
    return {binding.key: binding for binding in bindings_for_config(cfg)}


def keys_with_type(value_type: str) -> set[str]:
    return {binding.key for binding in _STATIC_BINDINGS if binding.value_type == value_type}


def runtime_keys_for_config_section(section: str, *, value_type: str | None = None) -> tuple[str, ...]:
    return tuple(
        binding.key
        for binding in _STATIC_BINDINGS
        if binding.config_path[:1] == (section,) and (value_type is None or binding.value_type == value_type)
    )


def _static_bindings() -> tuple[RuntimeParamBinding, ...]:
    manifest = get_tabular_manifest()
    specs = _unique_specs(tuple(item.parameters for item in (*manifest.tasks, *manifest.stages)))
    return tuple(_binding(spec) for spec in specs)


def _unique_specs(groups: tuple[tuple[ParameterSpec, ...], ...]) -> tuple[ParameterSpec, ...]:
    specs: dict[str, ParameterSpec] = {}
    for group in groups:
        for spec in group:
            current = specs.get(spec.name)
            if current is None:
                specs[spec.name] = spec
            elif current.value_type != spec.value_type or current.config_path != spec.config_path:
                raise ValueError(f"Conflicting runtime ParameterSpec for {spec.name!r}.")
    return tuple(specs.values())


def _binding(spec: ParameterSpec) -> RuntimeParamBinding:
    return RuntimeParamBinding(spec.name, _binding_value_type(spec), spec.config_path)


def _binding_value_type(spec: ParameterSpec) -> str:
    if spec.name == "Model/candidates":
        return "candidates"
    if spec.value_type == "enum":
        return "str"
    return spec.value_type


def _stage_input_bindings(cfg: dict[str, Any]) -> tuple[RuntimeParamBinding, ...]:
    inputs = cfg.get("stage_inputs")
    if not isinstance(inputs, dict):
        return ()
    return tuple(RuntimeParamBinding(f"Input/{key}", "json", ("stage_inputs", key)) for key in inputs)


def _merge_bindings(
    static: tuple[RuntimeParamBinding, ...],
    dynamic: tuple[RuntimeParamBinding, ...],
) -> tuple[RuntimeParamBinding, ...]:
    return tuple(
        ({binding.key: binding for binding in static} | {binding.key: binding for binding in dynamic}).values()
    )


_STATIC_BINDINGS = _static_bindings()
