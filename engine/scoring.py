from __future__ import annotations

import math

import pandas as pd


def _safe_float(value, default: float = 0.0) -> float:
    try:
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return default
        return number
    except Exception:
        return default


def score_trend_strength(row: pd.Series) -> int:
    """Score how cleanly price is trending above key moving averages."""
    close = _safe_float(row.get("close"))
    sma_20 = _safe_float(row.get("sma_20"))
    sma_50 = _safe_float(row.get("sma_50"))
    sma_200 = _safe_float(row.get("sma_200"))

    score = 0

    if close > sma_20 > 0:
        score += 8
    if close > sma_50 > 0:
        score += 8
    if close > sma_200 > 0:
        score += 6
    if sma_20 > sma_50 > 0:
        score += 6
    if sma_50 > sma_200 > 0:
        score += 4

    return min(score, 32)


def score_momentum(row: pd.Series) -> int:
    """Reward constructive medium-term momentum but avoid pure blow-off moves."""
    change_20d = _safe_float(row.get("change_20d_pct"))
    change_60d = _safe_float(row.get("change_60d_pct"))
    rsi = _safe_float(row.get("rsi_14"))

    score = 0

    if 3 <= change_20d <= 18:
        score += 10
    elif 0 < change_20d < 3:
        score += 5
    elif 18 < change_20d <= 35:
        score += 5
    elif change_20d < -8:
        score -= 5

    if 5 <= change_60d <= 40:
        score += 8
    elif 0 < change_60d < 5:
        score += 4
    elif change_60d > 60:
        score -= 4

    if 45 <= rsi <= 68:
        score += 8
    elif 68 < rsi <= 75:
        score += 3
    elif rsi > 75:
        score -= 6
    elif rsi < 40:
        score -= 4

    return max(min(score, 26), -10)


def score_volume_confirmation(row: pd.Series) -> int:
    """Reward demand confirmation without overreacting to one-day spikes."""
    volume_ratio = _safe_float(row.get("volume_ratio"))

    if 1.15 <= volume_ratio <= 2.5:
        return 12
    if 1.0 <= volume_ratio < 1.15:
        return 7
    if 0.8 <= volume_ratio < 1.0:
        return 3
    if volume_ratio > 3.5:
        return 2
    return 0


def score_relative_strength_proxy(row: pd.Series) -> int:
    """Proxy relative strength using price position and multi-period returns.

    This is not true benchmark-relative strength yet. It is a simple internal
    proxy until market index context is added.
    """
    close = _safe_float(row.get("close"))
    high_52w = _safe_float(row.get("high_52w"))
    change_20d = _safe_float(row.get("change_20d_pct"))
    change_60d = _safe_float(row.get("change_60d_pct"))

    score = 0

    if high_52w > 0:
        distance_from_high = ((close / high_52w) - 1) * 100
        if -10 <= distance_from_high <= 0:
            score += 10
        elif -20 <= distance_from_high < -10:
            score += 5
        elif distance_from_high < -35:
            score -= 4

    if change_20d > 0 and change_60d > 0:
        score += 8
    elif change_20d > 0 or change_60d > 0:
        score += 4

    return max(min(score, 18), -8)


def penalty_volatility(row: pd.Series) -> int:
    """Penalise unusually jumpy names."""
    volatility_20d = _safe_float(row.get("volatility_20d_pct"))

    if volatility_20d <= 0:
        return 0
    if volatility_20d <= 2.5:
        return 0
    if volatility_20d <= 4:
        return -4
    if volatility_20d <= 6:
        return -8
    return -12


def penalty_overextension(row: pd.Series) -> int:
    """Penalise candidates too extended above short-term trend."""
    close = _safe_float(row.get("close"))
    sma_20 = _safe_float(row.get("sma_20"))
    rsi = _safe_float(row.get("rsi_14"))
    change_20d = _safe_float(row.get("change_20d_pct"))

    penalty = 0

    if close > 0 and sma_20 > 0:
        extension = ((close / sma_20) - 1) * 100
        if extension > 18:
            penalty -= 12
        elif extension > 12:
            penalty -= 8
        elif extension > 8:
            penalty -= 4

    if rsi > 78:
        penalty -= 8
    elif rsi > 72:
        penalty -= 4

    if change_20d > 40:
        penalty -= 8
    elif change_20d > 28:
        penalty -= 4

    return penalty


def score_quality(row: pd.Series) -> dict:
    """Return smarter score components and final score."""
    trend_score = score_trend_strength(row)
    momentum_score = score_momentum(row)
    volume_score = score_volume_confirmation(row)
    relative_score = score_relative_strength_proxy(row)
    volatility_adjustment = penalty_volatility(row)
    extension_adjustment = penalty_overextension(row)

    raw_score = (
        trend_score
        + momentum_score
        + volume_score
        + relative_score
        + volatility_adjustment
        + extension_adjustment
    )

    final_score = max(0, min(100, int(round(raw_score))))

    return {
        "trend_score": trend_score,
        "momentum_score": momentum_score,
        "volume_score": volume_score,
        "relative_strength_score": relative_score,
        "volatility_penalty": volatility_adjustment,
        "extension_penalty": extension_adjustment,
        "score": final_score,
    }


def assign_signal(row: pd.Series) -> str:
    """Assign BUY/WATCH/IGNORE using score plus guardrails."""
    score = _safe_float(row.get("score"))
    trend_score = _safe_float(row.get("trend_score"))
    momentum_score = _safe_float(row.get("momentum_score"))
    volatility_penalty = _safe_float(row.get("volatility_penalty"))
    extension_penalty = _safe_float(row.get("extension_penalty"))

    # Guardrails: no BUY if the setup is too extended or too volatile.
    if score >= 78 and trend_score >= 22 and momentum_score >= 12 and volatility_penalty > -10 and extension_penalty > -10:
        return "BUY"

    if score >= 55:
        return "WATCH"

    return "IGNORE"


def explain_score(row: pd.Series) -> str:
    """Human-readable score explanation."""
    parts = []

    if _safe_float(row.get("trend_score")) >= 22:
        parts.append("strong trend")
    elif _safe_float(row.get("trend_score")) >= 14:
        parts.append("developing trend")

    if _safe_float(row.get("momentum_score")) >= 16:
        parts.append("healthy momentum")
    elif _safe_float(row.get("momentum_score")) < 0:
        parts.append("weak momentum")

    if _safe_float(row.get("volume_score")) >= 7:
        parts.append("volume support")

    if _safe_float(row.get("relative_strength_score")) >= 10:
        parts.append("relative strength")

    if _safe_float(row.get("volatility_penalty")) <= -8:
        parts.append("volatility risk")

    if _safe_float(row.get("extension_penalty")) <= -8:
        parts.append("overextended")

    if not parts:
        parts.append("mixed setup")

    return "; ".join(parts)
