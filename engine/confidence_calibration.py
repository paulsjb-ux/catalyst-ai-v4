from __future__ import annotations

from dataclasses import dataclass
import math
import pandas as pd


@dataclass(frozen=True)
class EvidenceDecision:
    multiplier: float
    evidence_label: str
    evidence_trades: int
    evidence_win_rate_pct: float
    evidence_profit_factor: float | str
    evidence_average_return_pct: float
    rationale: str


def _profit_factor(returns: pd.Series) -> float:
    winners = returns[returns > 0]
    losers = returns[returns <= 0]
    gross_profit = float(winners.sum())
    gross_loss = abs(float(losers.sum()))
    if gross_loss <= 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def score_band(score: float) -> str:
    value = float(score or 0)
    if value >= 92:
        return "92+"
    if value >= 86:
        return "86-91"
    if value >= 80:
        return "80-85"
    return "<80"


def evidence_decision(
    history: pd.DataFrame,
    *,
    minimum_evidence_trades: int = 20,
    full_size_profit_factor: float = 1.20,
    full_size_win_rate_pct: float = 48.0,
    full_size_average_return_pct: float = 0.15,
) -> EvidenceDecision:
    """Decide the permitted size from previously closed trades only."""
    if history is None or history.empty:
        return EvidenceDecision(
            multiplier=0.50,
            evidence_label="UNPROVEN",
            evidence_trades=0,
            evidence_win_rate_pct=0.0,
            evidence_profit_factor=0.0,
            evidence_average_return_pct=0.0,
            rationale="no prior closed trades",
        )

    returns = pd.to_numeric(
        history["return_pct"],
        errors="coerce",
    ).dropna()
    count = int(len(returns))
    if count == 0:
        return EvidenceDecision(
            multiplier=0.50,
            evidence_label="UNPROVEN",
            evidence_trades=0,
            evidence_win_rate_pct=0.0,
            evidence_profit_factor=0.0,
            evidence_average_return_pct=0.0,
            rationale="no usable prior returns",
        )

    win_rate = float((returns > 0).mean() * 100)
    average_return = float(returns.mean())
    profit_factor = _profit_factor(returns)

    if count < int(minimum_evidence_trades):
        multiplier = 0.60 if average_return > 0 else 0.45
        label = "BUILDING"
        rationale = f"{count}/{minimum_evidence_trades} evidence trades"
    elif (
        profit_factor >= full_size_profit_factor
        and win_rate >= full_size_win_rate_pct
        and average_return >= full_size_average_return_pct
    ):
        multiplier = 1.00
        label = "PROVEN"
        rationale = "out-of-sample evidence supports full size"
    elif profit_factor >= 1.05 and average_return > 0:
        multiplier = 0.70
        label = "MIXED"
        rationale = "positive but insufficient evidence"
    else:
        multiplier = 0.40
        label = "WEAK"
        rationale = "prior out-of-sample evidence is weak"

    pf_display: float | str = (
        round(profit_factor, 2)
        if math.isfinite(profit_factor)
        else "∞"
    )
    return EvidenceDecision(
        multiplier=round(multiplier, 2),
        evidence_label=label,
        evidence_trades=count,
        evidence_win_rate_pct=round(win_rate, 2),
        evidence_profit_factor=pf_display,
        evidence_average_return_pct=round(average_return, 3),
        rationale=rationale,
    )


