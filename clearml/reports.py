from __future__ import annotations

import json
from numbers import Real
from pathlib import Path
from typing import Any

from ml_platform_core.result import RunResult

MODEL_METRICS = ("rmse", "mae", "r2")
MAX_CANDIDATE_PLOT_GROUPS = 5
FEATURE_SUMMARY_SCALARS = (
    "input_rows",
    "train_rows",
    "valid_rows",
    "feature_count",
    "numeric_feature_count",
    "categorical_feature_count",
    "passthrough_feature_count",
    "dropped_feature_count",
    "transformed_feature_count",
)
TABLE_REPORTS = {
    "leaderboard",
    "leaderboard_topk",
    "candidate_predictions",
    "validation_predictions",
    "evaluation_predictions",
    "evaluation_summary",
    "leaderboard_decision_summary",
    "best_vs_ensemble_summary",
    "predictions",
    "schema_check_summary",
    "prediction_summary",
    "prediction_preview",
    "source_summary",
    "feature_summary_table",
    "missing_rate_by_column",
    "feature_type_counts",
    "data_quality_summary_table",
    "data_quality_warnings",
    "metrics_table",
    "metrics_by_candidate",
    "ensemble_metrics_table",
}
TABLE_SERIES_ALIASES = {
    "leaderboard": "leaderboard_table",
    "leaderboard_topk": "leaderboard_topk_table",
    "candidate_predictions": "candidate_predictions_table",
    "evaluation_summary": "evaluation_summary_table",
    "leaderboard_decision_summary": "leaderboard_decision_summary_table",
    "best_vs_ensemble_summary": "best_vs_ensemble_summary_table",
    "predictions": "predictions_table",
    "schema_check_summary": "schema_check_summary_table",
    "prediction_summary": "prediction_summary_table",
    "prediction_preview": "prediction_preview_table",
    "source_summary": "source_summary_table",
    "data_quality_summary_table": "data_quality_summary_table",
    "data_quality_warnings": "data_quality_warnings_table",
}
TABLE_REPORT_PREFIXES = (
    "feature_importance",
    "ensemble_members",
    "ensemble_weights",
    "metrics_table",
)
PREDICTION_PLOT_TABLES = {
    "candidate_predictions",
    "validation_predictions",
    "evaluation_predictions",
    "predictions",
}
NON_REPORT_TABLES = {
    # Compatibility aliases remain uploaded as artifacts, but the UI should
    # show the canonical table names only.
    "feature_summary",
    "feature_missingness",
    "ensemble_predictions",
}
NON_REPORT_PLOT_IMAGES = {
    # Generic aliases of best-entry plots; keep the artifacts, but avoid
    # duplicate image panels in ClearML PLOTS.
    "prediction_vs_actual",
    "residual_histogram",
    "residual_vs_predicted",
}


def _read_json(path: str | Path) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


def _read_csv_or_none(path: str | Path):
    try:
        import pandas as pd

        return pd.read_csv(path)
    except (OSError, UnicodeDecodeError, ValueError):
        return None


def _numeric_metrics(payload: dict[str, Any]) -> dict[str, float]:
    metrics = payload.get("metrics", payload)
    if not isinstance(metrics, dict):
        return {}
    return {name: float(metrics[name]) for name in MODEL_METRICS if isinstance(metrics.get(name), Real)}


def _report_candidate_metrics(adapter, path: str | Path, *, title_prefix: str) -> None:
    payload = _read_json(path)
    by_candidate = payload.get("metrics_by_candidate") or payload.get("metrics_by_model") or {}
    if not isinstance(by_candidate, dict):
        return
    for model_name, model_payload in by_candidate.items():
        if not isinstance(model_payload, dict):
            continue
        metrics = _numeric_metrics(model_payload)
        for metric_name, value in metrics.items():
            adapter.report_scalar(f"{title_prefix}/{metric_name}", str(model_name), value, iteration=0)
        if model_payload.get("artifact_kind") == "ensemble":
            series = str(model_payload.get("ensemble_method") or model_name)
            for metric_name, value in metrics.items():
                adapter.report_scalar(f"ensemble/{metric_name}", series, value, iteration=0)


def _report_best_model_metrics(adapter, metrics_payload: dict[str, Any]) -> None:
    best_model = metrics_payload.get("best_model")
    if not isinstance(best_model, dict):
        return
    series = str(best_model.get("model_name") or best_model.get("ensemble_method") or "best")
    for metric_name, value in _numeric_metrics(best_model).items():
        adapter.report_scalar(f"best_model/{metric_name}", series, value, iteration=0)


