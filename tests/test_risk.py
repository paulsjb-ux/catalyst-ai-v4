import pandas as pd

from engine.risk import atr, build_trade_plan


def test_atr_returns_values():
    frame = pd.DataFrame(
        {
            "High": [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25],
            "Low": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
            "Close": [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24],
        }
    )
    values = atr(frame, 14).dropna()
    assert not values.empty
    assert values.iloc[-1] > 0


def test_build_trade_plan_has_risk_reward():
    plan = build_trade_plan(
        ticker="AAPL",
        signal="BUY",
        score=85,
        close=100,
        atr_value=3,
        sma_20=96,
        sma_50=92,
    )

    assert plan["entry_price"] == 100
    assert plan["target_price"] > plan["entry_price"]
    assert plan["stop_loss"] < plan["entry_price"]
    assert plan["risk_reward"] > 0
    assert plan["position_quality"] in {"A", "B", "C", "LOW", "INVALID"}
