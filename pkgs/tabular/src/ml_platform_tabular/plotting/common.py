from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageFont


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


def write_metrics_bar_plot(
    items: Iterable[tuple[str, float]],
    path: Path,
    *,
    title: str,
    value_label: str = "value",
    top_n: int = 20,
    sort: str = "abs_desc",
) -> Path:
    pairs = _metric_pairs(items, sort=sort, top_n=top_n)
    image, draw = _bar_plot_canvas(pairs, title=title, value_label=value_label)
    if not pairs:
        return _save(image, path)
    _draw_bar_rows(draw, pairs, sort=sort)
    return _save(image, path)


def _metric_pairs(
    items: Iterable[tuple[str, float]],
    *,
    sort: str,
    top_n: int,
) -> list[tuple[str, float]]:
    pairs = []
    for name, value in items:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(numeric):
            pairs.append((str(name), numeric))
    _sort_metric_pairs(pairs, sort)
    return pairs[:top_n] if top_n > 0 else pairs


def _sort_metric_pairs(pairs: list[tuple[str, float]], sort: str) -> None:
    if sort == "input":
        return
    if sort == "value_asc":
        pairs.sort(key=lambda item: item[1])
    elif sort == "value_desc":
        pairs.sort(key=lambda item: item[1], reverse=True)
    else:
        pairs.sort(key=lambda item: abs(item[1]), reverse=True)


def _bar_plot_canvas(
    pairs: list[tuple[str, float]],
    *,
    title: str,
    value_label: str,
) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    row_h = 24
    width = 800
    height = max(240, 92 + row_h * max(len(pairs), 1))
    image, draw = _canvas(width, height)
    font = _font()
    draw.text((36, 18), title, fill="#243042", font=font)
    draw.text((230, height - 28), value_label, fill="#596579", font=font)
    if not pairs:
        draw.text((70, 70), f"No {value_label} available", fill="#243042", font=font)
    return image, draw


def _draw_bar_rows(draw: ImageDraw.ImageDraw, pairs: list[tuple[str, float]], *, sort: str) -> None:
    font = _font()
    row_h = 24
    left, top, plot_w = 230, 56, 500
    max_value = max(abs(value) for _, value in pairs) or 1.0
    for index, (name, value) in enumerate(pairs):
        y = top + index * row_h
        bar_w = int(abs(value) / max_value * plot_w)
        fill = "#2878b8" if index == 0 and sort in {"input", "value_asc", "value_desc"} else "#e17c45"
        draw.text((36, y + 4), _short_label(name), fill="#243042", font=font)
        draw.rectangle((left, y + 3, left + bar_w, y + 18), fill=fill)
        draw.text((left + bar_w + 6, y + 4), f"{value:.6g}", fill="#243042", font=font)


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
