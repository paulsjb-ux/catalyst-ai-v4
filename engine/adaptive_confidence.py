from __future__ import annotations

"""Catalyst AI v14 adaptive confidence and research diagnostics.

The overlay is deliberately walk-forward: only trades closed before a new trade's
entry date may influence that trade. This prevents future leakage while allowing
recent ticker, score-band and regime evidence to change confidence and sizing.
"""

from dataclasses import dataclass
import math
import pandas as pd

V14_COLUMNS = [
    "v14_confidence_score", "v14_confidence_label", "v14_position_size_pct",
    "v14_portfolio_return_pct", "v14_recent_component", "v14_history_component",
    "v14_regime_component", "v14_score_band_component", "v14_ticker_component",
    "v14_evidence_trades", "v14_reason",
]


@dataclass(frozen=True)
class AdaptiveDecision:
    score: float
    label: str
    size_pct: float
    recent_component: float
    history_component: float
    regime_component: float
    score_band_component: float
    ticker_component: float
    evidence_trades: int
    reason: str


def _returns(frame: pd.DataFrame) -> pd.Series:
    if frame is None or frame.empty or "return_pct" not in frame:
        return pd.Series(dtype=float)
    return pd.to_numeric(frame["return_pct"], errors="coerce").dropna()


def _quality(frame: pd.DataFrame, *, neutral: float = 50.0) -> tuple[float, int]:
    """Map trade evidence to a bounded 0-100 quality score."""
    values = _returns(frame)
    n = len(values)
    if n < 5:
        return neutral, n
    wins = float((values > 0).mean())
    gross_profit = float(values.clip(lower=0).sum())
    gross_loss = abs(float(values.clip(upper=0).sum()))
    pf = gross_profit / gross_loss if gross_loss else (3.0 if gross_profit > 0 else 0.0)
    expectancy = float(values.mean())
    # Stable, intentionally conservative calibration. PF is capped to avoid one
    # outlier dominating the confidence score.
    pf_part = min(max((pf - 0.75) / 1.50, 0.0), 1.0)
    win_part = min(max((wins - 0.30) / 0.40, 0.0), 1.0)
    exp_part = min(max((expectancy + 0.25) / 0.75, 0.0), 1.0)
    evidence_part = min(n / 30.0, 1.0)
    score = 100.0 * (0.40 * pf_part + 0.25 * win_part + 0.25 * exp_part + 0.10 * evidence_part)
    return round(score, 2), n


def adaptive_decision(
    history: pd.DataFrame,
    *,
    ticker: str,
    score_band: str,
    regime: str,
    position_cap_pct: float = 15.0,
) -> AdaptiveDecision:
    history = history.copy() if isinstance(history, pd.DataFrame) else pd.DataFrame()
    if history.empty:
        return AdaptiveDecision(45.0, "UNPROVEN", min(position_cap_pct, 5.0), 45, 50, 50, 50, 50, 0, "no closed evidence available")

    if "exit_date" in history:
        history = history.sort_values("exit_date")
    recent = history.tail(30)
    recent_score, recent_n = _quality(recent, neutral=45.0)
    history_score, history_n = _quality(history, neutral=50.0)

    ticker_frame = history[history.get("ticker", "").astype(str).str.upper() == str(ticker).upper()] if "ticker" in history else pd.DataFrame()
    band_frame = history[history.get("score_band", "").astype(str) == str(score_band)] if "score_band" in history else pd.DataFrame()
    regime_frame = history[history.get("market_regime", "ALL").astype(str) == str(regime)] if "market_regime" in history else history

    ticker_score, _ = _quality(ticker_frame, neutral=50.0)
    band_score, _ = _quality(band_frame, neutral=50.0)
    regime_score, _ = _quality(regime_frame, neutral=50.0)

    final = (
        0.40 * recent_score
        + 0.20 * history_score
        + 0.20 * regime_score
        + 0.10 * band_score
        + 0.10 * ticker_score
    )
    evidence = int(history_n)
    if evidence < 10:
        label, size = "UNPROVEN", min(position_cap_pct, 5.0)
    elif final >= 70:
        label, size = "HIGH", position_cap_pct
    elif final >= 58:
        label, size = "MEDIUM", min(position_cap_pct, 10.0)
    elif final >= 48:
        label, size = "LOW", min(position_cap_pct, 5.0)
    else:
        label, size = "BLOCK", 0.0

    reason = (
        f"recent {recent_score:.1f}; history {history_score:.1f}; regime {regime_score:.1f}; "
        f"band {band_score:.1f}; ticker {ticker_score:.1f}"
    )
    return AdaptiveDecision(
        round(final, 2), label, round(size, 2), recent_score, history_score,
        regime_score, band_score, ticker_score, evidence, reason,
    )


