from __future__ import annotations

import pandas as pd


def calculate_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    average_gain = gain.rolling(window=window, min_periods=window).mean()
    average_loss = loss.rolling(window=window, min_periods=window).mean()

    rs = average_gain / average_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def enrich_price_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Add indicators needed by the scanner."""
    if frame is None or frame.empty:
        return pd.DataFrame()

    output = frame.copy()
    close = output["Close"]

    output["sma_20"] = close.rolling(20, min_periods=5).mean()
    output["sma_50"] = close.rolling(50, min_periods=10).mean()
    output["sma_200"] = close.rolling(200, min_periods=50).mean()

    output["rsi_14"] = calculate_rsi(close, 14)
    output["change_1d_pct"] = close.pct_change(1) * 100
    output["change_20d_pct"] = close.pct_change(20) * 100
    output["change_60d_pct"] = close.pct_change(60) * 100
    output["volatility_20d_pct"] = close.pct_change().rolling(20, min_periods=10).std() * 100

    if "Volume" in output.columns:
        output["avg_volume_20d"] = output["Volume"].rolling(20, min_periods=5).mean()
        output["volume_ratio"] = output["Volume"] / output["avg_volume_20d"].replace(0, pd.NA)
    else:
        output["volume_ratio"] = 1.0

    output["high_52w"] = close.rolling(252, min_periods=20).max()

    return output
