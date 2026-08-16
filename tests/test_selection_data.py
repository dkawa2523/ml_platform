import pandas as pd
from ml_platform_tabular.target_sources import SOURCE_ROW_COLUMN
from ml_platform_tabular.training.preprocess_data import prepare_preprocess
from ml_platform_tabular.training.selection_data import selection_split


def test_selection_split_is_disjoint_from_final_test_and_preserves_groups(tmp_path):
    frame = pd.DataFrame(
        {
            "id": range(30),
            "group": [f"g{index // 5}" for index in range(30)],
            "feature": [float(index) for index in range(30)],
            "target": [float(index % 7) for index in range(30)],
        }
    )
    path = tmp_path / "train.csv"
    frame.to_csv(path, index=False)
    cfg = {
        "task": "tabular_pipeline",
        "run": {"seed": 7},
        "data": {"local_path": str(path), "target_column": "target", "id_columns": ["id"]},
        "split": {"method": "group", "group_column": "group", "valid_size": 0.2, "selection_size": 0.25},
        "features": {"preset": "basic"},
    }

    preprocess = prepare_preprocess(cfg).result
    selection = selection_split(cfg, preprocess)

    assert set(selection.X_fit["group"]).isdisjoint(selection.X_selection["group"])
    assert set(selection.X_selection[SOURCE_ROW_COLUMN]).isdisjoint(preprocess.X_valid[SOURCE_ROW_COLUMN])
    assert set(selection.X_fit[SOURCE_ROW_COLUMN]).isdisjoint(preprocess.X_valid[SOURCE_ROW_COLUMN])