def _report_feature_summary_metrics(adapter, path: str | Path) -> None:
    payload = _read_json(path)
    for key in FEATURE_SUMMARY_SCALARS:
        value = payload.get(key)
        if isinstance(value, Real):
            adapter.report_scalar("features", key, float(value), iteration=0)


def _report_plain_metrics(adapter, payload: dict[str, Any], *, title: str = "metrics") -> None:
    for metric_name, value in _numeric_metrics(payload).items():
        adapter.report_scalar(title, metric_name, value, iteration=0)
    _report_best_model_metrics(adapter, payload)


def _report_metrics_table(adapter, path: str | Path, *, title: str = "metrics") -> None:
    frame = _read_csv_or_none(path)
    if frame is None:
        return
    if not {"metric", "value"} <= set(frame.columns):
        return
    for row in frame.itertuples(index=False):
        try:
            value = float(row.value)
        except (TypeError, ValueError):
            continue
        adapter.report_scalar(title, str(row.metric), value, iteration=0)


def _report_ensemble_metrics_table(adapter, path: str | Path) -> None:
    frame = _read_csv_or_none(path)
    if frame is None:
        return
    if "ensemble_method" not in frame.columns:
        return
    for row in frame.to_dict(orient="records"):
        series = str(row.get("ensemble_method") or row.get("model_name") or "ensemble")
        for metric_name in MODEL_METRICS:
            value = row.get(metric_name)
            if isinstance(value, Real):
                adapter.report_scalar(f"ensemble/{metric_name}", series, float(value), iteration=0)


def _finite_pairs(frame, left: str, right: str):
    import pandas as pd

    x = pd.to_numeric(frame[left], errors="coerce")
    y = pd.to_numeric(frame[right], errors="coerce")
    valid = x.notna() & y.notna()
    return x[valid], y[valid]


def _r2_score(actual, prediction) -> float | None:
    if len(actual) < 2:
        return None
    ss_res = float(((actual - prediction) ** 2).sum())
    centered = actual - float(actual.mean())
    ss_tot = float((centered**2).sum())
    if ss_tot <= 0.0:
        return None
    return 1.0 - ss_res / ss_tot


def _candidate_label(frame, table_name: str) -> str:
    if "candidate_name" in frame.columns:
        value = frame["candidate_name"].dropna()
        if not value.empty:
            name = str(value.iloc[0])
            parts = []
            if "candidate_rank" in frame.columns:
                rank = frame["candidate_rank"].dropna()
                if not rank.empty:
                    parts.append(f"rank {int(float(rank.iloc[0]))}")
            if "artifact_kind" in frame.columns:
                kind = frame["artifact_kind"].dropna()
                if not kind.empty:
                    parts.append(str(kind.iloc[0]))
            if "ensemble_method" in frame.columns:
                method = frame["ensemble_method"].dropna()
                if not method.empty:
                    parts.append(str(method.iloc[0]))
            suffix = f" ({', '.join(parts)})" if parts else ""
            return f"{name}{suffix}"
    if table_name.startswith("ensemble_predictions_"):
        return table_name.replace("ensemble_predictions_", "ensemble:")
    return table_name


def _grouped_prediction_frames(frame, table_name: str):
    if "candidate_name" in frame.columns:
        for candidate_name, group in frame.groupby("candidate_name", sort=False):
            yield _candidate_label(group, table_name) or str(candidate_name), group
    else:
        yield _candidate_label(frame, table_name), frame


def _topk_candidate_plot_frame(frame):
    if "candidate_name" not in frame.columns:
        return frame
    if "candidate_rank" in frame.columns:
        import pandas as pd

        ranks = pd.to_numeric(frame["candidate_rank"], errors="coerce")
        top = frame[ranks.notna() & (ranks <= MAX_CANDIDATE_PLOT_GROUPS)].copy()
        if not top.empty:
            return top
    names = list(dict.fromkeys(str(value) for value in frame["candidate_name"].dropna()))
    keep = set(names[:MAX_CANDIDATE_PLOT_GROUPS])
    return frame[frame["candidate_name"].astype(str).isin(keep)].copy()


def _value_range(*values) -> tuple[float, float]:
    finite = []
    for value in values:
        for item in value:
            try:
                number = float(item)
            except (TypeError, ValueError):
                continue
            if number == number:
                finite.append(number)
    if not finite:
        return 0.0, 1.0
    low = min(finite)
    high = max(finite)
    if low == high:
        margin = 1.0 if low == 0 else abs(low) * 0.1
        return low - margin, high + margin
    margin = (high - low) * 0.05
    return low - margin, high + margin


