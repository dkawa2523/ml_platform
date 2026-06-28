from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping

from .stages import StageName, as_stage_name


class ConfigValidationError(ValueError):
    """Raised when external YAML config cannot be parsed into the typed boundary."""


def _copy_mapping(value: Mapping[str, object]) -> dict[str, Any]:
    return deepcopy(dict(value))


def _section(raw: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = raw.get(key)
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ConfigValidationError(f"{key} must be a mapping.")
    return value


def _optional_str(value: object, path: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigValidationError(f"{path} must be a string or null.")
    return value


def _required_str(value: object, path: str) -> str:
    text = _optional_str(value, path)
    if text is None or not text.strip():
        raise ConfigValidationError(f"{path} must be a non-empty string.")
    return text


def _optional_int(value: object, path: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigValidationError(f"{path} must be an integer or null.")
    return value


def _optional_float(value: object, path: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigValidationError(f"{path} must be a number or null.")
    return float(value)


def _optional_bool(value: object, path: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ConfigValidationError(f"{path} must be a boolean or null.")
    return value


def _str_list_or_none(value: object, path: str) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return [part.strip() for part in text.split(",") if part.strip()] if text else None
    if isinstance(value, list | tuple):
        return [str(item) for item in value]
    raise ConfigValidationError(f"{path} must be a list of strings, comma string, or null.")


def _list_or_empty(value: object, path: str) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list | tuple):
        return [deepcopy(item) for item in value]
    raise ConfigValidationError(f"{path} must be a list.")


def _mapping_or_empty(value: object, path: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ConfigValidationError(f"{path} must be a mapping.")
    return _copy_mapping(value)


def _extras(raw: Mapping[str, object], known: set[str]) -> dict[str, Any]:
    return {key: deepcopy(value) for key, value in raw.items() if key not in known}


@dataclass(frozen=True)
class RuntimeConfig:
    output_dir: str = "outputs"
    use_clearml: bool = False
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def parse(cls, raw: Mapping[str, object]) -> RuntimeConfig:
        output_dir = _optional_str(raw.get("output_dir"), "runtime.output_dir") or "outputs"
        use_clearml = _optional_bool(raw.get("use_clearml"), "runtime.use_clearml")
        return cls(output_dir=output_dir, use_clearml=bool(use_clearml), extras=_extras(raw, {"output_dir", "use_clearml"}))

    def to_dict(self) -> dict[str, Any]:
        return {"output_dir": self.output_dir, "use_clearml": self.use_clearml, **deepcopy(self.extras)}


@dataclass(frozen=True)
class RunSectionConfig:
    name: str | None = None
    seed: int | None = None
    stage: StageName | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def parse(cls, raw: Mapping[str, object]) -> RunSectionConfig:
        stage_value = _optional_str(raw.get("stage"), "run.stage")
        try:
            stage = as_stage_name(stage_value) if stage_value else None
        except ValueError as exc:
            raise ConfigValidationError(str(exc)) from exc
        return cls(
            name=_optional_str(raw.get("name"), "run.name"),
            seed=_optional_int(raw.get("seed"), "run.seed"),
            stage=stage,
            extras=_extras(raw, {"name", "seed", "stage"}),
        )

    def to_dict(self) -> dict[str, Any]:
        data = deepcopy(self.extras)
        if self.name is not None:
            data["name"] = self.name
        if self.seed is not None:
            data["seed"] = self.seed
        if self.stage is not None:
            data["stage"] = self.stage
        return data


@dataclass(frozen=True)
class DataConfig:
    local_path: str | None = None
    clearml_dataset_id: str | None = None
    dataset_file: str | None = None
    target_column: str | None = None
    feature_columns: list[str] | None = None
    id_columns: list[str] = field(default_factory=list)
    base_dir: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def parse(cls, raw: Mapping[str, object]) -> DataConfig:
        return cls(
            local_path=_optional_str(raw.get("local_path"), "data.local_path"),
            clearml_dataset_id=_optional_str(raw.get("clearml_dataset_id"), "data.clearml_dataset_id"),
            dataset_file=_optional_str(raw.get("dataset_file"), "data.dataset_file"),
            target_column=_optional_str(raw.get("target_column"), "data.target_column"),
            feature_columns=_str_list_or_none(raw.get("feature_columns"), "data.feature_columns"),
            id_columns=_str_list_or_none(raw.get("id_columns", []), "data.id_columns") or [],
            base_dir=_optional_str(raw.get("base_dir"), "data.base_dir"),
            extras=_extras(raw, {"local_path", "clearml_dataset_id", "dataset_file", "target_column", "feature_columns", "id_columns", "base_dir"}),
        )

    def to_dict(self) -> dict[str, Any]:
        data = deepcopy(self.extras)
        for key in ("local_path", "clearml_dataset_id", "dataset_file", "target_column", "feature_columns", "base_dir"):
            value = getattr(self, key)
            if value is not None:
                data[key] = deepcopy(value)
        data["id_columns"] = list(self.id_columns)
        return data


@dataclass(frozen=True)
class SplitConfig:
    method: str = "random"
    valid_size: float = 0.2
    group_column: str | None = None
    time_column: str | None = None
    valid_filter_column: str | None = None
    valid_filter_value: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def parse(cls, raw: Mapping[str, object]) -> SplitConfig:
        valid_size = _optional_float(raw.get("valid_size"), "split.valid_size")
        if valid_size is not None and not 0 < valid_size < 1:
            raise ConfigValidationError("split.valid_size must be between 0 and 1.")
        return cls(
            method=_optional_str(raw.get("method"), "split.method") or "random",
            valid_size=0.2 if valid_size is None else valid_size,
            group_column=_optional_str(raw.get("group_column"), "split.group_column"),
            time_column=_optional_str(raw.get("time_column"), "split.time_column"),
            valid_filter_column=_optional_str(raw.get("valid_filter_column"), "split.valid_filter_column"),
            valid_filter_value=_optional_str(raw.get("valid_filter_value"), "split.valid_filter_value"),
            extras=_extras(raw, {"method", "valid_size", "group_column", "time_column", "valid_filter_column", "valid_filter_value"}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "valid_size": self.valid_size,
            "group_column": self.group_column,
            "time_column": self.time_column,
            "valid_filter_column": self.valid_filter_column,
            "valid_filter_value": self.valid_filter_value,
            **deepcopy(self.extras),
        }


@dataclass(frozen=True)
class MetricsConfig:
    names: list[str] | str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def parse(cls, raw: Mapping[str, object]) -> MetricsConfig:
        names = raw.get("names")
        if names is not None and not isinstance(names, str | list | tuple):
            raise ConfigValidationError("metrics.names must be a list, comma string, or null.")
        parsed_names: list[str] | str | None
        parsed_names = names if isinstance(names, str) else (_str_list_or_none(names, "metrics.names") if names is not None else None)
        return cls(names=parsed_names, extras=_extras(raw, {"names"}))

    def to_dict(self) -> dict[str, Any]:
        data = deepcopy(self.extras)
        if self.names is not None:
            data["names"] = deepcopy(self.names)
        return data


@dataclass(frozen=True)
class FeaturesConfig:
    preset: str = "basic"
    numeric_impute_strategy: str = "median"
    categorical_impute_strategy: str = "missing_token"
    categorical_encoder: str = "onehot"
    scaling: str = "standard"
    drop_columns: list[str] = field(default_factory=list)
    passthrough_columns: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def parse(cls, raw: Mapping[str, object]) -> FeaturesConfig:
        return cls(
            preset=_optional_str(raw.get("preset"), "features.preset") or "basic",
            numeric_impute_strategy=_optional_str(raw.get("numeric_impute_strategy"), "features.numeric_impute_strategy") or "median",
            categorical_impute_strategy=_optional_str(raw.get("categorical_impute_strategy"), "features.categorical_impute_strategy") or "missing_token",
            categorical_encoder=_optional_str(raw.get("categorical_encoder"), "features.categorical_encoder") or "onehot",
            scaling=_optional_str(raw.get("scaling"), "features.scaling") or "standard",
            drop_columns=_str_list_or_none(raw.get("drop_columns", []), "features.drop_columns") or [],
            passthrough_columns=_str_list_or_none(raw.get("passthrough_columns", []), "features.passthrough_columns") or [],
            params=_mapping_or_empty(raw.get("params"), "features.params"),
            extras=_extras(
                raw,
                {
                    "preset",
                    "numeric_impute_strategy",
                    "categorical_impute_strategy",
                    "categorical_encoder",
                    "scaling",
                    "drop_columns",
                    "passthrough_columns",
                    "params",
                },
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "preset": self.preset,
            "numeric_impute_strategy": self.numeric_impute_strategy,
            "categorical_impute_strategy": self.categorical_impute_strategy,
            "categorical_encoder": self.categorical_encoder,
            "scaling": self.scaling,
            "drop_columns": list(self.drop_columns),
            "passthrough_columns": list(self.passthrough_columns),
            "params": deepcopy(self.params),
            **deepcopy(self.extras),
        }


@dataclass(frozen=True)
class EnsembleConfig:
    enabled: bool = False
    methods: list[str] = field(default_factory=lambda: ["mean_topk"])
    method: str = "mean_topk"
    top_k: int = 3
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def parse(cls, raw: Mapping[str, object]) -> EnsembleConfig:
        top_k = _optional_int(raw.get("top_k"), "model.ensemble.top_k")
        if top_k is not None and top_k < 1:
            raise ConfigValidationError("model.ensemble.top_k must be at least 1.")
        return cls(
            enabled=bool(_optional_bool(raw.get("enabled"), "model.ensemble.enabled")),
            methods=_str_list_or_none(raw.get("methods", ["mean_topk"]), "model.ensemble.methods") or ["mean_topk"],
            method=_optional_str(raw.get("method"), "model.ensemble.method") or "mean_topk",
            top_k=3 if top_k is None else top_k,
            extras=_extras(raw, {"enabled", "methods", "method", "top_k"}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "methods": list(self.methods),
            "method": self.method,
            "top_k": self.top_k,
            **deepcopy(self.extras),
        }


@dataclass(frozen=True)
class ModelConfig:
    name: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    candidates: list[Any] = field(default_factory=list)
    selection_metric: str | None = None
    ensemble: EnsembleConfig = field(default_factory=EnsembleConfig)
    source_type: str | None = None
    source_task_id: str | None = None
    model_selector: str | None = None
    local_model_path: str | None = None
    artifact_path: str | None = None
    info_path: str | None = None
    feature_spec_path: str | None = None
    preprocess_bundle_path: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def parse(cls, raw: Mapping[str, object]) -> ModelConfig:
        ensemble_raw = raw.get("ensemble") or {}
        if not isinstance(ensemble_raw, Mapping):
            raise ConfigValidationError("model.ensemble must be a mapping.")
        known = {
            "name",
            "params",
            "candidates",
            "selection_metric",
            "ensemble",
            "source_type",
            "source_task_id",
            "model_selector",
            "local_model_path",
            "artifact_path",
            "info_path",
            "feature_spec_path",
            "preprocess_bundle_path",
        }
        return cls(
            name=_optional_str(raw.get("name"), "model.name"),
            params=_mapping_or_empty(raw.get("params"), "model.params"),
            candidates=_list_or_empty(raw.get("candidates"), "model.candidates"),
            selection_metric=_optional_str(raw.get("selection_metric"), "model.selection_metric"),
            ensemble=EnsembleConfig.parse(ensemble_raw),
            source_type=_optional_str(raw.get("source_type"), "model.source_type"),
            source_task_id=_optional_str(raw.get("source_task_id"), "model.source_task_id"),
            model_selector=_optional_str(raw.get("model_selector"), "model.model_selector"),
            local_model_path=_optional_str(raw.get("local_model_path"), "model.local_model_path"),
            artifact_path=_optional_str(raw.get("artifact_path"), "model.artifact_path"),
            info_path=_optional_str(raw.get("info_path"), "model.info_path"),
            feature_spec_path=_optional_str(raw.get("feature_spec_path"), "model.feature_spec_path"),
            preprocess_bundle_path=_optional_str(raw.get("preprocess_bundle_path"), "model.preprocess_bundle_path"),
            extras=_extras(raw, known),
        )

    def to_dict(self) -> dict[str, Any]:
        data = deepcopy(self.extras)
        for key in (
            "name",
            "selection_metric",
            "source_type",
            "source_task_id",
            "model_selector",
            "local_model_path",
            "artifact_path",
            "info_path",
            "feature_spec_path",
            "preprocess_bundle_path",
        ):
            value = getattr(self, key)
            if value is not None:
                data[key] = value
        data["params"] = deepcopy(self.params)
        data["candidates"] = deepcopy(self.candidates)
        data["ensemble"] = self.ensemble.to_dict()
        return data


@dataclass(frozen=True)
class OutputConfig:
    prediction_name: str | None = None
    chunk_size: int | None = None
    report_plots: bool | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def parse(cls, raw: Mapping[str, object]) -> OutputConfig:
        return cls(
            prediction_name=_optional_str(raw.get("prediction_name"), "output.prediction_name"),
            chunk_size=_optional_int(raw.get("chunk_size"), "output.chunk_size"),
            report_plots=_optional_bool(raw.get("report_plots"), "output.report_plots"),
            extras=_extras(raw, {"prediction_name", "chunk_size", "report_plots"}),
        )

    def to_dict(self) -> dict[str, Any]:
        data = deepcopy(self.extras)
        if self.prediction_name is not None:
            data["prediction_name"] = self.prediction_name
        if self.chunk_size is not None:
            data["chunk_size"] = self.chunk_size
        if self.report_plots is not None:
            data["report_plots"] = self.report_plots
        return data


@dataclass(frozen=True)
class BaseTaskConfig:
    task: str
    profile: str | None
    runtime: RuntimeConfig
    run: RunSectionConfig


@dataclass(frozen=True)
class RunConfig:
    base: BaseTaskConfig
    data: DataConfig
    split: SplitConfig
    metrics: MetricsConfig
    features: FeaturesConfig
    model: ModelConfig
    output: OutputConfig
    clearml: dict[str, Any] = field(default_factory=dict)
    logging: dict[str, Any] = field(default_factory=dict)
    basic: dict[str, Any] = field(default_factory=dict)
    stage_inputs: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    extras: dict[str, Any] = field(default_factory=dict)
    present_sections: frozenset[str] = field(default_factory=frozenset)

    @property
    def task(self) -> str:
        return self.base.task

    @property
    def profile(self) -> str | None:
        return self.base.profile

    @property
    def runtime(self) -> RuntimeConfig:
        return self.base.runtime

    @property
    def run(self) -> RunSectionConfig:
        return self.base.run

    def to_dict(self) -> dict[str, Any]:
        data = deepcopy(self.extras)
        data["task"] = self.task
        if "profile" in self.present_sections or self.profile is not None:
            data["profile"] = self.profile
        if "runtime" in self.present_sections:
            data["runtime"] = self.runtime.to_dict()
        if "run" in self.present_sections:
            data["run"] = self.run.to_dict()
        if "data" in self.present_sections:
            data["data"] = self.data.to_dict()
        if "split" in self.present_sections:
            data["split"] = self.split.to_dict()
        if "metrics" in self.present_sections:
            data["metrics"] = self.metrics.to_dict()
        if "features" in self.present_sections:
            data["features"] = self.features.to_dict()
        if "model" in self.present_sections:
            data["model"] = self.model.to_dict()
        if "output" in self.present_sections:
            data["output"] = self.output.to_dict()
        if "clearml" in self.present_sections:
            data["clearml"] = deepcopy(self.clearml)
        if "logging" in self.present_sections:
            data["logging"] = deepcopy(self.logging)
        if "basic" in self.present_sections:
            data["basic"] = deepcopy(self.basic)
        if "stage_inputs" in self.present_sections:
            data["stage_inputs"] = deepcopy(self.stage_inputs)
        if "_meta" in self.present_sections:
            data["_meta"] = deepcopy(self.meta)
        return data


def parse_run_config(raw: Mapping[str, object]) -> RunConfig:
    if not isinstance(raw, Mapping):
        raise ConfigValidationError("run config must be a mapping.")
    task = _required_str(raw.get("task"), "task")
    present = frozenset(raw)
    runtime = RuntimeConfig.parse(_section(raw, "runtime"))
    run = RunSectionConfig.parse(_section(raw, "run"))
    known_top_level = {
        "task",
        "profile",
        "runtime",
        "run",
        "data",
        "split",
        "metrics",
        "features",
        "model",
        "output",
        "clearml",
        "logging",
        "basic",
        "stage_inputs",
        "_meta",
    }
    base = BaseTaskConfig(
        task=task,
        profile=_optional_str(raw.get("profile"), "profile"),
        runtime=runtime,
        run=run,
    )
    return RunConfig(
        base=base,
        data=DataConfig.parse(_section(raw, "data")),
        split=SplitConfig.parse(_section(raw, "split")),
        metrics=MetricsConfig.parse(_section(raw, "metrics")),
        features=FeaturesConfig.parse(_section(raw, "features")),
        model=ModelConfig.parse(_section(raw, "model")),
        output=OutputConfig.parse(_section(raw, "output")),
        clearml=_copy_mapping(_section(raw, "clearml")),
        logging=_copy_mapping(_section(raw, "logging")),
        basic=_copy_mapping(_section(raw, "basic")),
        stage_inputs=_copy_mapping(_section(raw, "stage_inputs")),
        meta=_copy_mapping(_section(raw, "_meta")),
        extras=_extras(raw, known_top_level),
        present_sections=present,
    )
