from __future__ import annotations

import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

from pathlib import Path

import numpy as np
import pandas as pd


def main() -> None:
    rng = np.random.default_rng(42)
    n = 200
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    category = rng.choice(["A", "B", "C"], size=n)
    category_effect = {"A": 0.0, "B": 2.0, "C": -1.0}
    target = 3.0 * x1 - 1.5 * x2 + np.array([category_effect[c] for c in category]) + rng.normal(scale=0.5, size=n)

    df = pd.DataFrame(
        {
            "id": range(n),
            "x1": x1,
            "x2": x2,
            "category": category,
            "target": target,
        }
    )

    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    df.to_csv(data_dir / "sample_train.csv", index=False)
    df.drop(columns=["target"]).head(50).to_csv(data_dir / "sample_infer.csv", index=False)
    print("Wrote data/sample_train.csv and data/sample_infer.csv")


if __name__ == "__main__":
    main()
