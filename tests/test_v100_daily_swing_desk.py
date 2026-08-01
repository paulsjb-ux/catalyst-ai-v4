import pandas as pd

from engine.swing_focus import SwingPolicy, build_swing_desk, policy_from_proof, swing_desk_summary


def test_policy_learns_validated_tickers_and_score_band():
    report = {
        "by_ticker": [
            {"ticker": "JPM", "trades": 36, "profit_factor": 2.4},
            {"ticker": "NVDA", "trades": 32, "profit_factor": 0.75},
        ],
        "by_score_band": [
            {"score_band": "80-85", "trades": 144, "profit_factor": 1.275},
            {"score_band": "86-91", "trades": 49, "profit_factor": 0.79},
        ],
    }
    policy = policy_from_proof(report)
    assert policy.preferred_tickers == ("JPM",)
    assert policy.score_min == 80
    assert policy.score_max == 85


def test_swing_desk_prioritises_validated_swing_setup():
    scan = pd.DataFrame([
        {"ticker": "JPM", "signal": "BUY", "score": 83, "trend": "TREND", "change_20d_pct": 4, "change_60d_pct": 9},
        {"ticker": "NVDA", "signal": "BUY", "score": 90, "trend": "TREND", "change_20d_pct": 6, "change_60d_pct": 15},
    ])
    plans = pd.DataFrame([
        {"ticker": "JPM", "entry_price": 100, "target_price": 110, "stop_loss": 96, "risk_reward": 2.5},
        {"ticker": "NVDA", "entry_price": 100, "target_price": 110, "stop_loss": 96, "risk_reward": 2.5},
    ])
    desk = build_swing_desk(scan, plans, {"regime": "RISK_ON"}, policy=SwingPolicy(preferred_tickers=("JPM",)))
    assert desk.iloc[0]["ticker"] == "JPM"
    assert desk.iloc[0]["swing_status"] == "PRIORITY"
    assert desk.iloc[0]["position_size_pct"] == 15
    assert desk.loc[desk["ticker"] == "NVDA", "swing_status"].iloc[0] == "WATCH"


def test_risk_off_prevents_qualified_swing_trades():
    scan = pd.DataFrame([{"ticker": "JPM", "signal": "BUY", "score": 83, "trend": "TREND", "change_20d_pct": 4, "change_60d_pct": 9}])
    plans = pd.DataFrame([{"ticker": "JPM", "risk_reward": 3.0}])
    policy = SwingPolicy(preferred_tickers=("JPM",))
    desk = build_swing_desk(scan, plans, {"regime": "RISK_OFF"}, policy=policy)
    summary = swing_desk_summary(desk, policy)
    assert summary["qualified_swing_trades"] == 0
    assert desk.iloc[0]["position_size_pct"] == 0
