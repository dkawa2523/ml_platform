from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml_platform_core.io import write_table

from .common import PALETTE, _canvas, _font, _save, _short_label, _value_range


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


def write_candidate_prediction_vs_actual_plot(
    frame: pd.DataFrame,
    path: Path,
    *,
    title: str = "Candidate prediction vs actual",
) -> Path:
    width, height = 780, 520
    image, draw = _canvas(width, height)
    font = _font()
    left, top, plot_w, plot_h = 86, 54, 560, 350
    actual_all = pd.to_numeric(frame.get("actual"), errors="coerce") if "actual" in frame else pd.Series(dtype=float)
    pred_all = (
        pd.to_numeric(frame.get("prediction"), errors="coerce") if "prediction" in frame else pd.Series(dtype=float)
    )
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


def write_candidate_residual_vs_predicted_plot(
    frame: pd.DataFrame,
    path: Path,
    *,
    title: str = "Candidate residuals vs predicted",
) -> Path:
    width, height = 780, 520
    image, draw = _canvas(width, height)
    font = _font()
    left, top, plot_w, plot_h = 86, 54, 560, 350
    prediction_all = (
        pd.to_numeric(frame.get("prediction"), errors="coerce") if "prediction" in frame else pd.Series(dtype=float)
    )
    residual_all = (
        pd.to_numeric(frame.get("residual"), errors="coerce") if "residual" in frame else pd.Series(dtype=float)
    )
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


def write_candidate_residual_histogram(
    frame: pd.DataFrame,
    path: Path,
    *,
    title: str = "Candidate residual histogram",
    bins: int = 20,
) -> Path:
    width, height = 780, 520
    image, draw = _canvas(width, height)
    font = _font()
    left, top, plot_w, plot_h = 86, 54, 560, 350
    residual_all = (
        pd.to_numeric(frame.get("residual"), errors="coerce") if "residual" in frame else pd.Series(dtype=float)
    )
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


def write_metrics_by_candidate_table(metrics_by_candidate: dict[str, Any], path: Path) -> Path:
    rows = [_metrics_by_candidate_row(name, payload) for name, payload in metrics_by_candidate.items()]
    return write_table(pd.DataFrame(rows), path)


def _metrics_by_candidate_row(name: str, payload: Any) -> dict[str, Any]:
    payload_dict = payload if isinstance(payload, dict) else {}
    row = {
        "model_name": name,
        "artifact_kind": payload_dict.get("artifact_kind"),
        "ensemble_method": payload_dict.get("ensemble_method"),
        "selection_metric": payload_dict.get("selection_metric"),
        "selection_value": payload_dict.get("selection_value"),
    }
    row.update(_numeric_metrics(payload_dict.get("metrics", payload_dict)))
    return row


def _numeric_metrics(metrics: Any) -> dict[str, float]:
    if not isinstance(metrics, dict):
        return {}
    return {
        str(metric_name): float(value)
        for metric_name, value in metrics.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }
