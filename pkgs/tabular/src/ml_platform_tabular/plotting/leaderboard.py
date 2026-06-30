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
        draw.text((34, panel_top), metric, fill="#243042", font=font)
        items = _metric_panel_items(view, metric)
        if not items:
            draw.text((76, panel_top + 28), f"No {metric} available", fill="#596579", font=font)
            continue
        _draw_metric_panel_items(draw, items, panel_top=panel_top, row_h=row_h)
    return _save(image, path)


def _metric_panel_items(rows: list[dict[str, Any]], metric: str) -> list[tuple[str, float, bool]]:
    items: list[tuple[str, float, bool]] = []
    for row in rows:
        value = _finite_metric_value(row, metric)
        if value is None:
            continue
        label = f"{row.get('rank', '?')}:{row.get('model_name', 'unknown')}"
        items.append((label, value, _is_best_rank(row)))
    return items


def _finite_metric_value(row: dict[str, Any], metric: str) -> float | None:
    try:
        value = float(row.get(metric))
    except (TypeError, ValueError):
        return None
    return value if np.isfinite(value) else None


def _is_best_rank(row: dict[str, Any]) -> bool:
    return int(row.get("rank", 0) or 0) == 1


def _draw_metric_panel_items(
    draw,
    items: list[tuple[str, float, bool]],
    *,
    panel_top: int,
    row_h: int,
) -> None:
    font = _font()
    left, plot_w = 230, 500
    max_value = max(abs(value) for _, value, _ in items) or 1.0
    for index, (label, value, is_best) in enumerate(items):
        y = panel_top + 26 + index * row_h
        bar_w = int(abs(value) / max_value * plot_w)
        fill = "#2878b8" if is_best else "#e17c45"
        draw.text((54, y + 4), _short_label(label, 28), fill="#243042", font=font)
        draw.rectangle((left, y + 3, left + bar_w, y + 18), fill=fill)
        draw.text((left + bar_w + 6, y + 4), f"{value:.6g}", fill="#243042", font=font)


def write_leaderboard_pareto_plot(
    rows: Iterable[dict[str, Any]],
    path: Path,
    *,
    x_metric: str = "r2",
    y_metric: str = "rmse",
    top_k: int = 10,
) -> Path:
    view = list(rows)[: max(int(top_k), 1)]
    points = _pareto_points(view, x_metric=x_metric, y_metric=y_metric)

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

    _draw_pareto_points(draw, points, left=left, top=top, plot_w=plot_w, plot_h=plot_h)
    return _save(image, path)


def _pareto_points(
    rows: list[dict[str, Any]],
    *,
    x_metric: str,
    y_metric: str,
) -> list[tuple[str, float, float, bool]]:
    points: list[tuple[str, float, float, bool]] = []
    for row in rows:
        x_value = _finite_metric_value(row, x_metric)
        y_value = _finite_metric_value(row, y_metric)
        if x_value is None or y_value is None:
            continue
        label = f"{row.get('rank', '?')}:{row.get('model_name', 'unknown')}"
        points.append((label, x_value, y_value, _is_best_rank(row)))
    return points


def _draw_pareto_points(
    draw,
    points: list[tuple[str, float, float, bool]],
    *,
    left: int,
    top: int,
    plot_w: int,
    plot_h: int,
) -> None:
    font = _font()
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
