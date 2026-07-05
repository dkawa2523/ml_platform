import json

import pytest

from ml_platform_core.result import RunResult

from clearml_test_utils import load_clearml_adapter_module, load_clearml_reports_module


def test_clearml_upload_plots_false_skips_media_but_uploads_plot_artifact(tmp_path):
    reports = load_clearml_reports_module()
    plot = tmp_path / "plot.svg"
    plot.write_text("<svg />", encoding="utf-8")

    class FakeAdapter:
        def __init__(self):
            self.uploads = []
            self.media = []
            self.plots = []
            self.scalars = []
            self.tables = []

        def report_scalar(self, title, series, value, iteration=0):
            self.scalars.append((title, series, value, iteration))

        def upload_artifact(self, name, path):
            self.uploads.append((name, path))

        def report_table(self, title, series, path, iteration=0):
            self.tables.append((title, series, path, iteration))

        def report_media(self, title, series, path, iteration=0):
            self.media.append((title, series, path, iteration))

        def report_scatter(self, title, series, points, iteration=0):
            self.plots.append(("scatter", title, series, points, iteration))

        def report_histogram(self, title, series, values, iteration=0):
            self.plots.append(("histogram", title, series, values, iteration))

    adapter = FakeAdapter()
    result = RunResult(run_dir=tmp_path, metrics={"rmse": 1.0}, plots={"prediction_vs_actual": plot})

    reports.report_result(adapter, result, upload_plots=False)

    assert ("metrics", "rmse", 1.0, 0) in adapter.scalars
    assert ("prediction_vs_actual", plot) in adapter.uploads
    assert adapter.media == []
    assert adapter.plots == []


def test_clearml_adapter_reports_prediction_scatter_as_markers():
    adapter_module = load_clearml_adapter_module()

    class FakeLogger:
        def __init__(self):
            self.scatter_calls = []

        def report_scatter2d(self, **kwargs):
            self.scatter_calls.append(kwargs)

    class FakeTask:
        def __init__(self):
            self.logger = FakeLogger()

        def get_logger(self):
            return self.logger

    task = FakeTask()
    adapter_module.ClearMLAdapter(task).report_scatter(
        "prediction_vs_actual",
        "validation_predictions",
        [(1.0, 0.9), (2.0, 2.1)],
        iteration=0,
    )

    assert task.logger.scatter_calls == [
        {
            "title": "prediction_vs_actual",
            "series": "validation_predictions",
            "scatter": [(1.0, 0.9), (2.0, 2.1)],
            "iteration": 0,
            "xaxis": "actual",
            "yaxis": "prediction",
            "mode": "markers",
        }
    ]


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


def test_clearml_adapter_reports_plotly_and_axis_named_histogram():
    adapter_module = load_clearml_adapter_module()

    class FakeLogger:
        def __init__(self):
            self.plotly_calls = []
            self.histogram_calls = []

        def report_plotly(self, **kwargs):
            self.plotly_calls.append(kwargs)

        def report_histogram(self, **kwargs):
            self.histogram_calls.append(kwargs)

    class FakeTask:
        def __init__(self):
            self.logger = FakeLogger()

        def get_logger(self):
            return self.logger

    task = FakeTask()
    adapter = adapter_module.ClearMLAdapter(task)
    adapter.report_plotly(
        "prediction_vs_actual",
        "validation_predictions",
        {"data": [{"type": "scatter"}], "layout": {"xaxis": {"title": "actual"}}},
        iteration=2,
    )
    adapter.report_histogram(
        "residual_histogram",
        "validation_predictions",
        [0.1, -0.2],
        iteration=3,
        xaxis="residual (actual - prediction)",
        yaxis="count",
    )

    assert task.logger.plotly_calls == [
        {
            "title": "prediction_vs_actual",
            "series": "validation_predictions",
            "figure": {"data": [{"type": "scatter"}], "layout": {"xaxis": {"title": "actual"}}},
            "iteration": 2,
        }
    ]
    assert task.logger.histogram_calls == [
        {
            "title": "residual_histogram",
            "series": "validation_predictions",
            "values": [0.1, -0.2],
            "iteration": 3,
            "xaxis": "residual (actual - prediction)",
            "yaxis": "count",
        }
    ]


