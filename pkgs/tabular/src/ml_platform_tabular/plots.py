from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from ml_platform_core.io import write_table


PALETTE = ("#2878b8", "#e17c45", "#59a14f", "#b07aa1", "#edc948")


def _font():
    return ImageFont.load_default()


def _canvas(width: int = 760, height: int = 460) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (width, height), "white")
    return image, ImageDraw.Draw(image)


def _save(image: Image.Image, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")
    return path


def _short_label(value: object, limit: int = 30) -> str:
    text = str(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _finite(values: Iterable[float]) -> np.ndarray:
    arr = np.asarray(list(values), dtype=float).reshape(-1)
    return arr[np.isfinite(arr)]


def transformed_columns_from_transformer(transformer: Any) -> list[str]:
    columns = list(getattr(transformer, "numeric_cols", []))
    for col in getattr(transformer, "categorical_cols", []):
        for level in getattr(transformer, "category_levels", {}).get(col, []):
            columns.append(f"{col}={level}")
    columns.extend(list(getattr(transformer, "passthrough_cols", [])))
    return columns


def feature_role(column: str, transformer: Any, feature_config: dict[str, Any]) -> str:
    if column in set(feature_config.get("drop_columns") or []):
        return "dropped"
    if column in set(getattr(transformer, "passthrough_cols", [])):
        return "passthrough"
    if column in set(getattr(transformer, "numeric_cols", [])):
        return "numeric"
    if column in set(getattr(transformer, "categorical_cols", [])):
        return "categorical"
    return "categorical_dropped" if feature_config.get("categorical_encoder") == "drop" else "selected"


def write_feature_summary_tables(
    *,
    df: pd.DataFrame,
    X: pd.DataFrame,
    X_train: pd.DataFrame,
    X_valid: pd.DataFrame,
    target_column: str,
    feature_columns: list[str],
    transformed_columns: list[str],
    transformer: Any,
    feature_config: dict[str, Any],
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_rows = [
        ("input_rows", len(df)),
        ("train_rows", len(X_train)),
        ("valid_rows", len(X_valid)),
        ("selected_feature_count", len(feature_columns)),
        ("numeric_feature_count", len(getattr(transformer, "numeric_cols", []))),
        ("categorical_feature_count", len(getattr(transformer, "categorical_cols", []))),
        ("passthrough_feature_count", len(getattr(transformer, "passthrough_cols", []))),
        ("dropped_feature_count", len(feature_config["drop_columns"])),
        ("transformed_feature_count", len(transformed_columns)),
        ("target_column", target_column),
        ("feature_preset", feature_config["preset"]),
        ("numeric_impute_strategy", feature_config["numeric_impute_strategy"]),
        ("categorical_impute_strategy", feature_config["categorical_impute_strategy"]),
        ("categorical_encoder", feature_config["categorical_encoder"]),
        ("scaling", feature_config["scaling"]),
    ]
    summary_path = write_table(
        pd.DataFrame([{"metric": key, "value": value} for key, value in summary_rows]),
        output_dir / "feature_summary_table.csv",
    )

    missing_rows: list[dict[str, Any]] = []
    visible_columns = list(feature_columns)
    for column in feature_config["drop_columns"]:
        if column in df.columns and column not in visible_columns:
            visible_columns.append(column)
    for column in visible_columns:
        source = df[column] if column in df.columns else X[column]
        missing_count = int(source.isna().sum())
        missing_rows.append(
            {
                "column": column,
                "role": feature_role(column, transformer, feature_config),
                "dtype": str(source.dtype),
                "missing_count": missing_count,
                "missing_rate": float(missing_count / len(source)) if len(source) else 0.0,
            }
        )
    missing_path = write_table(pd.DataFrame(missing_rows), output_dir / "missing_rate_by_column.csv")

    type_rows = []
    for role, count in {
        "numeric": len(getattr(transformer, "numeric_cols", [])),
        "categorical": len(getattr(transformer, "categorical_cols", [])),
        "passthrough": len(getattr(transformer, "passthrough_cols", [])),
        "dropped": len(feature_config["drop_columns"]),
        "transformed": len(transformed_columns),
    }.items():
        type_rows.append({"feature_type": role, "count": int(count)})
    type_counts_path = write_table(pd.DataFrame(type_rows), output_dir / "feature_type_counts.csv")
    return {
        "feature_summary_table": summary_path,
        "missing_rate_by_column": missing_path,
        "feature_type_counts": type_counts_path,
    }


def write_metrics_bar_plot(
    items: Iterable[tuple[str, float]],
    path: Path,
    *,
    title: str,
    value_label: str = "value",
    top_n: int = 20,
) -> Path:
    pairs = []
    for name, value in items:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(numeric):
            pairs.append((str(name), numeric))
    pairs.sort(key=lambda item: abs(item[1]), reverse=True)
    if top_n > 0:
        pairs = pairs[:top_n]

    row_h = 24
    width = 800
    height = max(240, 92 + row_h * max(len(pairs), 1))
    image, draw = _canvas(width, height)
    font = _font()
    draw.text((36, 18), title, fill="#243042", font=font)
    draw.text((230, height - 28), value_label, fill="#596579", font=font)
    if not pairs:
        draw.text((70, 70), f"No {value_label} available", fill="#243042", font=font)
        return _save(image, path)

    left, top, plot_w = 230, 56, 500
    max_value = max(abs(value) for _, value in pairs) or 1.0
    for index, (name, value) in enumerate(pairs):
        y = top + index * row_h
        bar_w = int(abs(value) / max_value * plot_w)
        draw.text((36, y + 4), _short_label(name), fill="#243042", font=font)
        draw.rectangle((left, y + 3, left + bar_w, y + 18), fill="#e17c45")
        draw.text((left + bar_w + 6, y + 4), f"{value:.6g}", fill="#243042", font=font)
    return _save(image, path)


def write_prediction_vs_actual_plot(y_true, y_pred, path: Path, *, title: str = "Prediction vs actual") -> Path:
    actual = _finite(y_true)
    prediction = _finite(y_pred)
    count = min(actual.size, prediction.size)
    actual = actual[:count]
    prediction = prediction[:count]

    width, height = 720, 480
    image, draw = _canvas(width, height)
    font = _font()
    left, top, plot_w, plot_h = 78, 48, 560, 340
    draw.text((left, 18), title, fill="#243042", font=font)
    draw.line((left, top + plot_h, left + plot_w, top + plot_h), fill="#596579")
    draw.line((left, top, left, top + plot_h), fill="#596579")
    draw.text((left + plot_w - 56, top + plot_h + 28), "actual", fill="#596579", font=font)
    draw.text((14, top + 4), "prediction", fill="#596579", font=font)
    if count == 0:
        draw.text((left + 20, top + 30), "No prediction data available", fill="#243042", font=font)
        return _save(image, path)

    min_value = float(min(np.min(actual), np.min(prediction)))
    max_value = float(max(np.max(actual), np.max(prediction)))
    span = max(max_value - min_value, 1e-12)
    draw.line((left, top + plot_h, left + plot_w, top), fill="#9aa4b2", width=1)
    for a, p in zip(actual, prediction):
        x = left + int((float(a) - min_value) / span * plot_w)
        y = top + plot_h - int((float(p) - min_value) / span * plot_h)
        draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill="#2878b8")
    return _save(image, path)


def write_residual_histogram(y_true, y_pred, path: Path, *, title: str = "Residual histogram") -> Path:
    actual = _finite(y_true)
    prediction = _finite(y_pred)
    count = min(actual.size, prediction.size)
    residual = actual[:count] - prediction[:count]
    return write_histogram_plot(residual, path, title=title, x_label="residual")


def write_histogram_plot(
    values: Iterable[float],
    path: Path,
    *,
    title: str,
    x_label: str,
    bins: int = 20,
) -> Path:
    arr = _finite(values)
    if arr.size == 0:
        arr = np.asarray([0.0], dtype=float)
    bins = min(max(int(bins), 5), 50)
    counts, _ = np.histogram(arr, bins=bins)

    width, height = 720, 480
    image, draw = _canvas(width, height)
    font = _font()
    left, top, plot_w, plot_h = 78, 48, 560, 340
    draw.text((left, 18), title, fill="#243042", font=font)
    draw.line((left, top + plot_h, left + plot_w, top + plot_h), fill="#596579")
    draw.line((left, top, left, top + plot_h), fill="#596579")
    draw.text((left + plot_w - 66, top + plot_h + 28), x_label, fill="#596579", font=font)
    max_count = max(int(np.max(counts)), 1)
    bar_w = plot_w / len(counts)
    for index, value in enumerate(counts):
        bar_h = int(int(value) / max_count * plot_h)
        x0 = int(left + index * bar_w)
        x1 = int(left + (index + 1) * bar_w - 2)
        y0 = top + plot_h - bar_h
        draw.rectangle((x0, y0, max(x1, x0 + 1), top + plot_h), fill="#e17c45")
    return _save(image, path)


def write_regression_plot_artifacts(y_true, y_pred, output_dir: Path, *, prefix: str = "validation") -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    scatter = write_prediction_vs_actual_plot(
        y_true,
        y_pred,
        output_dir / f"{prefix}_prediction_vs_actual.png",
        title="Prediction vs actual",
    )
    histogram = write_residual_histogram(
        y_true,
        y_pred,
        output_dir / f"{prefix}_residual_histogram.png",
        title="Residual histogram",
    )
    return {
        "prediction_vs_actual": scatter,
        "residual_histogram": histogram,
        f"{prefix}_prediction_vs_actual": scatter,
        f"{prefix}_residual_histogram": histogram,
    }


def write_leaderboard_table(rows: Iterable[dict[str, Any]], path: Path) -> Path:
    return write_table(pd.DataFrame(list(rows)), path)


def write_prediction_summary_tables(
    predictions_path: Path,
    output_dir: Path,
    *,
    target_column: str | None = None,
    preview_rows: int = 20,
) -> tuple[dict[str, Path], dict[str, Path]]:
    frame = pd.read_csv(predictions_path)
    if "prediction" not in frame.columns:
        raise ValueError("predictions.csv must contain a prediction column.")
    numeric = pd.to_numeric(frame["prediction"], errors="coerce").dropna()
    quantiles = numeric.quantile([0.25, 0.5, 0.75])
    summary_rows = [
        ("prediction_rows", int(len(frame))),
        ("prediction_mean", float(numeric.mean()) if len(numeric) else 0.0),
        ("prediction_std", float(numeric.std(ddof=0)) if len(numeric) else 0.0),
        ("prediction_min", float(numeric.min()) if len(numeric) else 0.0),
        ("prediction_p25", float(quantiles.loc[0.25]) if len(numeric) else 0.0),
        ("prediction_median", float(quantiles.loc[0.5]) if len(numeric) else 0.0),
        ("prediction_p75", float(quantiles.loc[0.75]) if len(numeric) else 0.0),
        ("prediction_max", float(numeric.max()) if len(numeric) else 0.0),
    ]
    summary_path = write_table(
        pd.DataFrame([{"metric": key, "value": value} for key, value in summary_rows]),
        output_dir / "prediction_summary.csv",
    )
    preview_path = write_table(frame.head(max(int(preview_rows), 1)), output_dir / "prediction_preview.csv")
    distribution_path = write_histogram_plot(
        numeric,
        output_dir / "prediction_distribution_histogram.png",
        title="Prediction distribution",
        x_label="prediction",
    )

    plots = {"prediction_distribution_histogram": distribution_path}
    actual_column = None
    for candidate in ("actual", "_target", target_column):
        if candidate and candidate in frame.columns:
            actual_column = candidate
            break
    if actual_column:
        actual = pd.to_numeric(frame[actual_column], errors="coerce")
        prediction = pd.to_numeric(frame["prediction"], errors="coerce")
        valid = actual.notna() & prediction.notna()
        if valid.any():
            plots.update(
                {
                    "prediction_vs_actual": write_prediction_vs_actual_plot(
                        actual[valid],
                        prediction[valid],
                        output_dir / "prediction_vs_actual.png",
                    ),
                    "residual_histogram": write_residual_histogram(
                        actual[valid],
                        prediction[valid],
                        output_dir / "residual_histogram.png",
                    ),
                }
            )
    return {"prediction_summary": summary_path, "prediction_preview": preview_path}, plots


def _feature_importance_frame(estimator: Any) -> pd.DataFrame | None:
    transformer = estimator.transformer
    columns = transformed_columns_from_transformer(transformer)
    model = estimator.model
    raw_values = None
    source = None
    if hasattr(model, "feature_importances_"):
        raw_values = np.asarray(getattr(model, "feature_importances_"), dtype=float).reshape(-1)
        source = "feature_importances_"
    elif hasattr(model, "coef_"):
        raw_values = np.asarray(getattr(model, "coef_"), dtype=float).reshape(-1)
        if raw_values.shape[0] == len(columns) + 1:
            raw_values = raw_values[1:]
        source = "coef_"
    if raw_values is None or raw_values.shape[0] != len(columns):
        return None
    frame = pd.DataFrame(
        {
            "feature": columns,
            "importance": np.abs(raw_values),
            "raw_value": raw_values,
            "source": source,
        }
    )
    frame = frame.sort_values("importance", ascending=False).reset_index(drop=True)
    frame.insert(0, "rank", range(1, len(frame) + 1))
    return frame


def write_feature_importance_plot_if_available(estimator: Any, output_dir: Path) -> tuple[Path | None, Path | None]:
    frame = _feature_importance_frame(estimator)
    if frame is None or frame.empty:
        return None, None
    table_path = write_table(frame, output_dir / "feature_importance.csv")
    plot_path = write_metrics_bar_plot(
        [(row.feature, row.importance) for row in frame.itertuples(index=False)],
        output_dir / "feature_importance.png",
        title="Feature importance",
        value_label="importance",
    )
    return table_path, plot_path


def write_metrics_by_candidate_table(metrics_by_candidate: dict[str, Any], path: Path) -> Path:
    rows = []
    for name, payload in metrics_by_candidate.items():
        metrics = payload.get("metrics", payload) if isinstance(payload, dict) else {}
        row = {
            "model_name": name,
            "artifact_kind": payload.get("artifact_kind") if isinstance(payload, dict) else None,
            "ensemble_method": payload.get("ensemble_method") if isinstance(payload, dict) else None,
            "selection_metric": payload.get("selection_metric") if isinstance(payload, dict) else None,
            "selection_value": payload.get("selection_value") if isinstance(payload, dict) else None,
        }
        if isinstance(metrics, dict):
            for metric_name, value in metrics.items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    row[str(metric_name)] = float(value)
        rows.append(row)
    return write_table(pd.DataFrame(rows), path)
