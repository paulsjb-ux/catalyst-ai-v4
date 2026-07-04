from __future__ import annotations

import math
import pandas as pd


def _safe(value: float, default: float = 0.0) -> float:
    try:
        value = float(value)
        return default if math.isnan(value) or math.isinf(value) else value
    except (TypeError, ValueError):
        return default


def score_latest(row: pd.Series) -> tuple[int, str, str, str]:
    close = _safe(row.get("Close"))
    sma20 = _safe(row.get("SMA20"))
    sma50 = _safe(row.get("SMA50"))
    sma200 = _safe(row.get("SMA200"))
    rsi14 = _safe(row.get("RSI14"), 50)
    vol_ratio = _safe(row.get("VolumeRatio"), 1)
    change20 = _safe(row.get("Change20D"))

    score = 0
    reasons: list[str] = []

    if close > sma20 > 0:
        score += 15
        reasons.append("above 20-day average")
    if sma20 > sma50 > 0:
        score += 15
        reasons.append("short-term trend rising")
    if close > sma50 > 0:
        score += 15
        reasons.append("above 50-day average")
    if sma50 > sma200 > 0:
        score += 20
        reasons.append("long-term trend rising")
    if 50 <= rsi14 <= 68:
        score += 15
        reasons.append("healthy momentum")
    elif 40 <= rsi14 < 50:
        score += 7
    elif rsi14 > 75:
        score -= 10
        reasons.append("overbought")
    if vol_ratio >= 1.20:
        score += 10
        reasons.append("strong volume")
    elif vol_ratio >= 1.0:
        score += 5
    if 2 <= change20 <= 18:
        score += 10
        reasons.append("positive 20-day return")
    elif change20 > 25:
        score -= 8
        reasons.append("extended move")

    score = max(0, min(100, int(round(score))))

    if close > sma50 > sma200 > 0:
        trend = "TREND"
    elif close > sma20 > 0:
        trend = "RECOVERING"
    else:
        trend = "WEAK"

    if score >= 75 and trend == "TREND":
        signal = "BUY"
    elif score >= 55:
        signal = "WATCH"
    else:
        signal = "IGNORE"

    reason = ", ".join(reasons[:4]) if reasons else "No qualifying setup"
    return score, signal, trend, reason
