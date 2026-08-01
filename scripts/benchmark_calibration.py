from time import perf_counter
import numpy as np
import pandas as pd
from engine.confidence_calibration import apply_walk_forward_calibration

rng = np.random.default_rng(7)
for count in (500, 2000, 10000):
    entries = pd.date_range("2010-01-01", periods=count, freq="D")
    trades = pd.DataFrame({
        "ticker": [f"T{i % 50:03d}" for i in range(count)],
        "entry_date": entries,
        "exit_date": entries + pd.to_timedelta(
            rng.integers(2, 30, size=count), unit="D"
        ),
        "score": rng.choice([78, 82, 88, 94], size=count),
        "risk_label": rng.choice(
            ["SMALL", "REDUCED", "FULL"], size=count
        ),
        "position_size_pct": rng.choice(
            [5.0, 10.0, 15.0, 20.0, 25.0], size=count
        ),
        "return_pct": rng.normal(0.15, 3.5, size=count),
    })
    started = perf_counter()
    result = apply_walk_forward_calibration(trades)
    print(
        f"trades={count} rows={len(result)} "
        f"seconds={perf_counter() - started:.4f}"
    )
