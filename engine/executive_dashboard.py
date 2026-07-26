from __future__ import annotations

import math
import pandas as pd


def _number(value, default: float = 0.0) -> float:
    try:
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return default
        return number
    except (TypeError, ValueError):
        return default


def _numeric_series(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    """Return a numeric Series aligned to frame.index, even when column is missing."""
    if column in frame.columns:
        return pd.to_numeric(frame[column], errors="coerce").fillna(default)
    return pd.Series(default, index=frame.index, dtype=float)


def confidence_grade(score: float) -> str:
    score = _number(score)
    if score >= 90:
        return "A+"
    if score >= 84:
        return "A"
    if score >= 78:
        return "A-"
    if score >= 72:
        return "B+"
    if score >= 66:
        return "B"
    if score >= 60:
        return "B-"
    if score >= 55:
        return "C+"
    if score >= 48:
        return "C"
    return "D"


def market_health(regime: dict | None, scan: pd.DataFrame | None) -> dict:
    regime = regime or {}
    frame = scan if isinstance(scan, pd.DataFrame) else pd.DataFrame()
    market_score = int(round(_number(regime.get("market_score"))))

    if frame.empty:
        breadth = 0.0
        above_50 = 0.0
        bullish = 0.0
    else:
        close = _numeric_series(frame, "close", default=float("nan"))
        sma_50 = _numeric_series(frame, "sma_50", default=float("nan"))
        valid = close.notna() & sma_50.notna() & (sma_50 > 0)
        above_50 = float((close[valid] > sma_50[valid]).mean() * 100) if valid.any() else 0.0
        trends = frame.get("trend", pd.Series(index=frame.index, dtype=str)).astype(str)
        bullish = float(trends.isin(["TREND", "RECOVERING"]).mean() * 100) if len(frame) else 0.0
        breadth = round((above_50 * 0.65) + (bullish * 0.35), 1)

    composite = int(round((market_score * 0.60) + (breadth * 0.40)))
    if composite >= 72:
        label, tone = "Strong", "positive"
    elif composite >= 55:
        label, tone = "Constructive", "positive"
    elif composite >= 40:
        label, tone = "Mixed", "info"
    elif composite >= 25:
        label, tone = "Weak", "warning"
    else:
        label, tone = "Hostile", "warning"

    regime_name = str(regime.get("regime", "UNKNOWN"))
    risk_state = "RISK ON" if regime_name in {"RISK_ON", "CONSTRUCTIVE"} else "RISK OFF" if regime_name in {"RISK_OFF", "DEFENSIVE"} else "NEUTRAL"
    return {
        "score": composite,
        "label": label,
        "tone": tone,
        "risk_state": risk_state,
        "breadth": round(breadth, 1),
        "above_50_pct": round(above_50, 1),
        "bullish_trend_pct": round(bullish, 1),
    }


def vix_snapshot(regime: dict | None) -> dict:
    regime = regime or {}
    vix = regime.get("vix", {}) if isinstance(regime.get("vix", {}), dict) else {}
    level = _number(vix.get("close"), 0.0)
    if level <= 0:
        return {"level": None, "label": "Unavailable", "tone": "info"}
    if level < 15:
        label, tone = "Calm", "positive"
    elif level < 20:
        label, tone = "Normal", "positive"
    elif level < 25:
        label, tone = "Elevated", "warning"
    elif level < 35:
        label, tone = "High", "warning"
    else:
        label, tone = "Extreme", "warning"
    return {"level": round(level, 2), "label": label, "tone": tone, "change_20d_pct": _number(vix.get("change_20d_pct"))}


def ranked_opportunities(scan: pd.DataFrame | None, plans: pd.DataFrame | None, limit: int = 8) -> pd.DataFrame:
    frame = scan.copy() if isinstance(scan, pd.DataFrame) else pd.DataFrame()
    plan_frame = plans.copy() if isinstance(plans, pd.DataFrame) else pd.DataFrame()
    if frame.empty:
        return pd.DataFrame()

    selected = frame[frame.get("signal", pd.Series(index=frame.index, dtype=str)).isin(["BUY", "WATCH"])].copy()
    if selected.empty:
        return pd.DataFrame()

    if not plan_frame.empty and "ticker" in plan_frame.columns:
        merge_cols = [c for c in ["ticker", "entry_price", "target_price", "stop_loss", "risk_reward", "position_quality"] if c in plan_frame.columns]
        selected = selected.merge(plan_frame[merge_cols], on="ticker", how="left")

    score = _numeric_series(selected, "score")
    selected["score"] = score
    selected["confidence"] = score.map(confidence_grade)
    rr = _numeric_series(selected, "risk_reward")
    selected["opportunity_rank"] = score + rr.clip(0, 5) * 2
    selected = selected.sort_values(["opportunity_rank", "score"], ascending=False).head(limit)
    columns = ["ticker", "signal", "confidence", "score", "trend", "change_20d_pct", "rsi_14", "entry_price", "target_price", "stop_loss", "risk_reward"]
    return selected[[c for c in columns if c in selected.columns]].reset_index(drop=True)


def best_trade(opportunities: pd.DataFrame | None) -> dict:
    if not isinstance(opportunities, pd.DataFrame) or opportunities.empty:
        return {}
    return opportunities.iloc[0].to_dict()