def test_clearml_adapter_report_plotly_does_not_silence_logger_runtime_errors():
    adapter_module = load_clearml_adapter_module()

    class FakeLogger:
        def report_plotly(self, **kwargs):
            raise RuntimeError("ClearML backend unavailable")

    class FakeTask:
        def get_logger(self):
            return FakeLogger()

    adapter = adapter_module.ClearMLAdapter(FakeTask())
    with pytest.raises(RuntimeError, match="ClearML backend unavailable"):
        adapter.report_plotly("plot", "series", {"data": []})


def test_clearml_report_result_expands_model_metrics_and_tables(tmp_path):
    reports = load_clearml_reports_module()
    metrics = tmp_path / "metrics.json"
    metrics.write_text(
        json.dumps(
            {
                "rmse": 0.25,
                "mae": 0.18,
                "r2": 0.92,
                "best_model": {"model_name": "mean_topk", "metrics": {"rmse": 0.25, "mae": 0.18, "r2": 0.92}},
            }
        ),
        encoding="utf-8",
    )
    feature_summary = tmp_path / "feature_summary.json"
    feature_summary.write_text(
        json.dumps(
            {
                "input_rows": 100,
                "train_rows": 80,
                "valid_rows": 20,
                "feature_count": 4,
                "numeric_feature_count": 3,
                "categorical_feature_count": 1,
                "passthrough_feature_count": 0,
                "dropped_feature_count": 0,
                "transformed_feature_count": 5,
            }
        ),
        encoding="utf-8",
    )
    leaderboard = tmp_path / "leaderboard.csv"
    leaderboard.write_text(
        "rank,model_name,artifact_kind,ensemble_method,selection_metric,rmse,mae,r2,infer_target,ref_kind\n"
        "1,mean_topk,ensemble,mean_topk,rmse,0.25,0.18,0.92,ensemble:mean_topk,task_artifact\n"
        "2,ridge,model,,rmse,0.3,0.2,0.9,ridge,task_artifact\n",
        encoding="utf-8",
    )
    feature_summary_table = tmp_path / "feature_summary_table.csv"
    feature_summary_table.write_text("metric,value\ninput_rows,100\n", encoding="utf-8")
    missing_rate_by_column = tmp_path / "missing_rate_by_column.csv"
    missing_rate_by_column.write_text("column,role,missing_count,missing_rate\nx,numeric,0,0.0\n", encoding="utf-8")
    feature_type_counts = tmp_path / "feature_type_counts.csv"
    feature_type_counts.write_text("feature_type,count\nnumeric,1\n", encoding="utf-8")
    data_quality_summary_table = tmp_path / "data_quality_summary_table.csv"
    data_quality_summary_table.write_text("metric,value\nrow_count,100\ntarget_is_numeric,true\n", encoding="utf-8")
    data_quality_warnings = tmp_path / "data_quality_warnings.csv"
    data_quality_warnings.write_text(
        "warning_type,column,value,message\npossible_leakage,target_score,target_score,Feature name looks suspicious.\n",
        encoding="utf-8",
    )
    feature_importance = tmp_path / "feature_importance_linear.csv"
    feature_importance.write_text("rank,feature,importance,raw_value,source\n1,x,0.5,0.5,coef_\n", encoding="utf-8")
    metrics_table = tmp_path / "metrics_table.csv"
    metrics_table.write_text("metric,value\nrmse,0.25\nmae,0.18\nr2,0.92\n", encoding="utf-8")
    validation_predictions = tmp_path / "validation_predictions.csv"
    validation_predictions.write_text("actual,prediction,residual,abs_error\n1,0.9,0.1,0.1\n", encoding="utf-8")
    aggregate_validation_predictions = tmp_path / "validation_predictions_linear.csv"
    aggregate_validation_predictions.write_text(
        "actual,prediction,residual,abs_error\n1,0.9,0.1,0.1\n", encoding="utf-8"
    )
    evaluation_predictions = tmp_path / "evaluation_predictions.csv"
    evaluation_predictions.write_text("actual,prediction,residual,abs_error\n1,1.1,-0.1,0.1\n", encoding="utf-8")
    predictions = tmp_path / "predictions.csv"
    predictions.write_text("row_index,prediction\n0,1.1\n", encoding="utf-8")
    schema_check_summary = tmp_path / "schema_check_summary.csv"
    schema_check_summary.write_text("metric,value\nstatus,ok\nrow_count,1\n", encoding="utf-8")
    prediction_summary = tmp_path / "prediction_summary.csv"
    prediction_summary.write_text("metric,value\nprediction_rows,1\n", encoding="utf-8")
    prediction_preview = tmp_path / "prediction_preview.csv"
    prediction_preview.write_text("prediction\n1.1\n", encoding="utf-8")
    source_summary = tmp_path / "source_summary.csv"
    source_summary.write_text("field,value\nmodel_selector,best\nartifact_kind,model\n", encoding="utf-8")
    processed_train = tmp_path / "processed_train.csv"
    processed_train.write_text("x,target\n1,2\n", encoding="utf-8")
    ensemble_predictions = tmp_path / "ensemble_predictions_weighted.csv"
    ensemble_predictions.write_text("actual,prediction,residual,abs_error\n1,1.05,-0.05,0.05\n", encoding="utf-8")
    ensemble_predictions_alias = tmp_path / "ensemble_predictions.csv"
    ensemble_predictions_alias.write_text(
        "actual,prediction,residual,abs_error\n1,1.05,-0.05,0.05\n",
        encoding="utf-8",
    )
    ensemble_metrics_table = tmp_path / "ensemble_metrics_table.csv"
    ensemble_metrics_table.write_text("ensemble_method,rmse,mae,r2\nweighted,0.24,0.17,0.93\n", encoding="utf-8")
    ensemble_members = tmp_path / "ensemble_members_weighted.csv"
    ensemble_members.write_text("rank,model_name,weight\n1,ridge,1.0\n", encoding="utf-8")
    ensemble_weights = tmp_path / "ensemble_weights_weighted.csv"
    ensemble_weights.write_text("rank,model_name,weight\n1,ridge,1.0\n", encoding="utf-8")
    plot_paths = {
        "validation_prediction_vs_actual": tmp_path / "validation_prediction_vs_actual.png",
        "best_prediction_vs_actual": tmp_path / "best_prediction_vs_actual.png",
        "best_residual_histogram": tmp_path / "best_residual_histogram.png",
        "prediction_distribution_histogram": tmp_path / "prediction_distribution_histogram.png",
        "leaderboard_metric_panel": tmp_path / "leaderboard_metric_panel.png",
    }
    suppressed_plot_alias = tmp_path / "prediction_vs_actual.png"
    for plot_path in [*plot_paths.values(), suppressed_plot_alias]:
        plot_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    class FakeAdapter:
        def __init__(self):
            self.uploads = []
            self.images = []
            self.media = []
            self.plots = []
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

        def report_plotly(self, title, series, figure, iteration=0):
            self.plots.append(("plotly", title, series, figure, iteration))

        def report_scatter(self, title, series, points, iteration=0):
            self.plots.append(("scatter", title, series, points, iteration))

        def report_histogram(self, title, series, values, iteration=0, **kwargs):
            self.plots.append(("histogram", title, series, values, iteration, kwargs))

    adapter = FakeAdapter()
    result = RunResult(
        run_dir=tmp_path,
        metrics={
            "rmse": 0.25,
            "best_model": {"model_name": "mean_topk", "metrics": {"rmse": 0.25, "mae": 0.18, "r2": 0.92}},
        },
        artifacts={
            "metrics": metrics,
            "feature_summary": feature_summary,
        },
        tables={
            "leaderboard": leaderboard,
            "feature_summary_table": feature_summary_table,
            "missing_rate_by_column": missing_rate_by_column,
            "feature_type_counts": feature_type_counts,
            "data_quality_summary_table": data_quality_summary_table,
            "data_quality_warnings": data_quality_warnings,
            "feature_importance_linear": feature_importance,
            "metrics_table": metrics_table,
            "validation_predictions": validation_predictions,
            "validation_predictions_linear": aggregate_validation_predictions,
            "evaluation_predictions": evaluation_predictions,
            "predictions": predictions,
            "schema_check_summary": schema_check_summary,
            "prediction_summary": prediction_summary,
            "prediction_preview": prediction_preview,
            "source_summary": source_summary,
            "processed_train": processed_train,
            "ensemble_metrics_table": ensemble_metrics_table,
            "ensemble_predictions": ensemble_predictions_alias,
            "ensemble_predictions_weighted": ensemble_predictions,
            "ensemble_members_weighted": ensemble_members,
            "ensemble_weights_weighted": ensemble_weights,
        },
        plots={**plot_paths, "prediction_vs_actual": suppressed_plot_alias},
    )

    reports.report_result(adapter, result)

    _assert_report_uploads(adapter, plot_paths, suppressed_plot_alias)
    _assert_report_scalars(adapter)
    _assert_report_tables(
        adapter,
        {
            "leaderboard_table": leaderboard,
            "feature_summary_table": feature_summary_table,
            "missing_rate_by_column": missing_rate_by_column,
            "feature_type_counts": feature_type_counts,
            "data_quality_summary_table": data_quality_summary_table,
            "data_quality_warnings_table": data_quality_warnings,
            "feature_importance_linear": feature_importance,
            "metrics_table": metrics_table,
            "validation_predictions": validation_predictions,
            "evaluation_predictions": evaluation_predictions,
            "predictions_table": predictions,
            "schema_check_summary_table": schema_check_summary,
            "prediction_summary_table": prediction_summary,
            "prediction_preview_table": prediction_preview,
            "source_summary_table": source_summary,
            "ensemble_metrics_table": ensemble_metrics_table,
            "ensemble_predictions_weighted": ensemble_predictions,
            "ensemble_members_weighted": ensemble_members,
            "ensemble_weights_weighted": ensemble_weights,
        },
        {
            "ensemble_predictions": ensemble_predictions_alias,
            "validation_predictions_linear": aggregate_validation_predictions,
            "processed_train": processed_train,
        },
    )
    _assert_report_images(adapter, plot_paths, suppressed_plot_alias)
    assert adapter.plots == []
    assert adapter.media == []


