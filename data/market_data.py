from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
import hashlib
import json

import pandas as pd

CACHE_DIR = Path("storage/market_cache")
DEFAULT_CACHE_MINUTES = 20
MIN_HISTORY_ROWS = 60
DEFAULT_RETRY_WORKERS = 6
_MEMORY_CACHE_LOCK = threading.RLock()
_MEMORY_CACHE: dict[tuple[str, str, str], tuple[float, pd.DataFrame]] = {}


@dataclass(frozen=True)
class MarketDataResult:
    prices: dict[str, pd.DataFrame]
    errors: dict[str, str]
    fetched_at: datetime
    cache_hits: int = 0


def _clean_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    cleaned = frame.copy()
    cleaned.columns = [str(col).title() for col in cleaned.columns]
    expected = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    available = [col for col in expected if col in cleaned.columns]
    cleaned = cleaned[available]
    if "Close" in cleaned.columns:
        cleaned = cleaned.dropna(subset=["Close"])
    return cleaned


def _normalise_tickers(tickers: Iterable[str]) -> list[str]:
    # dict preserves order and removes duplicates.
    return list(dict.fromkeys(str(t).strip().upper() for t in tickers if str(t).strip()))


def _cache_key(ticker: str, period: str, interval: str) -> str:
    digest = hashlib.sha1(f"{ticker}|{period}|{interval}".encode("utf-8")).hexdigest()[:12]
    return f"{ticker.replace('^', 'INDEX_').replace('/', '_')}_{digest}"


def _cache_paths(ticker: str, period: str, interval: str) -> tuple[Path, Path]:
    key = _cache_key(ticker, period, interval)
    return CACHE_DIR / f"{key}.pkl", CACHE_DIR / f"{key}.json"


def _read_cache(ticker: str, period: str, interval: str, max_age_minutes: int) -> pd.DataFrame | None:
    memory_key = (ticker, period, interval)
    now = time.monotonic()
    with _MEMORY_CACHE_LOCK:
        memory_item = _MEMORY_CACHE.get(memory_key)
        if memory_item is not None:
            expires_at, memory_frame = memory_item
            if now < expires_at:
                return memory_frame.copy()
            _MEMORY_CACHE.pop(memory_key, None)

    frame_path, meta_path = _cache_paths(ticker, period, interval)
    if not frame_path.exists() or not meta_path.exists():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        fetched_at = datetime.fromisoformat(str(meta["fetched_at"]))
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - fetched_at > timedelta(minutes=max_age_minutes):
            return None
        frame = pd.read_pickle(frame_path)
        frame = _clean_frame(frame)
        if len(frame) < MIN_HISTORY_ROWS:
            return None
        with _MEMORY_CACHE_LOCK:
            _MEMORY_CACHE[memory_key] = (now + max_age_minutes * 60, frame.copy())
        return frame
    except Exception:
        return None


def _write_cache(ticker: str, period: str, interval: str, frame: pd.DataFrame, fetched_at: datetime) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        frame_path, meta_path = _cache_paths(ticker, period, interval)
        frame.to_pickle(frame_path)
        meta_path.write_text(json.dumps({"fetched_at": fetched_at.isoformat()}), encoding="utf-8")
        with _MEMORY_CACHE_LOCK:
            _MEMORY_CACHE[(ticker, period, interval)] = (
                time.monotonic() + DEFAULT_CACHE_MINUTES * 60,
                frame.copy(),
            )
    except Exception:
        # Caching is an optimisation only and must never stop a scan.
        pass


def _split_batch_frame(batch: pd.DataFrame, tickers: list[str]) -> dict[str, pd.DataFrame]:
    output: dict[str, pd.DataFrame] = {}
    if batch is None or batch.empty:
        return output

    if len(tickers) == 1 and not isinstance(batch.columns, pd.MultiIndex):
        output[tickers[0]] = batch
        return output

    if not isinstance(batch.columns, pd.MultiIndex):
        return output

    # yfinance commonly returns (Price, Ticker), but support the inverse too.
    level0 = set(map(str, batch.columns.get_level_values(0)))
    level1 = set(map(str, batch.columns.get_level_values(1)))
    for ticker in tickers:
        try:
            if ticker in level1:
                frame = batch.xs(ticker, axis=1, level=1, drop_level=True)
            elif ticker in level0:
                frame = batch.xs(ticker, axis=1, level=0, drop_level=True)
            else:
                continue
            output[ticker] = frame
        except (KeyError, ValueError):
            continue
    return output


def _download_batch(tickers: list[str], period: str, interval: str) -> dict[str, pd.DataFrame]:
    import yfinance as yf
    if not tickers:
        return {}
    batch = yf.download(
        tickers=tickers if len(tickers) > 1 else tickers[0],
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=True,
        group_by="column",
    )
    return _split_batch_frame(batch, tickers)


def _download_single(ticker: str, period: str, interval: str) -> pd.DataFrame:
    import yfinance as yf
    frame = yf.download(
        ticker,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    return frame


def download_history(
    tickers: Iterable[str],
    period: str = "1y",
    interval: str = "1d",
    *,
    batch_size: int = 80,
    cache_minutes: int = DEFAULT_CACHE_MINUTES,
    use_cache: bool = True,
    retry_workers: int = DEFAULT_RETRY_WORKERS,
) -> MarketDataResult:
    """Download history efficiently using batches, cache and single-symbol retries."""
    requested = _normalise_tickers(tickers)
    prices: dict[str, pd.DataFrame] = {}
    errors: dict[str, str] = {}
    fetched_at = datetime.now(timezone.utc)
    cache_hits = 0
    pending: list[str] = []

    for ticker in requested:
        cached = _read_cache(ticker, period, interval, cache_minutes) if use_cache else None
        if cached is not None:
            prices[ticker] = cached
            cache_hits += 1
        else:
            pending.append(ticker)

    batch_size = max(1, int(batch_size))
    for start in range(0, len(pending), batch_size):
        batch_tickers = pending[start : start + batch_size]
        try:
            frames = _download_batch(batch_tickers, period, interval)
        except Exception:
            frames = {}

        retry: list[str] = []
        for ticker in batch_tickers:
            frame = _clean_frame(frames.get(ticker, pd.DataFrame()))
            if len(frame) < MIN_HISTORY_ROWS:
                retry.append(ticker)
                continue
            prices[ticker] = frame
            _write_cache(ticker, period, interval, frame, fetched_at)

        if retry:
            workers = max(1, min(int(retry_workers), len(retry)))
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="market-retry") as pool:
                futures = {pool.submit(_download_single, ticker, period, interval): ticker for ticker in retry}
                for future in as_completed(futures):
                    ticker = futures[future]
                    try:
                        frame = _clean_frame(future.result())
                        if len(frame) < MIN_HISTORY_ROWS:
                            errors[ticker] = "Insufficient price history"
                            continue
                        prices[ticker] = frame
                        _write_cache(ticker, period, interval, frame, fetched_at)
                    except Exception as exc:
                        errors[ticker] = str(exc)

    return MarketDataResult(
        prices=prices,
        errors=errors,
        fetched_at=fetched_at,
        cache_hits=cache_hits,
    )
