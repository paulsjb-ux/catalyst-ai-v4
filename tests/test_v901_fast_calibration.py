import numpy as np
import pandas as pd

from engine.confidence_calibration import (
    apply_walk_forward_calibration,
    evidence_decision,
    score_band,
)


def legacy(trades):
    output = trades.copy()
    output["entry_date"] = pd.to_datetime(output["entry_date"])
    output["exit_date"] = pd.to_datetime(output["exit_date"])
    output["score_band"] = output["score"].map(score_band)
    output["_original_order"] = range(len(output))
    rows = []
    for _, trade in output.sort_values(
        ["entry_date", "ticker", "_original_order"]
    ).iterrows():
        eligible = output[output["exit_date"] < trade["entry_date"]]
        group = eligible[
            (eligible["score_band"] == trade["score_band"])
            & (eligible["risk_label"] == trade["risk_label"])
        ]
        decision = evidence_decision(group)
        size = min(
            25.0,
            max(
                2.5,
                float(trade["position_size_pct"])
                * decision.multiplier,
            ),
        )
        row = trade.to_dict()
        row.update({
            "evidence_label": decision.evidence_label,
            "evidence_multiplier": decision.multiplier,
            "evidence_trades": decision.evidence_trades,
            "evidence_win_rate_pct": decision.evidence_win_rate_pct,
            "evidence_profit_factor": decision.evidence_profit_factor,
            "evidence_average_return_pct": decision.evidence_average_return_pct,
            "calibrated_position_size_pct": round(size, 2),
            "calibrated_portfolio_return_pct": round(
                float(trade["return_pct"]) * size / 100,
                4,
            ),
            "evidence_rationale": decision.rationale,
        })
        rows.append(row)
    return pd.DataFrame(rows).sort_values(
        "_original_order"
    ).drop(columns=["_original_order"]).reset_index(drop=True)


def sample(count=250):
    rng = np.random.default_rng(42)
    entries = pd.date_range("2020-01-01", periods=count, freq="2D")
    return pd.DataFrame({
        "ticker": [f"T{i % 12:02d}" for i in range(count)],
        "entry_date": entries,
        "exit_date": entries + pd.to_timedelta(
            rng.integers(2, 20, size=count),
            unit="D",
        ),
        "score": rng.choice([78, 82, 88, 94], size=count),
        "risk_label": rng.choice(
            ["SMALL", "REDUCED", "FULL"],
            size=count,
        ),
        "position_size_pct": rng.choice(
            [5.0, 10.0, 15.0, 20.0, 25.0],
            size=count,
        ),
        "return_pct": rng.normal(0.2, 3.0, size=count),
    })


def test_fast_matches_legacy():
    fast = apply_walk_forward_calibration(sample())
    old = legacy(sample())
    columns = [
        "evidence_label", "evidence_multiplier",
        "evidence_trades", "evidence_win_rate_pct",
        "evidence_profit_factor",
        "evidence_average_return_pct",
        "calibrated_position_size_pct",
        "calibrated_portfolio_return_pct",
        "evidence_rationale",
    ]
    pd.testing.assert_frame_equal(
        fast[columns],
        old[columns],
        check_dtype=False,
    )


def test_exit_on_entry_date_is_not_prior_evidence():
    trades = pd.DataFrame({
        "ticker": ["A", "B"],
        "entry_date": pd.to_datetime(
            ["2026-01-01", "2026-01-10"]
        ),
        "exit_date": pd.to_datetime(
            ["2026-01-10", "2026-01-20"]
        ),
        "score": [94, 94],
        "risk_label": ["FULL", "FULL"],
        "position_size_pct": [25.0, 25.0],
        "return_pct": [10.0, 5.0],
    })
    result = apply_walk_forward_calibration(
        trades,
        minimum_evidence_trades=1,
    )
    assert result.loc[1, "evidence_trades"] == 0
