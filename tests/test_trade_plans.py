import pandas as pd

from engine.trade_plans import build_trade_plans, filter_trade_plan_candidates


def test_filter_trade_plan_candidates():
    frame = pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT", "TSLA"],
            "signal": ["BUY", "WATCH", "IGNORE"],
        }
    )
    filtered = filter_trade_plan_candidates(frame)
    assert filtered["ticker"].tolist() == ["AAPL", "MSFT"]


def test_build_trade_plans_returns_rows():
    scan = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "signal": ["BUY"],
            "score": [85],
            "close": [100],
            "sma_20": [96],
            "sma_50": [92],
        }
    )
    prices = {
        "AAPL": pd.DataFrame(
            {
                "High": [101] * 20,
                "Low": [99] * 20,
                "Close": [100] * 20,
                "Volume": [1000] * 20,
            }
        )
    }
    plans = build_trade_plans(scan, prices)
    assert not plans.empty
    assert "target_price" in plans.columns
    assert "stop_loss" in plans.columns
