import pandas as pd

from engine.market_regime import build_market_regime
from engine.scanner import run_scan


def _prices(start=100, days=260, step=0.2):
    closes = [start + (i * step) for i in range(days)]
    return pd.DataFrame(
        {
            "Open": closes,
            "High": [c + 1 for c in closes],
            "Low": [c - 1 for c in closes],
            "Close": closes,
            "Volume": [1000000 + (i * 1000) for i in range(days)],
        },
        index=pd.date_range("2025-01-01", periods=days, freq="D"),
    )


def test_run_scan_with_market_regime_adds_columns():
    price_map = {"AAPL": _prices(), "SPY": _prices(start=400, step=0.4), "QQQ": _prices(start=300, step=0.5)}
    regime = build_market_regime(price_map)
    result = run_scan(price_map, market_regime=regime)
    assert not result.empty
    assert "market_regime" in result.columns
    assert "market_adjustment" in result.columns
    assert "base_score" in result.columns
    assert "SPY" not in result["ticker"].tolist()
    assert "QQQ" not in result["ticker"].tolist()
