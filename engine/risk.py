from __future__ import annotations

import math

import pandas as pd


def atr(frame: pd.DataFrame, window: int = 14) -> pd.Series:
    """Average True Range."""
    if frame is None or frame.empty:
        return pd.Series(dtype=float)

    high = frame["High"]
    low = frame["Low"]
    close = frame["Close"]
    previous_close = close.shift(1)

    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return true_range.rolling(window=window, min_periods=window).mean()


def _safe_float(value, default: float = 0.0) -> float:
    try:
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return default
        return number
    except Exception:
        return default


def build_trade_plan(
    ticker: str,
    signal: str,
    score: float,
    close: float,
    atr_value: float,
    sma_20: float | None = None,
    sma_50: float | None = None,
) -> dict:
    """Create target, stop and risk/reward plan for a candidate."""
    close = _safe_float(close)
    score = _safe_float(score)
    atr_value = _safe_float(atr_value)
    sma_20 = _safe_float(sma_20)
    sma_50 = _safe_float(sma_50)

    if close <= 0:
        return {
            "ticker": ticker,
            "entry_price": None,
            "target_price": None,
            "stop_loss": None,
            "risk_pct": None,
            "reward_pct": None,
            "risk_reward": None,
            "position_quality": "INVALID",
            "plan_reason": "Missing valid close price",
        }

    if atr_value <= 0:
        # Fallback to 4% volatility if ATR is unavailable.
        atr_value = close * 0.04

    entry = close

    # Higher score gets a slightly wider upside objective.
    target_atr_multiple = 2.2 if score >= 85 else 2.0 if score >= 75 else 1.6
    stop_atr_multiple = 1.2 if score >= 80 else 1.4

    target = entry + (atr_value * target_atr_multiple)
    stop_candidates = [entry - (atr_value * stop_atr_multiple)]

    if sma_20 > 0:
        stop_candidates.append(sma_20 * 0.985)

    if sma_50 > 0 and signal == "BUY":
        stop_candidates.append(sma_50 * 0.985)

    # Use the nearest sensible stop below entry.
    valid_stops = [candidate for candidate in stop_candidates if 0 < candidate < entry]
    stop = max(valid_stops) if valid_stops else entry - (atr_value * stop_atr_multiple)

    risk = entry - stop
    reward = target - entry

    risk_pct = (risk / entry) * 100 if entry else None
    reward_pct = (reward / entry) * 100 if entry else None
    risk_reward = reward / risk if risk > 0 else None

    if risk_reward is None:
        quality = "INVALID"
    elif signal == "BUY" and score >= 85 and risk_reward >= 1.8:
        quality = "A"
    elif signal == "BUY" and score >= 75 and risk_reward >= 1.5:
        quality = "B"
    elif signal in {"BUY", "WATCH"} and risk_reward >= 1.2:
        quality = "C"
    else:
        quality = "LOW"

    reason = f"{signal} score {score:.0f}; ATR-based plan; R/R {risk_reward:.2f}" if risk_reward else "Insufficient risk data"

    return {
        "ticker": ticker,
        "entry_price": round(entry, 2),
        "target_price": round(target, 2),
        "stop_loss": round(stop, 2),
        "risk_pct": round(risk_pct, 2) if risk_pct is not None else None,
        "reward_pct": round(reward_pct, 2) if reward_pct is not None else None,
        "risk_reward": round(risk_reward, 2) if risk_reward is not None else None,
        "position_quality": quality,
        "plan_reason": reason,
    }
