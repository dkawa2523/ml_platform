import pandas as pd

from ml_platform_tabular.plotting import (
    write_candidate_prediction_vs_actual_plot,
    write_candidate_residual_histogram,
    write_candidate_residual_vs_predicted_plot,
    write_leaderboard_table,
    write_metrics_bar_plot,
    write_prediction_summary_tables,
    write_prediction_vs_actual_plot,
    write_residual_histogram,
    write_residual_vs_predicted_plot,
)


def test_tabular_plot_writers_create_csv_and_png(tmp_path):
    scatter = write_prediction_vs_actual_plot([1, 2, 3], [1.1, 1.9, 3.2], tmp_path / "scatter.png")
    residual = write_residual_histogram([1, 2, 3], [1.1, 1.9, 3.2], tmp_path / "residual.png")
    residual_vs_predicted = write_residual_vs_predicted_plot(
        [1, 2, 3],
        [1.1, 1.9, 3.2],
        tmp_path / "residual_vs_predicted.png",
    )
    bar = write_metrics_bar_plot([("ridge", 0.2), ("linear", 0.3)], tmp_path / "bar.png", title="Metrics")
    candidate_frame = pd.DataFrame(
        {
            "candidate_name": ["ridge", "ridge", "mean_topk", "mean_topk"],
            "actual": [1.0, 2.0, 1.0, 2.0],
            "prediction": [0.9, 2.1, 1.05, 1.95],
            "residual": [0.1, -0.1, -0.05, 0.05],
        }
    )
    candidate_scatter = write_candidate_prediction_vs_actual_plot(
        candidate_frame,
        tmp_path / "candidate_scatter.png",
    )
    candidate_residual = write_candidate_residual_histogram(
        candidate_frame,
        tmp_path / "candidate_residual.png",
    )
    candidate_residual_vs_predicted = write_candidate_residual_vs_predicted_plot(
        candidate_frame,
        tmp_path / "candidate_residual_vs_predicted.png",
    )
    leaderboard = write_leaderboard_table(
        [{"rank": 1, "model_name": "ridge", "rmse": 0.2}],
        tmp_path / "leaderboard.csv",
    )

    predictions = tmp_path / "predictions.csv"
    pd.DataFrame({"prediction": [1.0, 2.0, 3.0]}).to_csv(predictions, index=False)
    tables, plots = write_prediction_summary_tables(predictions, tmp_path)

    for path in [
        scatter,
        residual,
        residual_vs_predicted,
        bar,
        candidate_scatter,
        candidate_residual,
        candidate_residual_vs_predicted,
        plots["prediction_distribution_histogram"],
    ]:
        assert path.exists()
        assert path.suffix == ".png"
        assert path.stat().st_size > 0
    assert leaderboard.exists()
    assert tables["prediction_summary"].exists()
    assert tables["prediction_preview"].exists()


def test_tabular_plotting_package_exports_new_split_boundary(tmp_path):
    path = write_leaderboard_table(
        [{"rank": 1, "model_name": "ridge", "rmse": 0.2}],
        tmp_path / "leaderboard_from_package.csv",
    )

    assert path.exists()
    assert path.suffix == ".csv"
