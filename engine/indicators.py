from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    avg_loss = losses.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    values = 100 - (100 / (1 + rs))
    return values.fillna(50)


def volume_ratio(volume: pd.Series, window: int = 20) -> pd.Series:
    average = volume.rolling(window=window, min_periods=window).mean()
    return volume / average.replace(0, np.nan)


def enrich_prices(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = frame.copy()
    enriched["SMA20"] = sma(enriched["Close"], 20)
    enriched["SMA50"] = sma(enriched["Close"], 50)
    enriched["SMA200"] = sma(enriched["Close"], 200)
    enriched["RSI14"] = rsi(enriched["Close"], 14)
    enriched["VolumeRatio"] = volume_ratio(enriched["Volume"], 20)
    enriched["Change1D"] = enriched["Close"].pct_change() * 100
    enriched["Change20D"] = enriched["Close"].pct_change(20) * 100
    return enriched