def _prediction_vs_actual_figure(frame, table_name: str, *, title: str) -> dict[str, Any] | None:
    if not {"actual", "prediction"} <= set(frame.columns):
        return None
    traces: list[dict[str, Any]] = []
    all_actual = []
    all_prediction = []
    single_group = "candidate_name" not in frame.columns
    for label, group in _grouped_prediction_frames(frame, table_name):
        actual, prediction = _finite_pairs(group, "actual", "prediction")
        if actual.empty:
            continue
        all_actual.extend(float(value) for value in actual)
        all_prediction.extend(float(value) for value in prediction)
        r2 = _r2_score(actual, prediction)
        trace_name = label if r2 is None else f"{label} (R2={r2:.3f})"
        traces.append(
            {
                "type": "scatter",
                "mode": "markers",
                "name": trace_name,
                "x": [float(value) for value in actual],
                "y": [float(value) for value in prediction],
                "marker": {"size": 7},
            }
        )
    if not traces:
        return None
    low, high = _value_range(all_actual, all_prediction)
    traces.append(
        {
            "type": "scatter",
            "mode": "lines",
            "name": "y=x",
            "x": [low, high],
            "y": [low, high],
            "line": {"dash": "dash", "color": "#6b7280"},
        }
    )
    title_text = title
    if single_group and traces and "(R2=" in traces[0]["name"]:
        title_text = f"{title} {traces[0]['name'][traces[0]['name'].find('(R2=') :]}"
    return {
        "data": traces,
        "layout": {
            "title": title_text,
            "xaxis": {"title": "actual", "range": [low, high]},
            "yaxis": {"title": "prediction", "range": [low, high]},
            "showlegend": True,
        },
    }


def _residual_vs_predicted_figure(frame, table_name: str, *, title: str) -> dict[str, Any] | None:
    if not {"actual", "prediction"} <= set(frame.columns):
        return None
    traces: list[dict[str, Any]] = []
    all_prediction = []
    all_residual = []
    for label, group in _grouped_prediction_frames(frame, table_name):
        actual, prediction = _finite_pairs(group, "actual", "prediction")
        if actual.empty:
            continue
        residual = actual - prediction
        all_prediction.extend(float(value) for value in prediction)
        all_residual.extend(float(value) for value in residual)
        traces.append(
            {
                "type": "scatter",
                "mode": "markers",
                "name": label,
                "x": [float(value) for value in prediction],
                "y": [float(value) for value in residual],
                "marker": {"size": 7},
            }
        )
    if not traces:
        return None
    x_low, x_high = _value_range(all_prediction)
    y_low, y_high = _value_range(all_residual, [0.0])
    return {
        "data": [
            *traces,
            {
                "type": "scatter",
                "mode": "lines",
                "name": "zero residual",
                "x": [x_low, x_high],
                "y": [0.0, 0.0],
                "line": {"dash": "dash", "color": "#6b7280"},
            },
        ],
        "layout": {
            "title": title,
            "xaxis": {"title": "prediction", "range": [x_low, x_high]},
            "yaxis": {"title": "residual (actual - prediction)", "range": [y_low, y_high]},
            "showlegend": True,
        },
    }


def _residual_histogram_figure(frame, table_name: str, *, title: str) -> dict[str, Any] | None:
    if not {"actual", "prediction"} <= set(frame.columns):
        return None
    traces: list[dict[str, Any]] = []
    for label, group in _grouped_prediction_frames(frame, table_name):
        actual, prediction = _finite_pairs(group, "actual", "prediction")
        if actual.empty:
            continue
        residual = actual - prediction
        traces.append(
            {
                "type": "histogram",
                "name": label,
                "x": [float(value) for value in residual],
                "opacity": 0.6,
            }
        )
    if not traces:
        return None
    return {
        "data": traces,
        "layout": {
            "title": title,
            "xaxis": {"title": "residual (actual - prediction)"},
            "yaxis": {"title": "count"},
            "barmode": "overlay",
            "showlegend": True,
        },
    }


def _prediction_distribution_figure(frame, *, title: str = "Prediction distribution") -> dict[str, Any] | None:
    if "prediction" not in frame.columns:
        return None
    import pandas as pd

    prediction = pd.to_numeric(frame["prediction"], errors="coerce").dropna()
    if prediction.empty:
        return None
    return {
        "data": [
            {
                "type": "histogram",
                "name": "prediction",
                "x": [float(value) for value in prediction],
                "opacity": 0.75,
            }
        ],
        "layout": {
            "title": title,
            "xaxis": {"title": "prediction"},
            "yaxis": {"title": "count"},
            "showlegend": True,
        },
    }


def _format_cell(value: Any) -> str:
    if value is None:
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number != number:
        return ""
    return f"{number:.6g}"


def _leaderboard_label(row: dict[str, Any]) -> str:
    rank = row.get("rank", "?")
    name = row.get("model_name") or "unknown"
    method = row.get("ensemble_method")
    label = f"{rank}:{name}"
    if method:
        label = f"{label}:{method}"
    return label


def _leaderboard_topk(frame, top_k: int = MAX_CANDIDATE_PLOT_GROUPS):
    if "rank" not in frame.columns:
        return frame.head(top_k).copy()
    import pandas as pd

    ranks = pd.to_numeric(frame["rank"], errors="coerce")
    top = frame[ranks.notna() & (ranks <= top_k)].copy()
    return top if not top.empty else frame.head(top_k).copy()


def _leaderboard_table_figure(frame, *, title: str = "Leaderboard") -> dict[str, Any] | None:
    if frame.empty:
        return None
    columns = [
        "rank",
        "model_name",
        "artifact_kind",
        "ensemble_method",
        "rmse",
        "mae",
        "r2",
        "infer_target",
        "ref_kind",
    ]
    columns = [column for column in columns if column in frame.columns]
    if not columns:
        return None
    view = frame.head(20)
    row_colors = ["#fff4cc" if str(row.get("rank")) in {"1", "1.0"} else "#ffffff" for row in view.to_dict("records")]
    return {
        "data": [
            {
                "type": "table",
                "header": {
                    "values": columns,
                    "fill": {"color": "#f2f2f2"},
                    "align": "left",
                },
                "cells": {
                    "values": [[_format_cell(value) for value in view[column].tolist()] for column in columns],
                    "fill": {"color": [row_colors for _ in columns]},
                    "align": "left",
                },
            }
        ],
        "layout": {"title": title, "margin": {"l": 20, "r": 20, "t": 42, "b": 20}},
    }


def _selection_metric(frame) -> str:
    if "selection_metric" in frame.columns:
        values = frame["selection_metric"].dropna()
        if not values.empty:
            metric = str(values.iloc[0]).strip()
            if metric:
                return metric
    for candidate in ("rmse", "mae", "r2"):
        if candidate in frame.columns:
            return candidate
    return "score"


def _leaderboard_topk_bar_figure(frame, *, title: str = "Top-K score") -> dict[str, Any] | None:
    top = _leaderboard_topk(frame)
    metric = _selection_metric(top)
    if metric not in top.columns or top.empty:
        return None
    import pandas as pd

    values = pd.to_numeric(top[metric], errors="coerce")
    valid = values.notna()
    if not valid.any():
        return None
    rows = top[valid].to_dict("records")
    colors = ["#f28e2b" if str(row.get("rank")) in {"1", "1.0"} else "#4c78a8" for row in rows]
    return {
        "data": [
            {
                "type": "bar",
                "x": [_leaderboard_label(row) for row in rows],
                "y": [float(value) for value in values[valid]],
                "marker": {"color": colors},
                "name": metric,
            }
        ],
        "layout": {
            "title": f"{title} ({metric})",
            "xaxis": {"title": "rank/model"},
            "yaxis": {"title": metric},
            "showlegend": False,
        },
    }


def _leaderboard_metric_panel_figure(frame, *, title: str = "Top-K metric panel") -> dict[str, Any] | None:
    top = _leaderboard_topk(frame)
    if top.empty:
        return None
    import pandas as pd

    labels = [_leaderboard_label(row) for row in top.to_dict("records")]
    traces = []
    for metric in ("rmse", "mae", "r2"):
        if metric not in top.columns:
            continue
        values = pd.to_numeric(top[metric], errors="coerce")
        if values.notna().any():
            traces.append(
                {
                    "type": "bar",
                    "x": labels,
                    "y": [None if pd.isna(value) else float(value) for value in values],
                    "name": metric,
                }
            )
    if not traces:
        return None
    return {
        "data": traces,
        "layout": {
            "title": title,
            "xaxis": {"title": "rank/model"},
            "yaxis": {"title": "metric value"},
            "barmode": "group",
            "showlegend": True,
        },
    }


