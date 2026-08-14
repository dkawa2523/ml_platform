"""Nightly synthetic throughput and memory regression test."""

from __future__ import annotations

import time
import tracemalloc

import numpy as np
import pandas as pd
from ml_platform_tabular.models import build_model


def main() -> None:
    rng = np.random.default_rng(42)
    features = pd.DataFrame(rng.normal(size=(20_000, 20)), columns=[f"feature_{index}" for index in range(20)])
    target = features.sum(axis=1).to_numpy(dtype=float)
    tracemalloc.start()
    started = time.perf_counter()
    model = build_model("linear", {})
    feature_values = features.to_numpy(dtype=float)
    model.fit(feature_values, target)
    predictions = np.asarray(model.predict(feature_values), dtype=float)
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    if predictions.shape != (20_000,) or not np.isfinite(predictions).all():
        raise RuntimeError("load test produced invalid prediction shape or non-finite values")
    if elapsed > 60:
        raise RuntimeError(f"load test exceeded 60 seconds: {elapsed:.2f}s")
    if peak > 1024 * 1024 * 1024:
        raise RuntimeError(f"load test exceeded 1 GiB peak Python memory: {peak / 1024**2:.1f} MiB")
    print(f"load test: {elapsed:.2f}s, peak Python memory {peak / 1024**2:.1f} MiB")


if __name__ == "__main__":
    main()