def _assert_report_uploads(adapter, plot_paths, suppressed_plot_alias):
    expected_uploads = {
        ("prediction_vs_actual", suppressed_plot_alias),
        *set(plot_paths.items()),
    }
    assert expected_uploads <= set(adapter.uploads)


def _assert_report_scalars(adapter):
    expected_scalars = {
        ("ensemble/rmse", "weighted", 0.24, 0),
        ("best_model/r2", "mean_topk", 0.92, 0),
        ("features", "input_rows", 100.0, 0),
        ("features", "transformed_feature_count", 5.0, 0),
        ("metrics", "mae", 0.18, 0),
        ("metrics", "rmse", 0.25, 0),
    }
    assert expected_scalars <= set(adapter.scalars)


def _assert_report_tables(adapter, expected_tables, suppressed_tables):
    table_calls = set(adapter.tables)
    assert {("tables", name, path, 0) for name, path in expected_tables.items()} <= table_calls
    assert table_calls.isdisjoint({("tables", name, path, 0) for name, path in suppressed_tables.items()})


def _assert_report_images(adapter, plot_paths, suppressed_plot_alias):
    assert {("plots", name, path, 0) for name, path in plot_paths.items()} <= set(adapter.images)
    assert ("plots", "prediction_vs_actual", suppressed_plot_alias, 0) not in adapter.images


def test_clearml_report_result_falls_back_to_media_when_image_api_is_unavailable(tmp_path):
    reports = load_clearml_reports_module()
    plot = tmp_path / "plot.png"
    plot.write_bytes(b"\x89PNG\r\n\x1a\n")

    class FakeAdapter:
        def __init__(self):
            self.uploads = []
            self.media = []

        def upload_artifact(self, name, path):
            self.uploads.append((name, path))

        def report_scalar(self, title, series, value, iteration=0):
            pass

        def report_media(self, title, series, path, iteration=0):
            self.media.append((title, series, path, iteration))

    adapter = FakeAdapter()
    reports.report_result(adapter, RunResult(run_dir=tmp_path, plots={"plot": plot}))

    assert ("plot", plot) in adapter.uploads
    assert ("plots", "plot", plot, 0) in adapter.media
