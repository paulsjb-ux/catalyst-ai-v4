from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
import math
import pandas as pd

CALIBRATION_COLUMNS = [
    "score_band", "evidence_label", "evidence_multiplier",
    "evidence_trades", "evidence_win_rate_pct",
    "evidence_profit_factor", "evidence_average_return_pct",
    "calibrated_position_size_pct",
    "calibrated_portfolio_return_pct", "evidence_rationale",
]

@dataclass(frozen=True)
class EvidenceDecision:
    multiplier: float
    evidence_label: str
    evidence_trades: int
    evidence_win_rate_pct: float
    evidence_profit_factor: float | str
    evidence_average_return_pct: float
    rationale: str

@dataclass
class EvidenceStats:
    count: int = 0
    winners: int = 0
    return_sum: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0

    def add(self, value) -> None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return
        if math.isnan(number) or math.isinf(number):
            return
        self.count += 1
        self.return_sum += number
        if number > 0:
            self.winners += 1
            self.gross_profit += number
        else:
            self.gross_loss += abs(number)

    @property
    def win_rate_pct(self) -> float:
        return 100 * self.winners / self.count if self.count else 0.0

    @property
    def average_return_pct(self) -> float:
        return self.return_sum / self.count if self.count else 0.0

    @property
    def profit_factor(self) -> float:
        if self.gross_loss <= 0:
            return float("inf") if self.gross_profit > 0 else 0.0
        return self.gross_profit / self.gross_loss

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

def _decision(
    count: int,
    win_rate: float,
    average_return: float,
    profit_factor: float,
    minimum_evidence_trades: int,
    full_size_profit_factor: float,
    full_size_win_rate_pct: float,
    full_size_average_return_pct: float,
) -> EvidenceDecision:
    if count <= 0:
        return EvidenceDecision(
            0.50, "UNPROVEN", 0, 0.0, 0.0, 0.0,
            "no prior closed trades",
        )
    if count < int(minimum_evidence_trades):
        multiplier = 0.60 if average_return > 0 else 0.45
        label = "BUILDING"
        rationale = f"{count}/{minimum_evidence_trades} evidence trades"
    elif (
        profit_factor >= full_size_profit_factor
        and win_rate >= full_size_win_rate_pct
        and average_return >= full_size_average_return_pct
    ):
        multiplier, label = 1.0, "PROVEN"
        rationale = "out-of-sample evidence supports full size"
    elif profit_factor >= 1.05 and average_return > 0:
        multiplier, label = 0.70, "MIXED"
        rationale = "positive but insufficient evidence"
    else:
        multiplier, label = 0.40, "WEAK"
        rationale = "prior out-of-sample evidence is weak"

    pf = round(profit_factor, 2) if math.isfinite(profit_factor) else "∞"
    return EvidenceDecision(
        round(multiplier, 2), label, count, round(win_rate, 2), pf,
        round(average_return, 3), rationale,
    )

def evidence_decision(
    history: pd.DataFrame,
    *,
    minimum_evidence_trades: int = 20,
    full_size_profit_factor: float = 1.20,
    full_size_win_rate_pct: float = 48.0,
    full_size_average_return_pct: float = 0.15,
) -> EvidenceDecision:
    if history is None or history.empty:
        return _decision(
            0, 0, 0, 0, minimum_evidence_trades,
            full_size_profit_factor, full_size_win_rate_pct,
            full_size_average_return_pct,
        )
    returns = pd.to_numeric(history["return_pct"], errors="coerce").dropna()
    if returns.empty:
        return EvidenceDecision(
            0.50, "UNPROVEN", 0, 0.0, 0.0, 0.0,
            "no usable prior returns",
        )
    return _decision(
        len(returns), float((returns > 0).mean() * 100),
        float(returns.mean()), _profit_factor(returns),
        minimum_evidence_trades, full_size_profit_factor,
        full_size_win_rate_pct, full_size_average_return_pct,
    )

