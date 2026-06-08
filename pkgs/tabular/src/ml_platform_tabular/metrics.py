from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

DEFAULT_REGRESSION_METRICS = ("mae", "rmse", "r2")


def _normalize_metric_name(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _normalize_metric_names(metrics: Iterable[str] | str | None) -> tuple[str, ...]:
    if metrics is None:
        return DEFAULT_REGRESSION_METRICS
    if isinstance(metrics, str):
        names = tuple(name.strip() for name in metrics.split(",") if name.strip())
    else:
        names = tuple(metrics)
    if not names:
        raise ValueError("At least one regression metric is required.")
    return names


def regression_metrics(y_true, y_pred, metrics: Iterable[str] | str | None = None) -> dict[str, float]:
    y_true = np.asarray(y_true, dtype=float).reshape(-1)
    y_pred = np.asarray(y_pred, dtype=float).reshape(-1)
    if y_true.shape[0] != y_pred.shape[0]:
        raise ValueError("y_true and y_pred must have the same length.")
    if y_true.shape[0] == 0:
        raise ValueError("y_true and y_pred must not be empty.")

    residual = y_true - y_pred
    mae = float(np.mean(np.abs(residual)))
    mse = float(np.mean(residual**2))
    rmse = float(np.sqrt(mse))
    denom = float(np.sum((y_true - np.mean(y_true)) ** 2))
    r2 = 1.0 - float(np.sum(residual**2)) / denom if denom else 0.0

    values = {"mae": mae, "rmse": rmse, "r2": float(r2), "mse": mse}
    selected = _normalize_metric_names(metrics)
    result: dict[str, float] = {}
    for name in selected:
        key = _normalize_metric_name(name)
        if not key:
            continue
        if key not in values:
            raise ValueError(f"Unsupported regression metric: {name}")
        result[key] = values[key]
    return result


def regression_prediction_frame(base_frame, y_true, y_pred, *, model_name: str | None = None) -> pd.DataFrame:
    """Return a compact prediction table with residual columns."""
    frame = pd.DataFrame(base_frame).reset_index(drop=True).copy()
    actual = np.asarray(y_true, dtype=float).reshape(-1)
    prediction = np.asarray(y_pred, dtype=float).reshape(-1)
    if len(frame) != actual.shape[0] or actual.shape[0] != prediction.shape[0]:
        raise ValueError("Prediction frame, y_true, and y_pred must have the same length.")
    residual = actual - prediction
    frame["actual"] = actual
    frame["prediction"] = prediction
    frame["residual"] = residual
    frame["abs_error"] = np.abs(residual)
    # Deprecated compatibility columns kept for older notebooks/artifacts.
    frame["_target"] = actual
    frame["_prediction"] = prediction
    if model_name:
        frame["model_name"] = model_name
    return frame


def _scale(values: np.ndarray, size: int, *, lower_is_better: bool = False) -> np.ndarray:
    min_value = float(np.min(values))
    max_value = float(np.max(values))
    if max_value == min_value:
        scaled = np.full_like(values, size / 2, dtype=float)
    else:
        scaled = (values - min_value) / (max_value - min_value) * size
    return size - scaled if lower_is_better else scaled


def _write_svg(path: Path, body: str, *, width: int = 640, height: int = 420) -> Path:
    path.write_text(
        "\n".join(
            [
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
                '<rect width="100%" height="100%" fill="white"/>',
                '<style>text{font-family:Arial,sans-serif;font-size:13px;fill:#243042}.axis{stroke:#596579;stroke-width:1}.dot{fill:#2878b8;opacity:.65}.bar{fill:#e17c45;opacity:.8}</style>',
                body,
                "</svg>",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def write_metrics_by_model_bar_artifact(
    metrics_by_model: dict[str, Any],
    output_dir: Path,
    *,
    metric_names: Iterable[str] = DEFAULT_REGRESSION_METRICS,
) -> Path:
    """Write a compact grouped bar chart for model metrics."""
    output_dir.mkdir(parents=True, exist_ok=True)
    model_items: list[tuple[str, dict[str, float]]] = []
    for model_name, payload in metrics_by_model.items():
        metrics = payload.get("metrics", payload) if isinstance(payload, dict) else {}
        if isinstance(metrics, dict):
            numeric_metrics = {
                str(name): float(value)
                for name, value in metrics.items()
                if isinstance(value, (int, float)) and not isinstance(value, bool)
            }
            if numeric_metrics:
                model_items.append((str(model_name), numeric_metrics))

    names = [name for name in (_normalize_metric_name(item) for item in metric_names) if name]
    names = [name for name in names if any(name in metrics for _, metrics in model_items)]
    if not model_items or not names:
        return _write_svg(
            output_dir / "metrics_by_model_bar.svg",
            '<text x="70" y="40">No model metrics available</text>',
            width=720,
            height=420,
        )

    width, height = 720, 420
    left, top, plot_w, plot_h = 70, 54, 610, 270
    palette = ["#2878b8", "#e17c45", "#59a14f", "#b07aa1"]
    max_value = max(max(metrics.get(name, 0.0) for name in names) for _, metrics in model_items)
    min_value = min(min(metrics.get(name, 0.0) for name in names) for _, metrics in model_items)
    baseline = 0.0 if min_value >= 0 else min_value
    span = max(max_value - baseline, 1e-12)
    group_w = plot_w / max(len(model_items), 1)
    bar_w = max(group_w / (len(names) + 1), 4)

    bars = []
    labels = []
    for model_index, (model_name, metrics) in enumerate(model_items):
        group_x = left + model_index * group_w
        labels.append(
            f'<text x="{group_x + group_w / 2:.1f}" y="{top + plot_h + 34}" '
            'text-anchor="middle" transform="rotate(20 '
            f'{group_x + group_w / 2:.1f},{top + plot_h + 34})">{model_name}</text>'
        )
        for metric_index, metric_name in enumerate(names):
            value = metrics.get(metric_name)
            if value is None:
                continue
            bar_h = (float(value) - baseline) / span * plot_h
            bx = group_x + (metric_index + 0.5) * bar_w
            by = top + plot_h - bar_h
            color = palette[metric_index % len(palette)]
            bars.append(
                f'<rect x="{bx:.1f}" y="{by:.1f}" width="{max(bar_w - 2, 1):.1f}" '
                f'height="{bar_h:.1f}" fill="{color}" opacity=".85"/>'
            )

    legend = []
    for index, metric_name in enumerate(names):
        x = left + index * 120
        color = palette[index % len(palette)]
        legend.append(f'<rect x="{x}" y="18" width="12" height="12" fill="{color}" opacity=".85"/>')
        legend.append(f'<text x="{x + 18}" y="29">{metric_name}</text>')

    body = (
        f'<text x="{left}" y="44">Metrics by model</text>'
        f'<line class="axis" x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}"/>'
        f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}"/>'
        + "".join(legend)
        + "".join(bars)
        + "".join(labels)
    )
    return _write_svg(output_dir / "metrics_by_model_bar.svg", body, width=width, height=height)


def write_regression_plot_artifacts(y_true, y_pred, output_dir: Path, *, prefix: str = "validation") -> dict[str, Path]:
    """Write two lightweight SVG artifacts for ClearML upload."""
    output_dir.mkdir(parents=True, exist_ok=True)
    actual = np.asarray(y_true, dtype=float).reshape(-1)
    prediction = np.asarray(y_pred, dtype=float).reshape(-1)
    residual = actual - prediction
    width, height = 640, 420
    left, top, plot_w, plot_h = 70, 40, 520, 300

    x = left + _scale(actual, plot_w)
    y = top + _scale(prediction, plot_h, lower_is_better=True)
    diag = (
        f'<line class="axis" x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top}" '
        'stroke-dasharray="4 4"/>'
    )
    dots = "".join(f'<circle class="dot" cx="{float(px):.1f}" cy="{float(py):.1f}" r="3"/>' for px, py in zip(x, y))
    scatter_body = (
        f'<text x="{left}" y="24">Prediction vs actual</text>'
        f'<line class="axis" x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}"/>'
        f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}"/>'
        f"{diag}{dots}"
        f'<text x="{left + plot_w - 60}" y="{top + plot_h + 36}">actual</text>'
        f'<text x="16" y="{top + 12}">prediction</text>'
    )

    counts, edges = np.histogram(residual, bins=min(20, max(5, int(np.sqrt(len(residual))))))
    max_count = max(int(np.max(counts)), 1)
    bar_w = plot_w / len(counts)
    bars = ""
    for index, count in enumerate(counts):
        bar_h = (int(count) / max_count) * plot_h
        bx = left + index * bar_w
        by = top + plot_h - bar_h
        bars += f'<rect class="bar" x="{bx:.1f}" y="{by:.1f}" width="{max(bar_w - 2, 1):.1f}" height="{bar_h:.1f}"/>'
    hist_body = (
        f'<text x="{left}" y="24">Residual histogram</text>'
        f'<line class="axis" x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}"/>'
        f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}"/>'
        f"{bars}"
        f'<text x="{left + plot_w - 70}" y="{top + plot_h + 36}">residual</text>'
    )

    return {
        "prediction_vs_actual": _write_svg(output_dir / f"{prefix}_prediction_vs_actual.svg", scatter_body, width=width, height=height),
        "residual_histogram": _write_svg(output_dir / f"{prefix}_residual_histogram.svg", hist_body, width=width, height=height),
    }
