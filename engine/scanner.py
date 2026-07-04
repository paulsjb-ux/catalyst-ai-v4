from __future__ import annotations

import pandas as pd

from engine.indicators import enrich_price_frame
from engine.scoring import assign_signal, explain_score, score_quality


OUTPUT_COLUMNS = [
    "ticker",
    "signal",
    "score",
    "close",
    "change_1d_pct",
    "change_20d_pct",
    "change_60d_pct",
    "rsi_14",
    "volume_ratio",
    "volatility_20d_pct",
    "trend",
    "trend_score",
    "momentum_score",
    "volume_score",
    "relative_strength_score",
    "volatility_penalty",
    "extension_penalty",
    "reason",
    "sma_20",
    "sma_50",
    "sma_200",
    "high_52w",
]


def classify_trend(row: pd.Series) -> str:
    close = float(row.get("close", 0) or 0)
    sma_20 = float(row.get("sma_20", 0) or 0)
    sma_50 = float(row.get("sma_50", 0) or 0)
    sma_200 = float(row.get("sma_200", 0) or 0)

    if close > sma_20 > sma_50 > sma_200 > 0:
        return "TREND"
    if close > sma_20 > sma_50 > 0:
        return "TREND"
    if close > sma_20 > 0 and sma_20 < sma_50:
        return "RECOVERING"
    if close < sma_50 and close < sma_200:
        return "WEAK"
    return "MIXED"


def _latest_indicator_row(ticker: str, prices: pd.DataFrame) -> dict | None:
    enriched = enrich_price_frame(prices)

    if enriched.empty:
        return None

    latest = enriched.iloc[-1]

    row = {
        "ticker": ticker,
        "close": round(float(latest.get("Close", 0) or 0), 2),
        "change_1d_pct": round(float(latest.get("change_1d_pct", 0) or 0), 2),
        "change_20d_pct": round(float(latest.get("change_20d_pct", 0) or 0), 2),
        "change_60d_pct": round(float(latest.get("change_60d_pct", 0) or 0), 2),
        "rsi_14": round(float(latest.get("rsi_14", 50) or 50), 1),
        "volume_ratio": round(float(latest.get("volume_ratio", 1) or 1), 2),
        "volatility_20d_pct": round(float(latest.get("volatility_20d_pct", 0) or 0), 2),
        "sma_20": round(float(latest.get("sma_20", 0) or 0), 2),
        "sma_50": round(float(latest.get("sma_50", 0) or 0), 2),
        "sma_200": round(float(latest.get("sma_200", 0) or 0), 2),
        "high_52w": round(float(latest.get("high_52w", 0) or 0), 2),
    }

    row["trend"] = classify_trend(pd.Series(row))
    row.update(score_quality(pd.Series(row)))
    row["signal"] = assign_signal(pd.Series(row))
    row["reason"] = explain_score(pd.Series(row))

    return row


def run_scan(price_map: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Run smarter candidate scoring across downloaded price data."""
    if not price_map:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    rows: list[dict] = []

    for ticker, prices in price_map.items():
        try:
            row = _latest_indicator_row(str(ticker).upper(), prices)
            if row:
                rows.append(row)
        except Exception:
            continue

    if not rows:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    frame = pd.DataFrame(rows)

    for column in OUTPUT_COLUMNS:
        if column not in frame.columns:
            frame[column] = None

    signal_order = {"BUY": 0, "WATCH": 1, "IGNORE": 2}
    frame["_signal_order"] = frame["signal"].map(signal_order).fillna(9)
    frame = frame.sort_values(["_signal_order", "score", "ticker"], ascending=[True, False, True])
    frame = frame.drop(columns=["_signal_order"])

    return frame[OUTPUT_COLUMNS].reset_index(drop=True)
