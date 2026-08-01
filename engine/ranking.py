from __future__ import annotations

import math
import pandas as pd


RANKING_COLUMNS = [
    "priority_rank",
    "priority_score",
    "confidence_band",
    "relative_strength_percentile",
    "momentum_consistency",
    "risk_quality",
]


def _numeric(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce").fillna(default)


def _percentile(series: pd.Series, *, higher_is_better: bool = True) -> pd.Series:
    """Return stable cross-sectional percentile scores from 0 to 100."""
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() <= 1:
        return pd.Series(50.0, index=series.index)
    ranked = numeric.rank(
        method="average",
        pct=True,
        ascending=higher_is_better,
        na_option="bottom",
    )
    if not higher_is_better:
        ranked = numeric.rank(
            method="average",
            pct=True,
            ascending=False,
            na_option="bottom",
        )
    return (ranked * 100).clip(0, 100)


def _momentum_consistency(frame: pd.DataFrame) -> pd.Series:
    change_1d = _numeric(frame, "change_1d_pct")
    change_20d = _numeric(frame, "change_20d_pct")
    change_60d = _numeric(frame, "change_60d_pct")
    rsi = _numeric(frame, "rsi_14", 50)

    score = pd.Series(0.0, index=frame.index)
    score += (change_20d > 0).astype(float) * 25
    score += (change_60d > 0).astype(float) * 25
    score += (change_60d >= change_20d).astype(float) * 15
    score += change_1d.between(-3, 5).astype(float) * 10
    score += rsi.between(45, 72).astype(float) * 25
    return score.clip(0, 100)


def _risk_quality(frame: pd.DataFrame) -> pd.Series:
    volatility = _numeric(frame, "volatility_20d_pct")
    extension_penalty = _numeric(frame, "extension_penalty")
    volatility_penalty = _numeric(frame, "volatility_penalty")

    volatility_quality = (100 - volatility.clip(0, 8) * 10).clip(20, 100)
    penalty_quality = (
        100
        + extension_penalty.clip(-20, 0) * 3
        + volatility_penalty.clip(-20, 0) * 2
    ).clip(0, 100)
    return (0.55 * volatility_quality + 0.45 * penalty_quality).clip(0, 100)


def _confidence_band(priority_score: float, signal: str) -> str:
    signal = str(signal or "").upper()
    if signal == "BUY" and priority_score >= 82:
        return "A"
    if signal in {"BUY", "WATCH"} and priority_score >= 70:
        return "B"
    if signal in {"BUY", "WATCH"} and priority_score >= 58:
        return "C"
    return "D"


def rank_candidates(frame: pd.DataFrame) -> pd.DataFrame:
    """Add cross-sectional priority ranking without changing trading signals.

    Existing score and signal remain the strategy decision. Priority ranking
    sorts those decisions using the strength of each candidate relative to the
    rest of the current scan universe.
    """
    if frame is None or frame.empty:
        output = frame.copy() if isinstance(frame, pd.DataFrame) else pd.DataFrame()
        for column in RANKING_COLUMNS:
            output[column] = pd.Series(dtype="float64")
        return output

    output = frame.copy()
    change_20d = _numeric(output, "change_20d_pct")
    change_60d = _numeric(output, "change_60d_pct")
    volume_ratio = _numeric(output, "volume_ratio", 1)
    high_52w = _numeric(output, "high_52w")
    close = _numeric(output, "close")

    proximity = pd.Series(-100.0, index=output.index)
    valid_high = high_52w > 0
    proximity.loc[valid_high] = (
        close.loc[valid_high] / high_52w.loc[valid_high] - 1
    ) * 100

    rs_percentile = (
        0.35 * _percentile(change_20d)
        + 0.40 * _percentile(change_60d)
        + 0.15 * _percentile(proximity)
        + 0.10 * _percentile(volume_ratio)
    ).clip(0, 100)

    consistency = _momentum_consistency(output)
    risk_quality = _risk_quality(output)
    strategy_score = _numeric(output, "score")

    priority_score = (
        0.55 * strategy_score
        + 0.25 * rs_percentile
        + 0.10 * consistency
        + 0.10 * risk_quality
    ).round(1).clip(0, 100)

    output["relative_strength_percentile"] = rs_percentile.round(1)
    output["momentum_consistency"] = consistency.round(1)
    output["risk_quality"] = risk_quality.round(1)
    output["priority_score"] = priority_score
    output["confidence_band"] = [
        _confidence_band(score, signal)
        for score, signal in zip(
            output["priority_score"],
            output.get("signal", pd.Series("", index=output.index)),
        )
    ]

    signal_order = output.get(
        "signal",
        pd.Series("IGNORE", index=output.index),
    ).map({"BUY": 0, "WATCH": 1, "IGNORE": 2}).fillna(9)

    output["_signal_order_rank"] = signal_order
    output = output.sort_values(
        ["_signal_order_rank", "priority_score", "score", "ticker"],
        ascending=[True, False, False, True],
    ).drop(columns=["_signal_order_rank"])

    output["priority_rank"] = range(1, len(output) + 1)
    return output.reset_index(drop=True)