def _decision_from_stats(stats: EvidenceStats | None, **kwargs) -> EvidenceDecision:
    stats = stats or EvidenceStats()
    return _decision(
        stats.count, stats.win_rate_pct, stats.average_return_pct,
        stats.profit_factor, kwargs["minimum_evidence_trades"],
        kwargs["full_size_profit_factor"],
        kwargs["full_size_win_rate_pct"],
        kwargs["full_size_average_return_pct"],
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
    """O(n log n) calibration using only exits strictly before entry."""
    if trades is None or trades.empty:
        output = trades.copy() if isinstance(trades, pd.DataFrame) else pd.DataFrame()
        for column in CALIBRATION_COLUMNS:
            output[column] = pd.Series(dtype="object")
        return output

    output = trades.copy()
    output["entry_date"] = pd.to_datetime(output["entry_date"])
    output["exit_date"] = pd.to_datetime(output["exit_date"])
    output["score_band"] = output["score"].map(score_band)
    output["_original_order"] = range(len(output))

    entry_records = output.sort_values(
        ["entry_date", "ticker", "_original_order"]
    ).to_dict("records")
    exit_records = output.sort_values(
        ["exit_date", "_original_order"]
    ).to_dict("records")

    stats_by_group = defaultdict(EvidenceStats)
    rows = []
    pointer = 0

    decision_kwargs = {
        "minimum_evidence_trades": minimum_evidence_trades,
        "full_size_profit_factor": full_size_profit_factor,
        "full_size_win_rate_pct": full_size_win_rate_pct,
        "full_size_average_return_pct": full_size_average_return_pct,
    }

    for trade in entry_records:
        entry_date = trade["entry_date"]
        while pointer < len(exit_records) and exit_records[pointer]["exit_date"] < entry_date:
            closed = exit_records[pointer]
            group = (
                str(closed.get("score_band", "")),
                str(closed.get("risk_label", "")),
            )
            stats_by_group[group].add(closed.get("return_pct"))
            pointer += 1

        group = (
            str(trade.get("score_band", "")),
            str(trade.get("risk_label", "")),
        )
        decision = _decision_from_stats(
            stats_by_group.get(group),
            **decision_kwargs,
        )
        original_size = float(trade.get("position_size_pct", 100.0) or 0.0)
        multiplier = decision.multiplier if enabled else 1.0
        size = min(25.0, max(2.5, original_size * multiplier))
        raw_return = float(trade.get("return_pct", 0.0) or 0.0)

        row = dict(trade)
        row.update({
            "evidence_label": decision.evidence_label if enabled else "OFF",
            "evidence_multiplier": multiplier,
            "evidence_trades": decision.evidence_trades,
            "evidence_win_rate_pct": decision.evidence_win_rate_pct,
            "evidence_profit_factor": decision.evidence_profit_factor,
            "evidence_average_return_pct": decision.evidence_average_return_pct,
            "calibrated_position_size_pct": round(size, 2),
            "calibrated_portfolio_return_pct": round(raw_return * size / 100, 4),
            "evidence_rationale": (
                decision.rationale
                if enabled else "walk-forward calibration disabled"
            ),
        })
        rows.append(row)

    result = pd.DataFrame(rows).sort_values("_original_order")
    return result.drop(columns=["_original_order"]).reset_index(drop=True)

def calibration_summary(trades: pd.DataFrame) -> pd.DataFrame:
    if trades is None or trades.empty or "evidence_label" not in trades.columns:
        return pd.DataFrame(columns=[
            "evidence_label", "trades", "average_size_pct",
            "average_return_pct", "calibrated_contribution_pct",
        ])
    summary = trades.groupby("evidence_label", sort=True).agg(
        trades=("evidence_label", "size"),
        average_size_pct=("calibrated_position_size_pct", "mean"),
        average_return_pct=("return_pct", "mean"),
        calibrated_contribution_pct=("calibrated_portfolio_return_pct", "sum"),
    ).reset_index()
    summary["average_size_pct"] = summary["average_size_pct"].round(2)
    summary["average_return_pct"] = summary["average_return_pct"].round(3)
    summary["calibrated_contribution_pct"] = summary[
        "calibrated_contribution_pct"
    ].round(2)
    return summary.sort_values(
        ["calibrated_contribution_pct", "trades"],
        ascending=[False, False],
    ).reset_index(drop=True)
