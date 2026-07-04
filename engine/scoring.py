import math
import pandas as pd
def _safe(value: float, default: float = 0.0) -> float:
    try:
        value = float(value)
        return default if math.isnan(value) or math.isinf(value) else value
    except (TypeError, ValueError):
        return default
def score_latest(row: pd.Series) -> tuple[int, str, str, str]:
    close, sma20, sma50, sma200 = _safe(row.get("Close")), _safe(row.get("SMA20")), _safe(row.get("SMA50")), _safe(row.get("SMA200"))
    rsi14, vol_ratio, change20 = _safe(row.get("RSI14"),50), _safe(row.get("VolumeRatio"),1), _safe(row.get("Change20D"))
    score, reasons = 0, []
    if close > sma20 > 0: score += 15; reasons.append("above 20-day average")
    if sma20 > sma50 > 0: score += 15; reasons.append("short-term trend rising")
    if close > sma50 > 0: score += 15; reasons.append("above 50-day average")
    if sma50 > sma200 > 0: score += 20; reasons.append("long-term trend rising")
    if 50 <= rsi14 <= 68: score += 15; reasons.append("healthy momentum")
    elif 40 <= rsi14 < 50: score += 7
    elif rsi14 > 75: score -= 10; reasons.append("overbought")
    if vol_ratio >= 1.20: score += 10; reasons.append("strong volume")
    elif vol_ratio >= 1.0: score += 5
    if 2 <= change20 <= 18: score += 10; reasons.append("positive 20-day return")
    elif change20 > 25: score -= 8; reasons.append("extended move")
    score = max(0, min(100, int(round(score))))
    trend = "TREND" if close > sma50 > sma200 > 0 else ("RECOVERING" if close > sma20 > 0 else "WEAK")
    signal = "BUY" if score >= 75 and trend == "TREND" else ("WATCH" if score >= 55 else "IGNORE")
    return score, signal, trend, ", ".join(reasons[:4]) if reasons else "No qualifying setup"
