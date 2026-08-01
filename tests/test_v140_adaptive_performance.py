import pandas as pd

from engine.adaptive_confidence import (
    adaptive_decision,
    apply_adaptive_confidence,
    holding_period_diagnostics,
)


def _trades():
    dates = pd.date_range("2024-01-01", periods=40, freq="7D")
    return pd.DataFrame({
        "ticker": ["JPM"] * 20 + ["NVDA"] * 20,
        "entry_date": dates,
        "exit_date": dates + pd.Timedelta(days=5),
        "return_pct": [1.0, .8, -.3, .9, .7] * 4 + [-.8, .2, -.7, .1, -.6] * 4,
        "holding_days": [5, 8, 15, 25, 45] * 8,
        "score_band": ["80-85"] * 40,
        "market_regime": ["BULL"] * 40,
        "v92_position_size_pct": [15.0] * 40,
    })


def test_adaptive_decision_rewards_stronger_ticker_evidence():
    history = _trades()
    jpm = adaptive_decision(history, ticker="JPM", score_band="80-85", regime="BULL")
    nvda = adaptive_decision(history, ticker="NVDA", score_band="80-85", regime="BULL")
    assert jpm.ticker_component > nvda.ticker_component
    assert 0 <= jpm.score <= 100


def test_overlay_is_walk_forward_and_caps_size():
    result = apply_adaptive_confidence(_trades())
    assert "v14_confidence_score" in result
    assert result.iloc[0]["v14_evidence_trades"] == 0
    assert result["v14_position_size_pct"].max() <= 15.0


def test_holding_period_diagnostics_cover_swing_buckets():
    diag = holding_period_diagnostics(_trades())
    assert set(diag["holding_bucket"]) == {"1-5", "6-10", "11-20", "21-40", "40+"}
    assert "profit_factor" in diag
