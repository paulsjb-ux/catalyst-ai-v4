from __future__ import annotations

"""Catalyst AI v14.1 research diagnostics.

These diagnostics explain *why* adaptive decisions were reduced/blocked, isolate
stress-test failure drivers, attribute outcomes to confidence components, and
compare confidence bands with observed win rates. They are descriptive research
tools; they do not alter trade selection or returns.
"""

from typing import Any
import math
import pandas as pd


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if frame is None or frame.empty or column not in frame.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _summary_from_returns(values: pd.Series) -> dict[str, Any]:
    values = pd.to_numeric(values, errors="coerce").dropna()
    if values.empty:
        return {"trades": 0, "win_rate_pct": 0.0, "average_return_pct": 0.0,
                "total_return_pct": 0.0, "profit_factor": 0.0, "max_drawdown_pct": 0.0}
    winners = values[values > 0]
    losers = values[values <= 0]
    gp = float(winners.sum())
    gl = abs(float(losers.sum()))
    pf: float | str = gp / gl if gl else (math.inf if gp else 0.0)
    equity = (1.0 + values / 100.0).cumprod()
    dd = equity / equity.cummax() - 1.0
    return {
        "trades": int(len(values)),
        "win_rate_pct": round(float((values > 0).mean() * 100.0), 2),
        "average_return_pct": round(float(values.mean()), 4),
        "total_return_pct": round(float((equity.iloc[-1] - 1.0) * 100.0), 2),
        "profit_factor": round(float(pf), 3) if math.isfinite(float(pf)) else "∞",
        "max_drawdown_pct": round(float(dd.min() * 100.0), 2),
    }


def decision_filter_diagnostics(trades: pd.DataFrame) -> pd.DataFrame:
    """Explain adaptive size reductions and blocks using the five v14 components."""
    columns = ["reason", "trades", "share_pct", "average_return_pct", "profit_factor"]
    if trades is None or trades.empty:
        return pd.DataFrame(columns=columns)

    work = trades.copy()
    reasons: list[list[str]] = []
    component_map = {
        "Weak recent evidence": "v14_recent_component",
        "Weak historical evidence": "v14_history_component",
        "Weak regime evidence": "v14_regime_component",
        "Weak score-band evidence": "v14_score_band_component",
        "Weak ticker evidence": "v14_ticker_component",
    }
    for _, row in work.iterrows():
        row_reasons: list[str] = []
        evidence = float(pd.to_numeric(pd.Series([row.get("v14_evidence_trades")]), errors="coerce").fillna(0).iloc[0])
        label = str(row.get("v14_confidence_label", "")).upper()
        if evidence < 10 or label == "UNPROVEN":
            row_reasons.append("Insufficient closed evidence")
        for name, col in component_map.items():
            value = pd.to_numeric(pd.Series([row.get(col)]), errors="coerce").iloc[0]
            if pd.notna(value) and float(value) < 48.0:
                row_reasons.append(name)
        if label == "BLOCK":
            row_reasons.append("Final confidence below block threshold")
        elif label == "LOW":
            row_reasons.append("Final confidence limited to low size")
        elif label == "MEDIUM":
            row_reasons.append("Final confidence limited to medium size")
        if not row_reasons:
            row_reasons.append("No adaptive restriction")
        reasons.append(row_reasons)

    work["_reasons"] = reasons
    exploded = work.explode("_reasons")
    total = max(len(work), 1)
    rows = []
    for reason, group in exploded.groupby("_reasons", dropna=False):
        values = _numeric(group, "return_pct").dropna()
        summary = _summary_from_returns(values)
        rows.append({
            "reason": str(reason),
            "trades": int(len(group)),
            "share_pct": round(float(len(group) / total * 100.0), 2),
            "average_return_pct": summary["average_return_pct"],
            "profit_factor": summary["profit_factor"],
        })
    return pd.DataFrame(rows, columns=columns).sort_values(["trades", "reason"], ascending=[False, True]).reset_index(drop=True)


