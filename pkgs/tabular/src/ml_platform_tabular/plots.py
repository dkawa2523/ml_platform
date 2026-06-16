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


def _paired_finite(y_true, y_pred) -> tuple[np.ndarray, np.ndarray]:
    actual = np.asarray(list(y_true), dtype=float).reshape(-1)
    prediction = np.asarray(list(y_pred), dtype=float).reshape(-1)
    count = min(actual.size, prediction.size)
    actual = actual[:count]
    prediction = prediction[:count]
    valid = np.isfinite(actual) & np.isfinite(prediction)
    return actual[valid], prediction[valid]


def _r2_score(actual: np.ndarray, prediction: np.ndarray) -> float | None:
    if actual.size == 0:
        return None
    ss_res = float(np.sum((actual - prediction) ** 2))
    ss_tot = float(np.sum((actual - float(np.mean(actual))) ** 2))
    if ss_tot <= 1e-12:
        return None
    return 1.0 - ss_res / ss_tot


def _value_range(*arrays: np.ndarray) -> tuple[float, float, float]:
    values = np.concatenate([arr.reshape(-1) for arr in arrays if arr.size])
    if values.size == 0:
        return 0.0, 1.0, 1.0
    min_value = float(np.min(values))
    max_value = float(np.max(values))
    span = max(max_value - min_value, 1e-12)
    return min_value, max_value, span


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
    sort: str = "abs_desc",
) -> Path:
    pairs = []
    for name, value in items:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(numeric):
            pairs.append((str(name), numeric))
    if sort == "input":
        pass
    elif sort == "value_asc":
        pairs.sort(key=lambda item: item[1])
    elif sort == "value_desc":
        pairs.sort(key=lambda item: item[1], reverse=True)
    else:
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
        fill = "#2878b8" if index == 0 and sort in {"input", "value_asc", "value_desc"} else "#e17c45"
        draw.text((36, y + 4), _short_label(name), fill="#243042", font=font)
        draw.rectangle((left, y + 3, left + bar_w, y + 18), fill=fill)
        draw.text((left + bar_w + 6, y + 4), f"{value:.6g}", fill="#243042", font=font)
    return _save(image, path)


def write_prediction_vs_actual_plot(y_true, y_pred, path: Path, *, title: str = "Prediction vs actual") -> Path:
    actual, prediction = _paired_finite(y_true, y_pred)
    count = actual.size

    width, height = 720, 480
    image, draw = _canvas(width, height)
    font = _font()
    left, top, plot_w, plot_h = 78, 48, 560, 340
    r2 = _r2_score(actual, prediction)
    title_text = title if r2 is None else f"{title} (R2={r2:.3f})"
    draw.text((left, 18), title_text, fill="#243042", font=font)
    draw.line((left, top + plot_h, left + plot_w, top + plot_h), fill="#596579")
    draw.line((left, top, left, top + plot_h), fill="#596579")
    draw.text((left + plot_w - 56, top + plot_h + 28), "actual", fill="#596579", font=font)
    draw.text((14, top + 4), "prediction", fill="#596579", font=font)
    if count == 0:
        draw.text((left + 20, top + 30), "No prediction data available", fill="#243042", font=font)
        return _save(image, path)

    min_value, max_value, span = _value_range(actual, prediction)
    draw.line((left, top + plot_h, left + plot_w, top), fill="#9aa4b2", width=1)
    draw.text((left + plot_w - 40, top + 8), "y=x", fill="#596579", font=font)
    for a, p in zip(actual, prediction):
        x = left + int((float(a) - min_value) / span * plot_w)
        y = top + plot_h - int((float(p) - min_value) / span * plot_h)
        draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill="#2878b8")
    return _save(image, path)


def write_residual_histogram(y_true, y_pred, path: Path, *, title: str = "Residual histogram") -> Path:
    actual, prediction = _paired_finite(y_true, y_pred)
    residual = actual - prediction
    return write_histogram_plot(residual, path, title=title, x_label="residual (actual - prediction)")


