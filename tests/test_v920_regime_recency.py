import pandas as pd
from engine.regime_recency_confidence import apply_regime_recency_confidence, recency_decision, score_band_diagnostics


def test_all_trades_are_capped_at_reduced_size():
    trades = pd.DataFrame({
        "ticker": ["A", "B"], "entry_date": pd.to_datetime(["2026-02-01", "2026-03-01"]),
        "exit_date": pd.to_datetime(["2026-02-05", "2026-03-05"]), "score_band": ["80-85", "80-85"],
        "market_regime": ["RISK_ON", "RISK_ON"], "return_pct": [5.0, 4.0],
        "calibrated_position_size_pct": [25.0, 25.0],
    })
    result = apply_regime_recency_confidence(trades, reduced_cap_pct=15.0)
    assert result["v92_position_size_pct"].max() <= 15.0


def test_proven_expires_when_recent_performance_is_weak():
    dates = pd.date_range("2026-01-01", periods=20, freq="7D")
    history = pd.DataFrame({"exit_date": dates, "return_pct": [2.0] * 12 + [-4.0] * 8})
    decision = recency_decision(history, previous_status="PROVEN", as_of="2026-06-01", half_life_days=20)
    assert decision.status != "PROVEN"
    assert decision.direction == "DOWNGRADE"


def test_score_band_diagnostics_separate_regimes():
    trades = pd.DataFrame({
        "entry_date": pd.to_datetime(["2026-01-01", "2026-01-02"]), "score_band": ["80-85", "80-85"],
        "market_regime": ["RISK_ON", "RISK_OFF"], "return_pct": [2.0, -2.0],
        "confidence_status": ["PROVEN", "WEAK"], "confidence_direction": ["UPGRADE", "DOWNGRADE"],
    })
    result = score_band_diagnostics(trades)
    assert set(result["market_regime"]) == {"RISK_ON", "RISK_OFF"}