def stress_decomposition(
    trades: pd.DataFrame,
    *,
    return_column: str,
    additional_cost_pct: float = 0.20,
    entry_delay_penalty_pct: float = 0.15,
) -> pd.DataFrame:
    """Isolate the contribution of costs and delayed entry to stress failure."""
    columns = ["scenario", "cost_pct", "delay_penalty_pct", "trades", "average_return_pct",
               "total_return_pct", "profit_factor", "max_drawdown_pct"]
    if trades is None or trades.empty or return_column not in trades.columns:
        return pd.DataFrame(columns=columns)
    base = _numeric(trades, return_column).fillna(0.0)
    scenarios = [
        ("Baseline", 0.0, 0.0),
        ("Additional costs only", abs(float(additional_cost_pct)), 0.0),
        ("Delayed entry only", 0.0, abs(float(entry_delay_penalty_pct))),
        ("Combined stress", abs(float(additional_cost_pct)), abs(float(entry_delay_penalty_pct))),
        ("Half combined stress", abs(float(additional_cost_pct)) / 2.0, abs(float(entry_delay_penalty_pct)) / 2.0),
    ]
    rows = []
    for name, cost, delay in scenarios:
        summary = _summary_from_returns(base - cost - delay)
        rows.append({"scenario": name, "cost_pct": round(cost, 4), "delay_penalty_pct": round(delay, 4), **summary})
    return pd.DataFrame(rows, columns=columns)


def feature_attribution(trades: pd.DataFrame) -> pd.DataFrame:
    """Compare component strength in winners and losers and rank observed lift."""
    columns = ["component", "winner_average", "loser_average", "winner_lift", "return_correlation", "observations"]
    if trades is None or trades.empty or "return_pct" not in trades.columns:
        return pd.DataFrame(columns=columns)
    components = {
        "Recent performance": "v14_recent_component",
        "Historical performance": "v14_history_component",
        "Market regime": "v14_regime_component",
        "Score band": "v14_score_band_component",
        "Ticker quality": "v14_ticker_component",
        "Final confidence": "v14_confidence_score",
    }
    returns = _numeric(trades, "return_pct")
    rows = []
    for name, col in components.items():
        values = _numeric(trades, col)
        valid = pd.DataFrame({"component": values, "return": returns}).dropna()
        if valid.empty:
            continue
        winners = valid.loc[valid["return"] > 0, "component"]
        losers = valid.loc[valid["return"] <= 0, "component"]
        winner_avg = float(winners.mean()) if not winners.empty else 0.0
        loser_avg = float(losers.mean()) if not losers.empty else 0.0
        correlation = float(valid["component"].corr(valid["return"])) if len(valid) > 1 else 0.0
        if math.isnan(correlation):
            correlation = 0.0
        rows.append({
            "component": name,
            "winner_average": round(winner_avg, 2),
            "loser_average": round(loser_avg, 2),
            "winner_lift": round(winner_avg - loser_avg, 2),
            "return_correlation": round(correlation, 4),
            "observations": int(len(valid)),
        })
    return pd.DataFrame(rows, columns=columns).sort_values("winner_lift", ascending=False).reset_index(drop=True)


def confidence_calibration(trades: pd.DataFrame) -> pd.DataFrame:
    """Compare adaptive confidence ranges with realised win rate and returns."""
    columns = ["confidence_band", "trades", "average_confidence", "observed_win_rate_pct",
               "calibration_gap_pct", "average_return_pct", "profit_factor"]
    if trades is None or trades.empty or "v14_confidence_score" not in trades.columns:
        return pd.DataFrame(columns=columns)
    work = trades.copy()
    work["_confidence"] = _numeric(work, "v14_confidence_score")
    work["_return"] = _numeric(work, "return_pct")
    bins = [-0.001, 47.999, 57.999, 69.999, 100.0]
    labels = ["BLOCK / <48", "LOW / 48-57", "MEDIUM / 58-69", "HIGH / 70+"]
    work["confidence_band"] = pd.cut(work["_confidence"], bins=bins, labels=labels, include_lowest=True)
    rows = []
    for band, group in work.groupby("confidence_band", observed=False):
        valid = group.dropna(subset=["_confidence", "_return"])
        if valid.empty:
            continue
        summary = _summary_from_returns(valid["_return"])
        avg_conf = float(valid["_confidence"].mean())
        win_rate = float((valid["_return"] > 0).mean() * 100.0)
        rows.append({
            "confidence_band": str(band),
            "trades": int(len(valid)),
            "average_confidence": round(avg_conf, 2),
            "observed_win_rate_pct": round(win_rate, 2),
            "calibration_gap_pct": round(win_rate - avg_conf, 2),
            "average_return_pct": summary["average_return_pct"],
            "profit_factor": summary["profit_factor"],
        })
    return pd.DataFrame(rows, columns=columns)
