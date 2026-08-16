import pytest
from ml_platform_tabular import models as model_module
from ml_platform_tabular.models import (
    AVAILABLE_MODELS,
    DEPENDENCY_FREE_MODELS,
    OPTIONAL_DEPENDENCY_MODELS,
    SUPPORTED_MODELS,
    OptionalDependencyError,
    build_model,
    model_params_for_seed,
)


def test_model_policy_excludes_out_of_scope_models():
    assert DEPENDENCY_FREE_MODELS == [
        "linear",
        "ridge",
        "lasso",
        "elasticnet",
        "random_forest",
        "extra_trees",
        "gradient_boosting",
    ]
    assert OPTIONAL_DEPENDENCY_MODELS == ["lightgbm", "xgboost", "catboost"]
    assert [*DEPENDENCY_FREE_MODELS, *OPTIONAL_DEPENDENCY_MODELS] == SUPPORTED_MODELS
    assert AVAILABLE_MODELS == SUPPORTED_MODELS
    for name in ["knn", "svr", "mlp", "gaussian_process", "tabpfn"]:
        with pytest.raises(ValueError, match="out of current product scope"):
            build_model(name)


def test_linear_model_rejects_parameters_it_cannot_apply():
    with pytest.raises(ValueError, match="does not accept model parameters"):
        build_model("linear", {"fit_intercept": False})


def test_run_seed_is_the_single_model_seed():
    assert model_params_for_seed("random_forest", {"n_estimators": 3, "random_state": 999}, 7) == {
        "n_estimators": 3,
        "random_state": 7,
    }
    assert model_params_for_seed("catboost", {"iterations": 3, "random_seed": 999}, 7) == {
        "iterations": 3,
        "random_seed": 7,
    }
    assert model_params_for_seed("ridge", {"alpha": 2.0}, 7) == {"alpha": 2.0}


def test_optional_dependency_models_fail_cleanly_when_dependency_missing(monkeypatch):
    real_import_module = model_module.importlib.import_module

    def fake_import_module(name):
        if name in {"lightgbm", "xgboost", "catboost"}:
            raise ModuleNotFoundError(f"No module named {name!r}", name=name)
        return real_import_module(name)

    monkeypatch.setattr(model_module.importlib, "import_module", fake_import_module)
    for name in ["lightgbm", "xgboost", "catboost"]:
        with pytest.raises(OptionalDependencyError, match=r"requires optional dependency.*uv sync --extra gbm"):
            build_model(name)


def test_optional_dependency_import_error_is_not_reported_as_missing(monkeypatch):
    def fake_import_module(name):
        if name == "lightgbm":
            raise ImportError("DLL load failed")
        raise AssertionError(f"unexpected import: {name}")

    monkeypatch.setattr(model_module.importlib, "import_module", fake_import_module)

    with pytest.raises(OptionalDependencyError, match=r"could not be imported.*DLL load failed"):
        build_model("lightgbm")


def test_optional_dependency_missing_class_has_version_message(monkeypatch):
    class FakeLightGBM:
        pass

    def fake_import_module(name):
        if name == "lightgbm":
            return FakeLightGBM()
        raise AssertionError(f"unexpected import: {name}")

    monkeypatch.setattr(model_module.importlib, "import_module", fake_import_module)

    with pytest.raises(OptionalDependencyError, match=r"LGBMRegressor.*does not expose"):
        build_model("lightgbm")


def test_optional_dependency_internal_runtime_error_is_not_hidden(monkeypatch):
    def fake_import_module(name):
        if name == "lightgbm":
            raise RuntimeError("library init failed")
        raise AssertionError(f"unexpected import: {name}")

    monkeypatch.setattr(model_module.importlib, "import_module", fake_import_module)

    with pytest.raises(RuntimeError, match="library init failed"):
        build_model("lightgbm")
