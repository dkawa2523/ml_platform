from __future__ import annotations

from pathlib import Path

from .common import (
    _canvas,
    _font,
    _paired_finite,
    _r2_score,
    _save,
    _value_range,
    write_histogram_plot,
)


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

    min_value, _, span = _value_range(actual, prediction)
    draw.line((left, top + plot_h, left + plot_w, top), fill="#9aa4b2", width=1)
    draw.text((left + plot_w - 40, top + 8), "y=x", fill="#596579", font=font)
    for a, p in zip(actual, prediction, strict=True):
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
    for p, r in zip(prediction, residual, strict=True):
        x = left + int((float(p) - x_min) / x_span * plot_w)
        y = top + plot_h - int((float(r) - y_min) / y_span * plot_h)
        draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill="#e17c45")
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