def _leaderboard_pareto_figure(frame, *, title: str = "Pareto: r2 vs rmse") -> dict[str, Any] | None:
    if not {"r2", "rmse"} <= set(frame.columns):
        return None
    import pandas as pd

    top = _leaderboard_topk(frame, top_k=10)
    r2 = pd.to_numeric(top["r2"], errors="coerce")
    rmse = pd.to_numeric(top["rmse"], errors="coerce")
    valid = r2.notna() & rmse.notna()
    if not valid.any():
        return None
    rows = top[valid].to_dict("records")
    colors = ["#f28e2b" if str(row.get("rank")) in {"1", "1.0"} else "#4c78a8" for row in rows]
    return {
        "data": [
            {
                "type": "scatter",
                "mode": "markers+text",
                "x": [float(value) for value in r2[valid]],
                "y": [float(value) for value in rmse[valid]],
                "text": [_leaderboard_label(row) for row in rows],
                "textposition": "top center",
                "marker": {"size": 9, "color": colors, "opacity": 0.85},
                "name": "candidate",
            }
        ],
        "layout": {
            "title": title,
            "xaxis": {"title": "r2"},
            "yaxis": {"title": "rmse"},
            "showlegend": False,
        },
    }


def _report_plotly(adapter, title: str, series: str, figure: dict[str, Any] | None) -> bool:
    if not figure:
        return False
    report_plotly = getattr(adapter, "report_plotly", None)
    if not callable(report_plotly):
        return False
    report_plotly(title, series, figure, iteration=0)
    return True


def _report_leaderboard_dashboard(adapter, path: str | Path) -> None:
    report_plotly = getattr(adapter, "report_plotly", None)
    if not callable(report_plotly):
        return
    frame = _read_csv_or_none(path)
    if frame is None:
        return
    _report_plotly(adapter, "leaderboard", "table", _leaderboard_table_figure(frame))
    _report_plotly(adapter, "leaderboard", "top_k_scores", _leaderboard_topk_bar_figure(frame))
    _report_plotly(adapter, "leaderboard", "metric_panel", _leaderboard_metric_panel_figure(frame))
    _report_plotly(adapter, "leaderboard", "pareto_rmse_r2", _leaderboard_pareto_figure(frame))


def _report_prediction_plots(adapter, table_name: str, path: str | Path) -> None:
    report_scatter = getattr(adapter, "report_scatter", None)
    report_histogram = getattr(adapter, "report_histogram", None)
    report_plotly = getattr(adapter, "report_plotly", None)
    if not callable(report_plotly) and not callable(report_scatter) and not callable(report_histogram):
        return
    frame = _read_csv_or_none(path)
    if frame is None:
        return
    import pandas as pd

    if "prediction" not in frame:
        return
    prediction = pd.to_numeric(frame["prediction"], errors="coerce")
    if "actual" not in frame:
        values = prediction.dropna()
        if table_name == "predictions" and not values.empty:
            if callable(report_plotly):
                figure = _prediction_distribution_figure(frame, title="Prediction distribution")
                if _report_plotly(adapter, "prediction_distribution_histogram", table_name, figure):
                    return
            if callable(report_histogram):
                report_histogram(
                    "prediction_distribution_histogram",
                    table_name,
                    [float(value) for value in values],
                    iteration=0,
                    xaxis="prediction",
                    yaxis="count",
                )
        return
    actual = pd.to_numeric(frame["actual"], errors="coerce")
    valid = actual.notna() & prediction.notna()
    if not valid.any():
        return
    is_candidate_comparison = table_name == "candidate_predictions"
    is_best_evaluation = table_name == "evaluation_predictions"
    if is_candidate_comparison:
        frame = _topk_candidate_plot_frame(frame)
    plot_prefix = "topk_" if is_candidate_comparison else "best_" if is_best_evaluation else ""
    title_prefix = (
        f"Top-{MAX_CANDIDATE_PLOT_GROUPS} candidate "
        if is_candidate_comparison
        else "Best "
        if is_best_evaluation
        else ""
    )
    if callable(report_plotly):
        if is_candidate_comparison:
            plot_title = "leaderboard"
            residual_vs_title = "leaderboard"
            residual_hist_title = "leaderboard"
            prediction_series = "topk_prediction_vs_actual"
            residual_vs_series = "topk_residual_vs_predicted"
            residual_hist_series = "topk_residual_histogram"
        elif is_best_evaluation:
            plot_title = "leaderboard"
            residual_vs_title = "leaderboard"
            residual_hist_title = "leaderboard"
            prediction_series = "best_prediction_vs_actual"
            residual_vs_series = "best_residual_vs_predicted"
            residual_hist_series = "best_residual_histogram"
        else:
            plot_title = f"{plot_prefix}prediction_vs_actual"
            residual_vs_title = f"{plot_prefix}residual_vs_predicted"
            residual_hist_title = f"{plot_prefix}residual_histogram"
            prediction_series = table_name
            residual_vs_series = table_name
            residual_hist_series = table_name
        _report_plotly(
            adapter,
            plot_title,
            prediction_series,
            _prediction_vs_actual_figure(frame, table_name, title=f"{title_prefix}prediction vs actual"),
        )
        _report_plotly(
            adapter,
            residual_vs_title,
            residual_vs_series,
            _residual_vs_predicted_figure(frame, table_name, title=f"{title_prefix}residuals vs predicted"),
        )
        _report_plotly(
            adapter,
            residual_hist_title,
            residual_hist_series,
            _residual_histogram_figure(frame, table_name, title=f"{title_prefix}residual histogram"),
        )
        return

    actual = actual[valid]
    prediction = prediction[valid]
    if callable(report_scatter):
        points = [(float(a), float(p)) for a, p in zip(actual, prediction)]
        report_scatter(f"{plot_prefix}prediction_vs_actual", table_name, points, iteration=0)
    if callable(report_histogram):
        if "residual" in frame:
            residual = pd.to_numeric(frame.loc[valid, "residual"], errors="coerce").dropna()
        else:
            residual = actual - prediction
        report_histogram(
            f"{plot_prefix}residual_histogram",
            table_name,
            [float(value) for value in residual],
            iteration=0,
            xaxis="residual (actual - prediction)",
            yaxis="count",
        )