def apply_adaptive_confidence(
    trades: pd.DataFrame,
    *,
    enabled: bool = True,
    position_cap_pct: float = 15.0,
) -> pd.DataFrame:
    """Apply v14 confidence without look-ahead and recalculate portfolio returns."""
    if trades is None or trades.empty:
        output = trades.copy() if isinstance(trades, pd.DataFrame) else pd.DataFrame()
        for column in V14_COLUMNS:
            output[column] = pd.Series(dtype="object")
        return output

    output = trades.copy()
    output["entry_date"] = pd.to_datetime(output["entry_date"], errors="coerce")
    output["exit_date"] = pd.to_datetime(output["exit_date"], errors="coerce")
    if "market_regime" not in output:
        output["market_regime"] = "ALL"
    output["_v14_order"] = range(len(output))
    rows = []
    for _, trade in output.sort_values(["entry_date", "ticker", "_v14_order"]).iterrows():
        eligible = output[output["exit_date"] < trade["entry_date"]]
        decision = adaptive_decision(
            eligible,
            ticker=str(trade.get("ticker", "")),
            score_band=str(trade.get("score_band", "")),
            regime=str(trade.get("market_regime", "ALL")),
            position_cap_pct=position_cap_pct,
        )
        legacy = float(trade.get("v92_position_size_pct", trade.get("position_size_pct", position_cap_pct)) or 0.0)
        size = min(legacy, decision.size_pct, position_cap_pct) if enabled else legacy
        raw_return = float(trade.get("return_pct", 0.0) or 0.0)
        row = trade.to_dict()
        row.update({
            "v14_confidence_score": decision.score if enabled else 0.0,
            "v14_confidence_label": decision.label if enabled else "OFF",
            "v14_position_size_pct": round(size, 2),
            "v14_portfolio_return_pct": round(raw_return * size / 100.0, 4),
            "v14_recent_component": decision.recent_component,
            "v14_history_component": decision.history_component,
            "v14_regime_component": decision.regime_component,
            "v14_score_band_component": decision.score_band_component,
            "v14_ticker_component": decision.ticker_component,
            "v14_evidence_trades": decision.evidence_trades,
            "v14_reason": decision.reason if enabled else "v14 adaptive confidence disabled",
        })
        rows.append(row)
    return pd.DataFrame(rows).sort_values("_v14_order").drop(columns=["_v14_order"]).reset_index(drop=True)


def holding_period_diagnostics(trades: pd.DataFrame) -> pd.DataFrame:
    """Measure whether longer swing holds improve expectancy and profit factor."""
    columns = ["holding_bucket", "trades", "win_rate_pct", "average_return_pct", "median_return_pct", "total_return_pct", "profit_factor"]
    if trades is None or trades.empty or "holding_days" not in trades:
        return pd.DataFrame(columns=columns)
    work = trades.copy()
    work["holding_days"] = pd.to_numeric(work["holding_days"], errors="coerce")
    work["return_pct"] = pd.to_numeric(work["return_pct"], errors="coerce")
    bins = [0, 5, 10, 20, 40, float("inf")]
    labels = ["1-5", "6-10", "11-20", "21-40", "40+"]
    work["holding_bucket"] = pd.cut(work["holding_days"], bins=bins, labels=labels, include_lowest=True)
    rows = []
    for bucket, group in work.groupby("holding_bucket", observed=False):
        values = group["return_pct"].dropna()
        if values.empty:
            continue
        gp = float(values.clip(lower=0).sum())
        gl = abs(float(values.clip(upper=0).sum()))
        rows.append({
            "holding_bucket": str(bucket), "trades": len(values),
            "win_rate_pct": round(float((values > 0).mean() * 100), 2),
            "average_return_pct": round(float(values.mean()), 4),
            "median_return_pct": round(float(values.median()), 4),
            "total_return_pct": round(float(values.sum()), 2),
            "profit_factor": round(gp / gl, 3) if gl else (float("inf") if gp else 0.0),
        })
    return pd.DataFrame(rows, columns=columns)


def confidence_diagnostics(trades: pd.DataFrame) -> pd.DataFrame:
    if trades is None or trades.empty or "v14_confidence_label" not in trades:
        return pd.DataFrame()
    rows = []
    for label, group in trades.groupby("v14_confidence_label", dropna=False):
        values = pd.to_numeric(group["return_pct"], errors="coerce").dropna()
        gp = float(values.clip(lower=0).sum())
        gl = abs(float(values.clip(upper=0).sum()))
        rows.append({
            "confidence": label, "trades": len(values),
            "win_rate_pct": round(float((values > 0).mean() * 100), 2) if len(values) else 0.0,
            "average_return_pct": round(float(values.mean()), 4) if len(values) else 0.0,
            "profit_factor": round(gp / gl, 3) if gl else (float("inf") if gp else 0.0),
            "average_size_pct": round(float(pd.to_numeric(group["v14_position_size_pct"], errors="coerce").mean()), 2),
        })
    return pd.DataFrame(rows).sort_values("confidence")
