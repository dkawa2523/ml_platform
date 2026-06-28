from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from ml_platform_core.io import write_table

from .common import _canvas, _font, _save, _short_label, _value_range


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