def write_residual_vs_predicted_plot(y_true, y_pred, path: Path, *, title: str = "Residuals vs predicted") -> Path:
    actual, prediction = _paired_finite(y_true, y_pred)
    residual = actual - prediction

    width, height = 720, 480
    image, draw = _canvas(width, height)
    font = _font()
    left, top, plot_w, plot_h = 78, 48, 560, 340
    draw.text((left, 18), title, fill="#243042", font=font)
    draw.line((left, top + plot_h, left + plot_w, top + plot_h), fill="#596579")
    draw.line((left, top, left, top + plot_h), fill="#596579")
    draw.text((left + plot_w - 74, top + plot_h + 28), "prediction", fill="#596579", font=font)
    draw.text((14, top + 4), "residual", fill="#596579", font=font)
    if prediction.size == 0:
        draw.text((left + 20, top + 30), "No residual data available", fill="#243042", font=font)
        return _save(image, path)

    x_min, _, x_span = _value_range(prediction)
    y_min, y_max, y_span = _value_range(residual)
    if y_min <= 0.0 <= y_max:
        zero_y = top + plot_h - int((0.0 - y_min) / y_span * plot_h)
        draw.line((left, zero_y, left + plot_w, zero_y), fill="#9aa4b2", width=1)
        draw.text((left + plot_w - 32, zero_y + 4), "0", fill="#596579", font=font)
    for p, r in zip(prediction, residual):
        x = left + int((float(p) - x_min) / x_span * plot_w)
        y = top + plot_h - int((float(r) - y_min) / y_span * plot_h)
        draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill="#e17c45")
    return _save(image, path)


def write_histogram_plot(
    values: Iterable[float],
    path: Path,
    *,
    title: str,
    x_label: str,
    y_label: str = "count",
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
    draw.text((16, top + 18), y_label, fill="#596579", font=font)
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
    residual_vs_predicted = write_residual_vs_predicted_plot(
        y_true,
        y_pred,
        output_dir / f"{prefix}_residual_vs_predicted.png",
        title="Residuals vs predicted",
    )
    return {
        f"{prefix}_prediction_vs_actual": scatter,
        f"{prefix}_residual_histogram": histogram,
        f"{prefix}_residual_vs_predicted": residual_vs_predicted,
    }


def _candidate_groups(frame: pd.DataFrame):
    if "candidate_name" in frame.columns:
        return frame.groupby("candidate_name", sort=False)
    return [("candidate", frame)]


def topk_candidate_predictions(frame: pd.DataFrame, *, top_k: int = 5) -> pd.DataFrame:
    if top_k <= 0 or frame.empty:
        return frame.copy()
    if "candidate_rank" in frame.columns:
        ranks = pd.to_numeric(frame["candidate_rank"], errors="coerce")
        top = frame[ranks.notna() & (ranks <= top_k)].copy()
        if not top.empty:
            return top
    if "candidate_name" not in frame.columns:
        return frame.copy()
    names = list(dict.fromkeys(str(value) for value in frame["candidate_name"].dropna()))
    keep = set(names[:top_k])
    return frame[frame["candidate_name"].astype(str).isin(keep)].copy()


def write_candidate_prediction_vs_actual_plot(frame: pd.DataFrame, path: Path, *, title: str = "Candidate prediction vs actual") -> Path:
    width, height = 780, 520
    image, draw = _canvas(width, height)
    font = _font()
    left, top, plot_w, plot_h = 86, 54, 560, 350
    actual_all = pd.to_numeric(frame.get("actual"), errors="coerce") if "actual" in frame else pd.Series(dtype=float)
    pred_all = pd.to_numeric(frame.get("prediction"), errors="coerce") if "prediction" in frame else pd.Series(dtype=float)
    valid_all = actual_all.notna() & pred_all.notna()
    actual_values = actual_all[valid_all].to_numpy(dtype=float)
    pred_values = pred_all[valid_all].to_numpy(dtype=float)
    _, _, span = _value_range(actual_values, pred_values)
    min_value = float(min(np.min(actual_values), np.min(pred_values))) if actual_values.size else 0.0

    draw.text((left, 18), title, fill="#243042", font=font)
    draw.line((left, top + plot_h, left + plot_w, top + plot_h), fill="#596579")
    draw.line((left, top, left, top + plot_h), fill="#596579")
    draw.text((left + plot_w - 56, top + plot_h + 28), "actual", fill="#596579", font=font)
    draw.text((14, top + 4), "prediction", fill="#596579", font=font)
    if not actual_values.size:
        draw.text((left + 20, top + 30), "No candidate prediction data available", fill="#243042", font=font)
        return _save(image, path)
    draw.line((left, top + plot_h, left + plot_w, top), fill="#9aa4b2", width=1)
    draw.text((left + plot_w - 40, top + 8), "y=x", fill="#596579", font=font)
    for index, (candidate, group) in enumerate(_candidate_groups(frame)):
        color = PALETTE[index % len(PALETTE)]
        actual = pd.to_numeric(group["actual"], errors="coerce")
        prediction = pd.to_numeric(group["prediction"], errors="coerce")
        valid = actual.notna() & prediction.notna()
        for a, p in zip(actual[valid], prediction[valid]):
            x = left + int((float(a) - min_value) / span * plot_w)
            y = top + plot_h - int((float(p) - min_value) / span * plot_h)
            draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=color)
        legend_y = 58 + index * 18
        draw.rectangle((665, legend_y + 4, 675, legend_y + 14), fill=color)
        draw.text((682, legend_y), _short_label(candidate, 20), fill="#243042", font=font)
    return _save(image, path)


