import pandas as pd

from engine.proof_validation import build_proof_report
from engine.research_diagnostics import (
    confidence_calibration,
    decision_filter_diagnostics,
    feature_attribution,
    stress_decomposition,
)


def _trades():
    dates = pd.date_range("2024-01-01", periods=12, freq="10D")
    returns = [1.0, -0.4, 0.8, -0.3, 1.2, -0.6] * 2
    return pd.DataFrame({
        "ticker": ["JPM", "MSFT"] * 6,
        "entry_date": dates,
        "exit_date": dates + pd.Timedelta(days=6),
        "return_pct": returns,
        "v14_portfolio_return_pct": [r * .10 for r in returns],
        "score_band": ["80-85"] * 12,
        "confidence_regime": ["BULL"] * 12,
        "market_regime": ["BULL"] * 12,
        "holding_days": [6] * 12,
        "v14_confidence_score": [72, 45, 68, 50, 76, 42] * 2,
        "v14_confidence_label": ["HIGH", "BLOCK", "MEDIUM", "LOW", "HIGH", "BLOCK"] * 2,
        "v14_position_size_pct": [15, 0, 10, 5, 15, 0] * 2,
        "v14_evidence_trades": list(range(12)),
        "v14_recent_component": [70, 40, 65, 45, 75, 35] * 2,
        "v14_history_component": [65, 50, 60, 52, 68, 48] * 2,
        "v14_regime_component": [70, 42, 66, 48, 72, 38] * 2,
        "v14_score_band_component": [62, 55, 60, 54, 64, 50] * 2,
        "v14_ticker_component": [75, 40, 70, 45, 78, 35] * 2,
    })


def test_stress_decomposition_isolates_cost_and_delay():
    result = stress_decomposition(_trades(), return_column="v14_portfolio_return_pct")
    assert set(result["scenario"]) >= {"Baseline", "Additional costs only", "Delayed entry only", "Combined stress"}
    combined = result.loc[result["scenario"] == "Combined stress", "average_return_pct"].iloc[0]
    baseline = result.loc[result["scenario"] == "Baseline", "average_return_pct"].iloc[0]
    assert combined < baseline


def test_restriction_and_attribution_diagnostics_are_populated():
    assert not decision_filter_diagnostics(_trades()).empty
    attribution = feature_attribution(_trades())
    assert "winner_lift" in attribution
    assert "Final confidence" in set(attribution["component"])


def test_confidence_calibration_has_observed_win_rate():
    result = confidence_calibration(_trades())
    assert "observed_win_rate_pct" in result
    assert result["trades"].sum() == 12


def test_v141_report_contains_research_sections():
    report = build_proof_report(_trades(), build_version="14.2")
    for key in ("decision_filter_diagnostics", "stress_decomposition", "feature_attribution", "confidence_calibration"):
        assert key in report
        assert report[key]
