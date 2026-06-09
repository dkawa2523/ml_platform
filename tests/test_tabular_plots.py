import pandas as pd

from ml_platform_tabular.plots import (
    write_leaderboard_table,
    write_metrics_bar_plot,
    write_prediction_summary_tables,
    write_prediction_vs_actual_plot,
    write_residual_histogram,
)


def test_tabular_plot_writers_create_csv_and_png(tmp_path):
    scatter = write_prediction_vs_actual_plot([1, 2, 3], [1.1, 1.9, 3.2], tmp_path / "scatter.png")
    residual = write_residual_histogram([1, 2, 3], [1.1, 1.9, 3.2], tmp_path / "residual.png")
    bar = write_metrics_bar_plot([("ridge", 0.2), ("linear", 0.3)], tmp_path / "bar.png", title="Metrics")
    leaderboard = write_leaderboard_table(
        [{"rank": 1, "model_name": "ridge", "rmse": 0.2}],
        tmp_path / "leaderboard.csv",
    )

    predictions = tmp_path / "predictions.csv"
    pd.DataFrame({"prediction": [1.0, 2.0, 3.0]}).to_csv(predictions, index=False)
    tables, plots = write_prediction_summary_tables(predictions, tmp_path)

    for path in [scatter, residual, bar, plots["prediction_distribution_histogram"]]:
        assert path.exists()
        assert path.suffix == ".png"
        assert path.stat().st_size > 0
    assert leaderboard.exists()
    assert tables["prediction_summary"].exists()
    assert tables["prediction_preview"].exists()
