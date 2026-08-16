import json

from clearml_test_utils import load_clearml_adapter_module, load_clearml_reports_module
from ml_platform_core.result import RunResult


class RecordingAdapter:
    def __init__(self):
        self.uploads = []
        self.images = []
        self.media = []
        self.scalars = []
        self.tables = []

    def report_scalar(self, title, series, value, iteration=0):
        self.scalars.append((title, series, value, iteration))

    def upload_artifact(self, name, path):
        self.uploads.append((name, path))

    def report_table(self, title, series, path, iteration=0):
        self.tables.append((title, series, path, iteration))

    def report_image(self, title, series, path, iteration=0):
        self.images.append((title, series, path, iteration))

    def report_media(self, title, series, path, iteration=0):
        self.media.append((title, series, path, iteration))


def test_clearml_upload_plots_false_skips_media_but_uploads_plot_artifact(tmp_path):
    reports = load_clearml_reports_module()
    plot = tmp_path / "plot.svg"
    plot.write_text("<svg />", encoding="utf-8")
    adapter = RecordingAdapter()

    reports.report_result(
        adapter,
        RunResult(run_dir=tmp_path, metrics={"rmse": 1.0}, plots={"prediction_vs_actual": plot}),
        upload_plots=False,
    )

    assert ("metrics", "rmse", 1.0, 0) in adapter.scalars
    assert ("prediction_vs_actual", plot) in adapter.uploads
    assert adapter.images == []
    assert adapter.media == []


def test_clearml_adapter_reports_table_preview_with_row_limit(tmp_path):
    adapter_module = load_clearml_adapter_module()
    table = tmp_path / "large.csv"
    table.write_text("value\n" + "\n".join(str(index) for index in range(1005)), encoding="utf-8")

    class FakeLogger:
        def report_table(self, **kwargs):
            self.table = kwargs["table_plot"]

    class FakeTask:
        def __init__(self):
            self.logger = FakeLogger()

        def get_logger(self):
            return self.logger

    task = FakeTask()
    adapter_module.ClearMLAdapter(task).report_table("tables", "large", table)

    assert len(task.logger.table) == 1000


def test_clearml_report_result_reports_only_canonical_diagnostics(tmp_path):
    reports = load_clearml_reports_module()
    metrics = tmp_path / "metrics.json"
    metrics.write_text(
        json.dumps({"best_model": {"model_name": "ridge", "metrics": {"rmse": 0.25}}}),
        encoding="utf-8",
    )
    data_quality = tmp_path / "data_quality_summary.json"
    data_quality.write_text(
        json.dumps(
            {
                "row_count": 100,
                "train_rows": 80,
                "valid_rows": 20,
                "feature_count": 4,
                "numeric_feature_count": 3,
                "categorical_feature_count": 1,
                "transformed_feature_count": 5,
            }
        ),
        encoding="utf-8",
    )
    leaderboard = tmp_path / "leaderboard.csv"
    leaderboard.write_text("rank,model_name,rmse\n1,ridge,0.25\n", encoding="utf-8")
    warnings = tmp_path / "data_quality_warnings.csv"
    warnings.write_text("warning_type,column,value,message\n", encoding="utf-8")
    processed = tmp_path / "processed_train.csv"
    processed.write_text("x,target\n1,2\n", encoding="utf-8")
    ensemble_metrics = tmp_path / "ensemble_metrics_table.csv"
    ensemble_metrics.write_text("ensemble_method,rmse\nweighted,0.24\n", encoding="utf-8")
    plot = tmp_path / "best_prediction_vs_actual.png"
    plot.write_bytes(b"\x89PNG\r\n\x1a\n")

    adapter = RecordingAdapter()
    reports.report_result(
        adapter,
        RunResult(
            run_dir=tmp_path,
            metrics={"rmse": 0.25, "mse": 0.0625, "candidate_count": 2},
            artifacts={"metrics": metrics, "data_quality_summary": data_quality},
            tables={
                "leaderboard": leaderboard,
                "data_quality_warnings": warnings,
                "processed_train": processed,
                "ensemble_metrics_table": ensemble_metrics,
            },
            plots={"best_prediction_vs_actual": plot},
        ),
    )

    assert {
        ("metrics", "rmse", 0.25, 0),
        ("metrics", "mse", 0.0625, 0),
        ("best_model/rmse", "ridge", 0.25, 0),
        ("features", "row_count", 100.0, 0),
        ("features", "transformed_feature_count", 5.0, 0),
        ("ensemble/rmse", "weighted", 0.24, 0),
    } <= set(adapter.scalars)
    assert all(series != "candidate_count" for _, series, _, _ in adapter.scalars)
    assert ("tables", "leaderboard_table", leaderboard, 0) in adapter.tables
    assert ("tables", "data_quality_warnings_table", warnings, 0) in adapter.tables
    assert ("tables", "processed_train", processed, 0) not in adapter.tables
    assert ("plots", "best_prediction_vs_actual", plot, 0) in adapter.images
    assert {("metrics", metrics), ("data_quality_summary", data_quality)} <= set(adapter.uploads)


def test_clearml_report_result_falls_back_to_media_when_image_api_is_unavailable(tmp_path):
    reports = load_clearml_reports_module()
    plot = tmp_path / "plot.png"
    plot.write_bytes(b"\x89PNG\r\n\x1a\n")

    class MediaAdapter:
        def __init__(self):
            self.uploads = []
            self.media = []

        def upload_artifact(self, name, path):
            self.uploads.append((name, path))

        def report_scalar(self, title, series, value, iteration=0):
            pass

        def report_media(self, title, series, path, iteration=0):
            self.media.append((title, series, path, iteration))

    adapter = MediaAdapter()
    reports.report_result(adapter, RunResult(run_dir=tmp_path, plots={"plot": plot}))

    assert ("plot", plot) in adapter.uploads
    assert ("plots", "plot", plot, 0) in adapter.media
