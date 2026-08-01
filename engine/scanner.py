from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import RLock
from typing import Any
import logging
import os

import pandas as pd

from engine.indicators import enrich_price_frame
from engine.market_regime import apply_market_regime
from engine.ranking import RANKING_COLUMNS, rank_candidates
from engine.scoring import assign_signal, explain_score, score_quality

LOGGER = logging.getLogger(__name__)

OUTPUT_COLUMNS = [
    "ticker", "signal", "score", "base_score", "market_regime", "market_score",
    "market_adjustment", "close", "change_1d_pct", "change_20d_pct",
    "change_60d_pct", "rsi_14", "volume_ratio", "volatility_20d_pct",
    "trend", "trend_score", "momentum_score", "volume_score",
    "relative_strength_score", "volatility_penalty", "extension_penalty",
    "priority_rank", "priority_score", "confidence_band",
    "relative_strength_percentile", "momentum_consistency", "risk_quality",
    "reason", "regime_reason", "sma_20", "sma_50", "sma_200", "high_52w",
]

# Synthetic benchmarks show pandas rolling calculations are faster serially
# at this universe size. Parallel mode remains available as an override.
DEFAULT_SCAN_WORKERS = 1
_INDICATOR_CACHE_MAX = 2500
_INDICATOR_CACHE_LOCK = RLock()
_INDICATOR_CACHE: dict[tuple[Any, ...], dict] = {}


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


def _scalar(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _frame_fingerprint(ticker: str, prices: pd.DataFrame) -> tuple[Any, ...]:
    if prices is None or prices.empty:
        return ticker, 0, None, None, None

    last_index = prices.index[-1] if len(prices.index) else None
    close_value: Any = None
    volume_value: Any = None

    if "Close" in prices.columns:
        close = prices["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        if len(close):
            close_value = _scalar(close.iloc[-1], default=float("nan"))

    if "Volume" in prices.columns:
        volume = prices["Volume"]
        if isinstance(volume, pd.DataFrame):
            volume = volume.iloc[:, 0]
        if len(volume):
            volume_value = _scalar(volume.iloc[-1], default=float("nan"))

    return ticker, len(prices), str(last_index), close_value, volume_value


def clear_indicator_cache() -> None:
    with _INDICATOR_CACHE_LOCK:
        _INDICATOR_CACHE.clear()


def _get_cached_row(key: tuple[Any, ...]) -> dict | None:
    with _INDICATOR_CACHE_LOCK:
        value = _INDICATOR_CACHE.get(key)
        return dict(value) if value is not None else None


def _put_cached_row(key: tuple[Any, ...], row: dict) -> None:
    with _INDICATOR_CACHE_LOCK:
        if len(_INDICATOR_CACHE) >= _INDICATOR_CACHE_MAX:
            trim = max(1, _INDICATOR_CACHE_MAX // 4)
            for old_key in list(_INDICATOR_CACHE)[:trim]:
                _INDICATOR_CACHE.pop(old_key, None)
        _INDICATOR_CACHE[key] = dict(row)


def score_enriched_row(
    ticker: str,
    latest: pd.Series,
    *,
    round_values: bool = True,
) -> dict:
    """Score one already-enriched price row using the live scanner rules.

    The historical backtester calls this same function, keeping live and
    historical BUY/WATCH/IGNORE decisions on one source of truth.
    """
    def value(name: str, default: float = 0.0, digits: int = 2) -> float:
        number = _scalar(latest.get(name, default), default)
        return round(number, digits) if round_values else number

    row = {
        "ticker": str(ticker).upper(),
        "close": value("Close"),
        "change_1d_pct": value("change_1d_pct"),
        "change_20d_pct": value("change_20d_pct"),
        "change_60d_pct": value("change_60d_pct"),
        "rsi_14": value("rsi_14", 50, 1),
        "volume_ratio": value("volume_ratio", 1),
        "volatility_20d_pct": value("volatility_20d_pct"),
        "sma_20": value("sma_20"),
        "sma_50": value("sma_50"),
        "sma_200": value("sma_200"),
        "high_52w": value("high_52w"),
    }
    row["trend"] = classify_trend(pd.Series(row))
    row.update(score_quality(pd.Series(row)))
    row["signal"] = assign_signal(pd.Series(row))
    row["reason"] = explain_score(pd.Series(row))
    return row


def _latest_indicator_row(ticker: str, prices: pd.DataFrame) -> dict | None:
    cache_key = _frame_fingerprint(ticker, prices)
    cached = _get_cached_row(cache_key)
    if cached is not None:
        return cached

    enriched = enrich_price_frame(prices)
    if enriched.empty:
        return None
    latest = enriched.iloc[-1]

    row = score_enriched_row(ticker, latest)
    _put_cached_row(cache_key, row)
    return row


def _score_one(item: tuple[str, pd.DataFrame]) -> tuple[str, dict | None, str | None]:
    ticker, prices = item
    ticker = str(ticker).upper()
    if ticker in {"SPY", "QQQ"}:
        return ticker, None, None
    try:
        return ticker, _latest_indicator_row(ticker, prices), None
    except Exception as exc:
        return ticker, None, str(exc)


def run_scan(
    price_map: dict[str, pd.DataFrame],
    market_regime: dict | None = None,
    *,
    workers: int = DEFAULT_SCAN_WORKERS,
) -> pd.DataFrame:
    """Score symbols concurrently while preserving deterministic results."""
    if not price_map:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    items = list(price_map.items())
    rows: list[dict] = []
    failures: list[tuple[str, str]] = []
    worker_count = max(1, min(int(workers), len(items)))

    if worker_count == 1:
        results = [_score_one(item) for item in items]
    else:
        results = []
        with ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix="catalyst-score",
        ) as pool:
            futures = [pool.submit(_score_one, item) for item in items]
            for future in as_completed(futures):
                results.append(future.result())

    for ticker, row, error in results:
        if row:
            rows.append(row)
        elif error:
            failures.append((ticker, error))

    if failures:
        LOGGER.warning(
            "Scanner skipped %s symbols; first failures: %s",
            len(failures),
            failures[:5],
        )

    if not rows:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    frame = pd.DataFrame(rows)
    if market_regime:
        frame = apply_market_regime(frame, market_regime)
    else:
        frame["base_score"] = frame["score"]
        frame["market_regime"] = "UNKNOWN"
        frame["market_score"] = 0
        frame["market_adjustment"] = 0
        frame["regime_reason"] = ""

    for column in OUTPUT_COLUMNS:
        if column not in frame.columns:
            frame[column] = None

    frame = rank_candidates(frame)

    for column in OUTPUT_COLUMNS:
        if column not in frame.columns:
            frame[column] = None

    return frame[OUTPUT_COLUMNS].reset_index(drop=True)
