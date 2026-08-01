from time import perf_counter
import numpy as np
import pandas as pd
from engine.scanner import clear_indicator_cache, run_scan


def make_frame(seed: int, rows: int = 260) -> pd.DataFrame:
    values = np.linspace(100 + seed, 140 + seed, rows)
    return pd.DataFrame(
        {
            "Open": values - 0.5,
            "High": values + 1,
            "Low": values - 1,
            "Close": values,
            "Volume": np.arange(rows) + 100_000,
        },
        index=pd.date_range("2025-01-01", periods=rows, freq="B"),
    )


prices = {f"T{i:04}": make_frame(i) for i in range(523)}
for workers in (1, 4, 8, 12):
    clear_indicator_cache()
    started = perf_counter()
    result = run_scan(prices, workers=workers)
    print(f"workers={workers} rows={len(result)} seconds={perf_counter() - started:.3f}")

started = perf_counter()
run_scan(prices, workers=12)
print(f"warm_cache_seconds={perf_counter() - started:.3f}")
