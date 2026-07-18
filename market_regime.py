from __future__ import annotations

import math
import pandas as pd

from engine.indicators import enrich_price_frame

REGIME_TICKERS = ["SPY", "QQQ"]


def _safe_float(value, default: float = 0.0) -> float:
    try:
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return default
        return number
    except Exception:
        return default


def analyse_index(ticker: str, prices: pd.DataFrame) -> dict:
    if prices is None or prices.empty:
        return {"ticker": ticker, "status": "MISSING", "score": 0, "trend": "UNKNOWN", "reason": "No market data"}

    enriched = enrich_price_frame(prices)
    if enriched.empty:
        return {"ticker": ticker, "status": "MISSING", "score": 0, "trend": "UNKNOWN", "reason": "No usable market data"}

    latest = enriched.iloc[-1]
    close = _safe_float(latest.get("Close"))
    sma_20 = _safe_float(latest.get("sma_20"))
    sma_50 = _safe_float(latest.get("sma_50"))
    sma_200 = _safe_float(latest.get("sma_200"))
    rsi = _safe_float(latest.get("rsi_14"), 50)
    change_20d = _safe_float(latest.get("change_20d_pct"))
    change_60d = _safe_float(latest.get("change_60d_pct"))
    volatility = _safe_float(latest.get("volatility_20d_pct"))

    score = 0
    reasons = []

    if close > sma_20 > 0:
        score += 12; reasons.append("above 20D")
    if close > sma_50 > 0:
        score += 14; reasons.append("above 50D")
    if close > sma_200 > 0:
        score += 14; reasons.append("above 200D")
    if sma_20 > sma_50 > 0:
        score += 10; reasons.append("20D above 50D")
    if sma_50 > sma_200 > 0:
        score += 8; reasons.append("50D above 200D")

    if 2 <= change_20d <= 15:
        score += 12; reasons.append("healthy 20D momentum")
    elif change_20d > 15:
        score += 4; reasons.append("extended 20D momentum")
    elif change_20d < -5:
        score -= 10; reasons.append("weak 20D momentum")

    if 5 <= change_60d <= 30:
        score += 8; reasons.append("healthy 60D momentum")
    elif change_60d < -8:
        score -= 10; reasons.append("weak 60D momentum")

    if 45 <= rsi <= 68:
        score += 8; reasons.append("constructive RSI")
    elif rsi > 75:
        score -= 8; reasons.append("overheated RSI")
    elif rsi < 40:
        score -= 8; reasons.append("weak RSI")

    if volatility > 4.5:
        score -= 10; reasons.append("high volatility")
    elif 0 < volatility <= 2.5:
        score += 4; reasons.append("controlled volatility")

    score = max(0, min(100, int(round(score))))

    if score >= 70:
        trend = "BULLISH"
    elif score >= 45:
        trend = "NEUTRAL"
    else:
        trend = "BEARISH"

    return {
        "ticker": ticker,
        "status": "READY",
        "score": score,
        "trend": trend,
        "close": round(close, 2),
        "sma_20": round(sma_20, 2),
        "sma_50": round(sma_50, 2),
        "sma_200": round(sma_200, 2),
        "rsi_14": round(rsi, 1),
        "change_20d_pct": round(change_20d, 2),
        "change_60d_pct": round(change_60d, 2),
        "volatility_20d_pct": round(volatility, 2),
        "reason": "; ".join(reasons) if reasons else "mixed market conditions",
    }


def build_market_regime(price_map: dict[str, pd.DataFrame]) -> dict:
    analyses = [analyse_index(ticker, price_map.get(ticker)) for ticker in REGIME_TICKERS]
    ready = [item for item in analyses if item.get("status") == "READY"]

    if not ready:
        return {
            "regime": "UNKNOWN",
            "market_score": 0,
            "regime_adjustment": 0,
            "risk_label": "UNKNOWN",
            "reason": "No SPY/QQQ market data available",
            "indices": analyses,
        }

    score_map = {item["ticker"]: item["score"] for item in ready}
    spy_score = score_map.get("SPY", 0)
    qqq_score = score_map.get("QQQ", spy_score)
    market_score = int(round((spy_score * 0.45) + (qqq_score * 0.55)))

    if market_score >= 72:
        regime, adjustment, risk_label = "RISK_ON", 6, "Supportive"
    elif market_score >= 55:
        regime, adjustment, risk_label = "CONSTRUCTIVE", 3, "Positive"
    elif market_score >= 40:
        regime, adjustment, risk_label = "NEUTRAL", 0, "Mixed"
    elif market_score >= 25:
        regime, adjustment, risk_label = "DEFENSIVE", -5, "Cautious"
    else:
        regime, adjustment, risk_label = "RISK_OFF", -10, "Hostile"

    return {
        "regime": regime,
        "market_score": market_score,
        "regime_adjustment": adjustment,
        "risk_label": risk_label,
        "reason": "; ".join([f"{item['ticker']} {item['trend']} {item['score']}" for item in ready]),
        "indices": analyses,
    }


def apply_market_regime(scan_frame: pd.DataFrame, regime: dict) -> pd.DataFrame:
    if scan_frame is None or scan_frame.empty:
        return pd.DataFrame()

    output = scan_frame.copy()
    adjustment = int(regime.get("regime_adjustment", 0))
    label = regime.get("regime", "UNKNOWN")

    output["base_score"] = output["score"]
    output["market_regime"] = label
    output["market_score"] = int(regime.get("market_score", 0))
    output["market_adjustment"] = adjustment

    adjusted_scores = []
    adjusted_signals = []

    for _, row in output.iterrows():
        original = _safe_float(row.get("score"))
        signal = str(row.get("signal", "IGNORE"))
        effective_adjustment = adjustment
        if signal == "IGNORE" and adjustment > 0:
            effective_adjustment = min(adjustment, 2)

        new_score = max(0, min(100, int(round(original + effective_adjustment))))
        adjusted_scores.append(new_score)

        if new_score >= 78 and label in {"RISK_ON", "CONSTRUCTIVE", "NEUTRAL"}:
            adjusted_signals.append("BUY")
        elif new_score >= 55:
            adjusted_signals.append("WATCH")
        else:
            adjusted_signals.append("IGNORE")

    output["score"] = adjusted_scores
    output["signal"] = adjusted_signals
    output["regime_reason"] = regime.get("reason", "")
    return output