def _is_report_table(name: str) -> bool:
    if name in NON_REPORT_TABLES:
        return False
    return (
        name in TABLE_REPORTS
        or name.startswith("ensemble_predictions_")
        or any(name.startswith(prefix) for prefix in TABLE_REPORT_PREFIXES)
    )


def _is_prediction_plot_table(name: str) -> bool:
    if name == "ensemble_predictions":
        return False
    return name in PREDICTION_PLOT_TABLES or name.startswith("ensemble_predictions_")


def _report_table(adapter, name: str, path: str | Path) -> None:
    adapter.report_table("tables", TABLE_SERIES_ALIASES.get(name, name), path, iteration=0)


def _report_plot_image(adapter, name: str, path: str | Path) -> None:
    if name in NON_REPORT_PLOT_IMAGES:
        return
    report_image = getattr(adapter, "report_image", None)
    if callable(report_image):
        report_image("plots", name, path, iteration=0)
        return
    report_media = getattr(adapter, "report_media", None)
    if callable(report_media):
        report_media("plots", name, path, iteration=0)


def report_result(adapter, result: RunResult, *, report_plots: bool = True) -> None:
    """Report RunResult to ClearML.

    Keep this small: upload artifacts/tables, publish scalar metrics, and turn
    standard prediction tables into ClearML-native plots when requested.
    """
    for name, value in result.metrics.items():
        if isinstance(value, Real):
            adapter.report_scalar("metrics", name, float(value), iteration=0)
    _report_best_model_metrics(adapter, result.metrics)

    for name, path in result.artifacts.items():
        adapter.upload_artifact(name, path)
        if name == "metrics":
            _report_plain_metrics(adapter, _read_json(path))
        if name == "feature_summary":
            _report_feature_summary_metrics(adapter, path)
        if name == "metrics_by_model":
            _report_candidate_metrics(adapter, path, title_prefix="metrics_by_model")
        if name == "metrics_by_candidate":
            _report_candidate_metrics(adapter, path, title_prefix="metrics_by_candidate")

    for name, path in result.tables.items():
        adapter.upload_artifact(name, path)
        if _is_report_table(name):
            _report_table(adapter, name, path)
        if report_plots and name == "leaderboard":
            _report_leaderboard_dashboard(adapter, path)
        if name == "metrics_table" or name.startswith("metrics_table_"):
            _report_metrics_table(adapter, path)
        if name == "ensemble_metrics_table":
            _report_ensemble_metrics_table(adapter, path)
        if report_plots and _is_prediction_plot_table(name):
            _report_prediction_plots(adapter, name, path)

    for name, path in result.plots.items():
        adapter.upload_artifact(name, path)
        if report_plots:
            _report_plot_image(adapter, name, path)
