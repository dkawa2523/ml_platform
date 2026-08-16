from __future__ import annotations

import pytest
from clearml_test_utils import FakeArtifact, FakeTask, install_fake_task_api, load_clearml_adapter_module


def _resolver(adapter, tasks):
    install_fake_task_api(adapter, tasks)
    resolver = adapter.ClearMLAdapter(task=None)
    resolver.resolve_artifact_path = lambda value: str(value)
    return resolver


def test_clearml_dataset_resolution_keeps_dataset_root_for_tabular_loader(tmp_path):
    adapter = load_clearml_adapter_module()
    root = tmp_path / "dataset"
    root.mkdir()
    (root / "first.csv").write_text("x\n1\n", encoding="utf-8")
    (root / "second.csv").write_text("x\n2\n", encoding="utf-8")

    resolved = adapter.ClearMLAdapter(task=None).resolve_dataset(None, str(root))

    assert resolved == str(root)


def test_clearml_resolves_infer_source_from_pipeline_controller_best_task():
    adapter = load_clearml_adapter_module()
    resolver = _resolver(
        adapter,
        [
            FakeTask("pipe", "tabular_train_pipeline_template"),
            FakeTask(
                "eval",
                "evaluate_models",
                artifacts={
                    "best_model": FakeArtifact("best_model.joblib"),
                    "best_model_json": FakeArtifact("best_model.json"),
                    "model_info": FakeArtifact("model_info.json"),
                },
                params={"Run/stage": "evaluate_models"},
                parent="pipe",
            ),
        ],
    )

    resolved = resolver.resolve_infer_model_source(
        {
            "task": "tabular_infer",
            "model": {"source_type": "task_id", "source_task_id": "pipe", "model_selector": "best"},
        }
    )

    assert resolved["model"]["artifact_path"] == "best_model.joblib"
    assert resolved["model"]["info_path"] == "model_info.json"
    assert resolved["model"]["resolved_source_task_name"] == "evaluate_models"
    assert resolved["model"]["resolved_source_artifact"] == "best_model"


def test_clearml_resolves_infer_source_from_pipeline_controller_ensemble_task():
    adapter = load_clearml_adapter_module()
    resolver = _resolver(
        adapter,
        [
            FakeTask("pipe", "tabular_train_pipeline_template"),
            FakeTask(
                "build",
                "build_ensemble",
                artifacts={
                    "model": FakeArtifact("ensemble.joblib"),
                    "model_info": FakeArtifact("ensemble_model_info.json"),
                },
                params={"Run/stage": "build_ensemble"},
                parent="pipe",
            ),
        ],
    )

    resolved = resolver.resolve_infer_model_source(
        {
            "task": "tabular_infer",
            "model": {"source_type": "task_id", "source_task_id": "pipe", "model_selector": "ensemble"},
        }
    )

    assert resolved["model"]["artifact_path"] == "ensemble.joblib"
    assert resolved["model"]["info_path"] == "ensemble_model_info.json"
    assert resolved["model"]["resolved_source_task_name"] == "build_ensemble"


def test_clearml_resolves_infer_source_from_pipeline_controller_ensemble_method_task():
    adapter = load_clearml_adapter_module()
    resolver = _resolver(
        adapter,
        [
            FakeTask("pipe", "tabular_train_pipeline_template"),
            FakeTask(
                "build",
                "build_ensemble",
                artifacts={
                    "model_weighted": FakeArtifact("ensemble_weighted.joblib"),
                    "model_info_weighted": FakeArtifact("ensemble_weighted_model_info.json"),
                },
                params={"Run/stage": "build_ensemble"},
                parent="pipe",
            ),
        ],
    )

    resolved = resolver.resolve_infer_model_source(
        {
            "task": "tabular_infer",
            "model": {"source_type": "task_id", "source_task_id": "pipe", "model_selector": "ensemble:weighted"},
        }
    )

    assert resolved["model"]["artifact_path"] == "ensemble_weighted.joblib"
    assert resolved["model"]["info_path"] == "ensemble_weighted_model_info.json"
    assert resolved["model"]["resolved_source_artifact"] == "model_weighted"


