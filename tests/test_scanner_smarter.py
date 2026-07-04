import pandas as pd

from engine.scanner import run_scan


def test_run_scan_contains_smarter_columns():
    dates = pd.date_range("2025-01-01", periods=260, freq="D")
    closes = [100 + (i * 0.2) for i in range(260)]
    prices = {
        "AAPL": pd.DataFrame(
            {
                "Open": closes,
                "High": [c + 1 for c in closes],
                "Low": [c - 1 for c in closes],
                "Close": closes,
                "Volume": [1000000 + (i * 1000) for i in range(260)],
            },
            index=dates,
        )
    }

    result = run_scan(prices)

    assert not result.empty
    assert "trend_score" in result.columns
    assert "momentum_score" in result.columns
    assert "relative_strength_score" in result.columns
    assert "volatility_penalty" in result.columns
    assert "extension_penalty" in result.columns