def write_candidate_residual_vs_predicted_plot(frame: pd.DataFrame, path: Path, *, title: str = "Candidate residuals vs predicted") -> Path:
    width, height = 780, 520
    image, draw = _canvas(width, height)
    font = _font()
    left, top, plot_w, plot_h = 86, 54, 560, 350
    prediction_all = pd.to_numeric(frame.get("prediction"), errors="coerce") if "prediction" in frame else pd.Series(dtype=float)
    residual_all = pd.to_numeric(frame.get("residual"), errors="coerce") if "residual" in frame else pd.Series(dtype=float)
    valid_all = prediction_all.notna() & residual_all.notna()
    pred_values = prediction_all[valid_all].to_numpy(dtype=float)
    residual_values = residual_all[valid_all].to_numpy(dtype=float)
    x_min, _, x_span = _value_range(pred_values)
    y_min, y_max, y_span = _value_range(residual_values)

    draw.text((left, 18), title, fill="#243042", font=font)
    draw.line((left, top + plot_h, left + plot_w, top + plot_h), fill="#596579")
    draw.line((left, top, left, top + plot_h), fill="#596579")
    draw.text((left + plot_w - 74, top + plot_h + 28), "prediction", fill="#596579", font=font)
    draw.text((14, top + 4), "residual", fill="#596579", font=font)
    if not pred_values.size:
        draw.text((left + 20, top + 30), "No candidate residual data available", fill="#243042", font=font)
        return _save(image, path)
    if y_min <= 0.0 <= y_max:
        zero_y = top + plot_h - int((0.0 - y_min) / y_span * plot_h)
        draw.line((left, zero_y, left + plot_w, zero_y), fill="#9aa4b2", width=1)
    for index, (candidate, group) in enumerate(_candidate_groups(frame)):
        color = PALETTE[index % len(PALETTE)]
        prediction = pd.to_numeric(group["prediction"], errors="coerce")
        residual = pd.to_numeric(group["residual"], errors="coerce")
        valid = prediction.notna() & residual.notna()
        for p, r in zip(prediction[valid], residual[valid]):
            x = left + int((float(p) - x_min) / x_span * plot_w)
            y = top + plot_h - int((float(r) - y_min) / y_span * plot_h)
            draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=color)
        legend_y = 58 + index * 18
        draw.rectangle((665, legend_y + 4, 675, legend_y + 14), fill=color)
        draw.text((682, legend_y), _short_label(candidate, 20), fill="#243042", font=font)
    return _save(image, path)


def write_candidate_residual_histogram(frame: pd.DataFrame, path: Path, *, title: str = "Candidate residual histogram", bins: int = 20) -> Path:
    width, height = 780, 520
    image, draw = _canvas(width, height)
    font = _font()
    left, top, plot_w, plot_h = 86, 54, 560, 350
    residual_all = pd.to_numeric(frame.get("residual"), errors="coerce") if "residual" in frame else pd.Series(dtype=float)
    residual_values = residual_all.dropna().to_numpy(dtype=float)
    if residual_values.size == 0:
        residual_values = np.asarray([0.0], dtype=float)
    bins = min(max(int(bins), 5), 50)
    counts_all, edges = np.histogram(residual_values, bins=bins)
    max_count = max(int(np.max(counts_all)), 1)
    x_min, x_max = float(edges[0]), float(edges[-1])
    x_span = max(x_max - x_min, 1e-12)
    centers = (edges[:-1] + edges[1:]) / 2.0

    draw.text((left, 18), title, fill="#243042", font=font)
    draw.line((left, top + plot_h, left + plot_w, top + plot_h), fill="#596579")
    draw.line((left, top, left, top + plot_h), fill="#596579")
    draw.text((left + plot_w - 170, top + plot_h + 28), "residual (actual - prediction)", fill="#596579", font=font)
    draw.text((16, top + 18), "count", fill="#596579", font=font)
    for index, (candidate, group) in enumerate(_candidate_groups(frame)):
        color = PALETTE[index % len(PALETTE)]
        residual = pd.to_numeric(group["residual"], errors="coerce").dropna().to_numpy(dtype=float)
        if residual.size == 0:
            continue
        counts, _ = np.histogram(residual, bins=edges)
        points = []
        for center, count in zip(centers, counts):
            x = left + int((float(center) - x_min) / x_span * plot_w)
            y = top + plot_h - int(float(count) / max_count * plot_h)
            points.append((x, y))
        for start, end in zip(points, points[1:]):
            draw.line((*start, *end), fill=color, width=2)
        legend_y = 58 + index * 18
        draw.rectangle((665, legend_y + 4, 675, legend_y + 14), fill=color)
        draw.text((682, legend_y), _short_label(candidate, 20), fill="#243042", font=font)
    return _save(image, path)


