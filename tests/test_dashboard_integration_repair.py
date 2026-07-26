from __future__ import annotations

import pandas as pd

from engine.dashboard_integration import derive_regime_from_scan, plans_are_complete, regime_is_complete, repair_plans


def test_repairs_missing_trade_plan_columns():
    scan = pd.DataFrame([
        {"ticker": "AMGN", "signal": "WATCH", "score": 83, "close": 300, "sma_20": 292, "sma_50": 285}
    ])
    plans = repair_plans(scan, pd.DataFrame())
    assert plans_are_complete(plans)
    assert plans.iloc[0]["entry_price"] == 300
    assert plans.iloc[0]["target_price"] > 300
    assert plans.iloc[0]["stop_loss"] < 300
    assert plans.iloc[0]["risk_reward"] > 0


def test_derives_partial_regime_from_scan():
    scan = pd.DataFrame([
        {"market_regime": "DEFENSIVE", "market_score": 30, "market_adjustment": -5, "regime_reason": "SPY BEARISH 36; QQQ BEARISH 26"}
    ])
    regime = derive_regime_from_scan(scan)
    assert regime["regime"] == "DEFENSIVE"
    assert regime["market_score"] == 30
    assert regime["risk_label"] == "Cautious"
    assert not regime_is_complete(regime)


def test_complete_regime_requires_spy_and_qqq():
    regime = {
        "indices": [
            {"ticker": "SPY", "trend": "BEARISH"},
            {"ticker": "QQQ", "trend": "BEARISH"},
        ],
        "vix": {"ticker": "^VIX", "close": 18.4},
    }
    assert regime_is_complete(regime)