def test_clearml_resolves_infer_source_from_direct_train_stage_task():
    adapter = load_clearml_adapter_module()
    resolver = _resolver(
        adapter,
        [
            FakeTask(
                "train-linear",
                "train_linear",
                artifacts={
                    "model": FakeArtifact("linear.joblib"),
                    "model_info": FakeArtifact("linear_model_info.json"),
                },
                params={"Run/stage": "train_model", "Model/name": "linear"},
            )
        ],
    )

    resolved = resolver.resolve_infer_model_source(
        {
            "task": "tabular_infer",
            "model": {"source_type": "task_id", "source_task_id": "train-linear", "model_selector": "linear"},
        }
    )

    assert resolved["model"]["artifact_path"] == "linear.joblib"
    assert resolved["model"]["info_path"] == "linear_model_info.json"


def test_clearml_infer_source_resolution_reports_available_tasks_on_failure():
    adapter = load_clearml_adapter_module()
    install_fake_task_api(
        adapter,
        [
            FakeTask("pipe", "pipeline"),
            FakeTask("train-ridge", "train_ridge", params={"Run/stage": "train_model"}, parent="pipe"),
        ],
    )
    resolver = adapter.ClearMLAdapter(task=None)

    with pytest.raises(ValueError, match="Discovered:"):
        resolver.resolve_infer_model_source(
            {
                "task": "tabular_infer",
                "model": {"source_type": "task_id", "source_task_id": "pipe", "model_selector": "linear"},
            }
        )


@pytest.mark.parametrize(
    ("task_kwargs", "message"),
    [
        ({"status": "in_progress"}, "completed or published"),
        ({"tags": ["unrelated"]}, "configured platform tags"),
    ],
)
def test_clearml_rejects_task_sources_outside_the_platform_contract(task_kwargs, message):
    adapter = load_clearml_adapter_module()
    resolver = _resolver(
        adapter,
        [
            FakeTask(
                "model-task",
                "train_linear",
                artifacts={"model": FakeArtifact("model.joblib"), "model_info": FakeArtifact("model_info.json")},
                params={"Run/stage": "train_model", "Model/name": "linear"},
                **task_kwargs,
            )
        ],
    )

    with pytest.raises(ValueError, match=message):
        resolver.resolve_infer_model_source(
            {
                "task": "tabular_infer",
                "model": {
                    "source_type": "task_id",
                    "source_task_id": "model-task",
                    "model_selector": "linear",
                },
            }
        )


def test_clearml_rejects_task_sources_from_unconfigured_projects():
    adapter = load_clearml_adapter_module()
    resolver = _resolver(
        adapter,
        [
            FakeTask(
                "model-task",
                "train_linear",
                project="Personal/Unreviewed",
                artifacts={"model": FakeArtifact("model.joblib"), "model_info": FakeArtifact("model_info.json")},
                params={"Run/stage": "train_model", "Model/name": "linear"},
            )
        ],
    )

    with pytest.raises(ValueError, match="outside configured ClearML run projects"):
        resolver.resolve_infer_model_source(
            {
                "task": "tabular_infer",
                "clearml": {"projects": {"train": "MLPlatform/Dev/Runs/Tabular/Train"}},
                "model": {
                    "source_type": "task_id",
                    "source_task_id": "model-task",
                    "model_selector": "linear",
                },
            }
        )


def test_clearml_model_source_policy_can_be_tightened_per_environment():
    adapter = load_clearml_adapter_module()
    resolver = _resolver(
        adapter,
        [
            FakeTask(
                "model-task",
                "train_linear",
                status="published",
                tags=["approved:model", "run_type:pipeline"],
                artifacts={"model": FakeArtifact("model.joblib"), "model_info": FakeArtifact("model_info.json")},
                params={"Run/stage": "train_model", "Model/name": "linear"},
            )
        ],
    )

    resolved = resolver.resolve_infer_model_source(
        {
            "task": "tabular_infer",
            "clearml": {
                "model_source": {
                    "allowed_statuses": ["published"],
                    "required_tags": ["approved:model"],
                    "allowed_run_types": ["pipeline"],
                    "project_keys": [],
                }
            },
            "model": {
                "source_type": "task_id",
                "source_task_id": "model-task",
                "model_selector": "linear",
            },
        }
    )

    assert resolved["model"]["artifact_path"] == "model.joblib"