def write_leaderboard_table(rows: Iterable[dict[str, Any]], path: Path) -> Path:
    return write_table(pd.DataFrame(list(rows)), path)


def write_leaderboard_metric_panel(
    rows: Iterable[dict[str, Any]],
    path: Path,
    *,
    metrics: Iterable[str] = ("rmse", "mae", "r2"),
    top_k: int = 5,
) -> Path:
    view = list(rows)[: max(int(top_k), 1)]
    metric_names = list(metrics)
    width = 900
    row_h = 24
    panel_h = 56 + row_h * max(len(view), 1)
    height = 34 + panel_h * len(metric_names)
    image, draw = _canvas(width, height)
    font = _font()
    draw.text((34, 14), f"Leaderboard metric panel (top {len(view)})", fill="#243042", font=font)
    if not view:
        draw.text((56, 70), "No leaderboard rows available", fill="#243042", font=font)
        return _save(image, path)

    for metric_index, metric in enumerate(metric_names):
        panel_top = 42 + metric_index * panel_h
        items: list[tuple[str, float, bool]] = []
        for row in view:
            value = row.get(metric)
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            if np.isfinite(numeric):
                label = f"{row.get('rank', '?')}:{row.get('model_name', 'unknown')}"
                items.append((label, numeric, int(row.get("rank", 0) or 0) == 1))
        draw.text((34, panel_top), metric, fill="#243042", font=font)
        if not items:
            draw.text((76, panel_top + 28), f"No {metric} available", fill="#596579", font=font)
            continue
        max_value = max(abs(value) for _, value, _ in items) or 1.0
        left, plot_w = 230, 500
        for index, (label, value, is_best) in enumerate(items):
            y = panel_top + 26 + index * row_h
            bar_w = int(abs(value) / max_value * plot_w)
            fill = "#2878b8" if is_best else "#e17c45"
            draw.text((54, y + 4), _short_label(label, 28), fill="#243042", font=font)
            draw.rectangle((left, y + 3, left + bar_w, y + 18), fill=fill)
            draw.text((left + bar_w + 6, y + 4), f"{value:.6g}", fill="#243042", font=font)
    return _save(image, path)


def write_leaderboard_pareto_plot(
    rows: Iterable[dict[str, Any]],
    path: Path,
    *,
    x_metric: str = "r2",
    y_metric: str = "rmse",
    top_k: int = 10,
) -> Path:
    view = list(rows)[: max(int(top_k), 1)]
    points: list[tuple[str, float, float, bool]] = []
    for row in view:
        try:
            x_value = float(row.get(x_metric))
            y_value = float(row.get(y_metric))
        except (TypeError, ValueError):
            continue
        if np.isfinite(x_value) and np.isfinite(y_value):
            label = f"{row.get('rank', '?')}:{row.get('model_name', 'unknown')}"
            points.append((label, x_value, y_value, int(row.get("rank", 0) or 0) == 1))

    width, height = 760, 500
    image, draw = _canvas(width, height)
    font = _font()
    left, top, plot_w, plot_h = 86, 54, 540, 340
    draw.text((left, 18), f"Leaderboard Pareto: {x_metric} vs {y_metric}", fill="#243042", font=font)
    draw.line((left, top + plot_h, left + plot_w, top + plot_h), fill="#596579")
    draw.line((left, top, left, top + plot_h), fill="#596579")
    draw.text((left + plot_w - 56, top + plot_h + 28), x_metric, fill="#596579", font=font)
    draw.text((16, top + 18), y_metric, fill="#596579", font=font)
    if not points:
        draw.text((left + 20, top + 30), "No comparable leaderboard metrics available", fill="#243042", font=font)
        return _save(image, path)

    x_values = np.asarray([item[1] for item in points], dtype=float)
    y_values = np.asarray([item[2] for item in points], dtype=float)
    x_min, _, x_span = _value_range(x_values)
    y_min, _, y_span = _value_range(y_values)
    for label, x_value, y_value, is_best in points:
        x = left + int((x_value - x_min) / x_span * plot_w)
        y = top + plot_h - int((y_value - y_min) / y_span * plot_h)
        fill = "#2878b8" if is_best else "#e17c45"
        radius = 5 if is_best else 4
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill)
        draw.text((x + 6, y - 6), _short_label(label, 18), fill="#243042", font=font)
    return _save(image, path)


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
    for candidate in ("actual", target_column):
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
                    "residual_vs_predicted": write_residual_vs_predicted_plot(
                        actual[valid],
                        prediction[valid],
                        output_dir / "residual_vs_predicted.png",
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