def apply_walk_forward_calibration(
    trades: pd.DataFrame,
    *,
    enabled: bool = True,
    minimum_evidence_trades: int = 20,
    full_size_profit_factor: float = 1.20,
    full_size_win_rate_pct: float = 48.0,
    full_size_average_return_pct: float = 0.15,
) -> pd.DataFrame:
    """Calibrate each trade using only trades closed before its entry date.

    Evidence groups are deliberately broad: score band + original risk label.
    This avoids overfitting tiny ticker-level samples while still validating
    whether the app's confidence labels have worked out of sample.
    """
    if trades is None or trades.empty:
        output = trades.copy() if isinstance(trades, pd.DataFrame) else pd.DataFrame()
        for column in [
            "score_band",
            "evidence_label",
            "evidence_multiplier",
            "evidence_trades",
            "evidence_win_rate_pct",
            "evidence_profit_factor",
            "evidence_average_return_pct",
            "calibrated_position_size_pct",
            "calibrated_portfolio_return_pct",
            "evidence_rationale",
        ]:
            output[column] = pd.Series(dtype="object")
        return output

    output = trades.copy()
    output["entry_date"] = pd.to_datetime(output["entry_date"])
    output["exit_date"] = pd.to_datetime(output["exit_date"])
    output["score_band"] = output["score"].map(score_band)
    output["_original_order"] = range(len(output))
    ordered = output.sort_values(
        ["entry_date", "ticker", "_original_order"],
        ascending=[True, True, True],
    )

    rows: list[dict] = []
    closed_history = pd.DataFrame(columns=ordered.columns)

    for _, trade in ordered.iterrows():
        entry_date = trade["entry_date"]
        eligible = output[output["exit_date"] < entry_date]

        same_group = eligible[
            (eligible["score_band"] == trade["score_band"])
            & (
                eligible.get(
                    "risk_label",
                    pd.Series("", index=eligible.index),
                )
                == trade.get("risk_label", "")
            )
        ]

        decision = evidence_decision(
            same_group,
            minimum_evidence_trades=minimum_evidence_trades,
            full_size_profit_factor=full_size_profit_factor,
            full_size_win_rate_pct=full_size_win_rate_pct,
            full_size_average_return_pct=full_size_average_return_pct,
        )

        original_size = float(trade.get("position_size_pct", 100.0) or 0.0)
        multiplier = decision.multiplier if enabled else 1.0
        calibrated_size = min(25.0, max(2.5, original_size * multiplier))
        raw_return = float(trade.get("return_pct", 0.0) or 0.0)
        calibrated_return = raw_return * calibrated_size / 100

        row = trade.to_dict()
        row.update(
            {
                "evidence_label": decision.evidence_label if enabled else "OFF",
                "evidence_multiplier": multiplier,
                "evidence_trades": decision.evidence_trades,
                "evidence_win_rate_pct": decision.evidence_win_rate_pct,
                "evidence_profit_factor": decision.evidence_profit_factor,
                "evidence_average_return_pct": decision.evidence_average_return_pct,
                "calibrated_position_size_pct": round(calibrated_size, 2),
                "calibrated_portfolio_return_pct": round(calibrated_return, 4),
                "evidence_rationale": (
                    decision.rationale
                    if enabled
                    else "walk-forward calibration disabled"
                ),
            }
        )
        rows.append(row)

    result = pd.DataFrame(rows).sort_values("_original_order")
    return result.drop(columns=["_original_order"]).reset_index(drop=True)


def calibration_summary(trades: pd.DataFrame) -> pd.DataFrame:
    if trades is None or trades.empty or "evidence_label" not in trades.columns:
        return pd.DataFrame(
            columns=[
                "evidence_label",
                "trades",
                "average_size_pct",
                "average_return_pct",
                "calibrated_contribution_pct",
            ]
        )

    rows = []
    for label, group in trades.groupby("evidence_label", sort=True):
        rows.append(
            {
                "evidence_label": label,
                "trades": int(len(group)),
                "average_size_pct": round(
                    float(
                        pd.to_numeric(
                            group["calibrated_position_size_pct"],
                            errors="coerce",
                        ).mean()
                    ),
                    2,
                ),
                "average_return_pct": round(
                    float(
                        pd.to_numeric(
                            group["return_pct"],
                            errors="coerce",
                        ).mean()
                    ),
                    3,
                ),
                "calibrated_contribution_pct": round(
                    float(
                        pd.to_numeric(
                            group["calibrated_portfolio_return_pct"],
                            errors="coerce",
                        ).sum()
                    ),
                    2,
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["calibrated_contribution_pct", "trades"],
        ascending=[False, False],
    ).reset_index(drop=True)
