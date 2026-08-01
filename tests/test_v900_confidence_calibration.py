import pandas as pd

from engine.confidence_calibration import (
    apply_walk_forward_calibration,
    calibration_summary,
    evidence_decision,
    score_band,
)
from engine.backtest import calculate_metrics


def _history(returns):
    return pd.DataFrame({"return_pct": returns})


def test_no_evidence_blocks_full_size():
    decision = evidence_decision(pd.DataFrame(), minimum_evidence_trades=20)
    assert decision.evidence_label == "UNPROVEN"
    assert decision.multiplier < 1.0


def test_full_size_requires_sample_and_quality():
    history = _history([2.0] * 14 + [-1.0] * 6)
    decision = evidence_decision(
        history,
        minimum_evidence_trades=20,
        full_size_profit_factor=1.2,
        full_size_win_rate_pct=48,
        full_size_average_return_pct=0.15,
    )
    assert decision.evidence_label == "PROVEN"
    assert decision.multiplier == 1.0


def test_weak_evidence_reduces_size():
    history = _history([1.0] * 8 + [-2.0] * 12)
    decision = evidence_decision(history, minimum_evidence_trades=20)
    assert decision.evidence_label == "WEAK"
    assert decision.multiplier == 0.4


def test_walk_forward_does_not_use_future_trades():
    trades = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "entry_date": pd.to_datetime(
                ["2026-01-02", "2026-02-02", "2026-03-02"]
            ),
            "exit_date": pd.to_datetime(
                ["2026-01-10", "2026-02-10", "2026-03-10"]
            ),
            "score": [93, 93, 93],
            "risk_label": ["FULL", "FULL", "FULL"],
            "position_size_pct": [25, 25, 25],
            "return_pct": [-5, 5, 50],
        }
    )
    calibrated = apply_walk_forward_calibration(
        trades,
        minimum_evidence_trades=1,
    )
    first = calibrated.iloc[0]
    second = calibrated.iloc[1]
    assert first["evidence_trades"] == 0
    assert second["evidence_trades"] == 1
    assert second["evidence_average_return_pct"] == -5.0


def test_calibrated_size_never_exceeds_original_size():
    trades = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "entry_date": pd.to_datetime(["2026-01-02"]),
            "exit_date": pd.to_datetime(["2026-01-10"]),
            "score": [93],
            "risk_label": ["FULL"],
            "position_size_pct": [25],
            "return_pct": [5],
        }
    )
    calibrated = apply_walk_forward_calibration(trades)
    assert calibrated.loc[0, "calibrated_position_size_pct"] <= 25


def test_metrics_include_calibrated_equity():
    trades = pd.DataFrame(
        {
            "ticker": ["A", "B"],
            "exit_date": pd.to_datetime(["2026-01-10", "2026-02-10"]),
            "return_pct": [10.0, -10.0],
            "portfolio_return_pct": [2.0, -2.0],
            "calibrated_portfolio_return_pct": [1.0, -0.5],
            "position_size_pct": [20.0, 20.0],
            "calibrated_position_size_pct": [10.0, 5.0],
            "holding_days": [5, 5],
        }
    )
    metrics, curve = calculate_metrics(trades)
    assert "calibrated_equity" in curve.columns
    assert "calibrated_compounded_return_pct" in metrics
    assert metrics["average_calibrated_position_size_pct"] == 7.5


def test_calibration_summary_has_evidence_groups():
    trades = pd.DataFrame(
        {
            "evidence_label": ["UNPROVEN", "PROVEN"],
            "calibrated_position_size_pct": [10, 20],
            "return_pct": [-1, 2],
            "calibrated_portfolio_return_pct": [-0.1, 0.4],
        }
    )
    result = calibration_summary(trades)
    assert set(result["evidence_label"]) == {"UNPROVEN", "PROVEN"}


def test_score_bands_are_stable():
    assert score_band(95) == "92+"
    assert score_band(88) == "86-91"
    assert score_band(82) == "80-85"
    assert score_band(78) == "<80"
