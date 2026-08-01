from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Iterable
import logging

import pandas as pd
import requests

LOGGER = logging.getLogger(__name__)

UNIVERSE_DIR = Path("data") / "universes"
GLOBAL_LIQUID_PATH = UNIVERSE_DIR / "global_liquid_universe.csv"
PJB_WATCHLIST_PATH = UNIVERSE_DIR / "pjb_watchlist.csv"
STARTER_LARGE_UNIVERSE_PATH = UNIVERSE_DIR / "starter_large_universe.csv"
SP500_FALLBACK_PATH = UNIVERSE_DIR / "sp500.csv"
NASDAQ100_FALLBACK_PATH = UNIVERSE_DIR / "nasdaq100.csv"
BROAD_US_PATH = UNIVERSE_DIR / "broad_us_equities.csv"

HTTP_TIMEOUT_SECONDS = 12
USER_AGENT = "CatalystAI/9.0.1"


def clean_ticker(ticker: str) -> str:
    text = str(ticker or "").upper().strip().replace(" ", "")
    if text in {"BRK.B", "BF.B"}:
        text = text.replace(".", "-")
    return text


def clean_ticker_list(tickers: Iterable[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for ticker in tickers:
        value = clean_ticker(ticker)
        if (
            not value
            or value in {"NAN", "NONE", "NULL"}
            or len(value) > 18
            or value in seen
        ):
            continue
        seen.add(value)
        cleaned.append(value)
    return cleaned


def load_universe_csv(path: str | Path) -> list[str]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    try:
        frame = pd.read_csv(file_path)
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
        LOGGER.warning("Universe file could not be read: %s (%s)", file_path, exc)
        return []
    if frame.empty:
        return []
    lowered = [str(column).lower().strip() for column in frame.columns]
    if "ticker" in lowered:
        column = frame.columns[lowered.index("ticker")]
    elif "symbol" in lowered:
        column = frame.columns[lowered.index("symbol")]
    else:
        column = frame.columns[0]
    return clean_ticker_list(frame[column].dropna().tolist())


def _read_html_tables(url: str) -> list[pd.DataFrame]:
    response = requests.get(
        url,
        timeout=HTTP_TIMEOUT_SECONDS,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    return pd.read_html(StringIO(response.text))


def fetch_sp500_tickers() -> list[str]:
    try:
        table = _read_html_tables(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        )[0]
        column = "Symbol" if "Symbol" in table.columns else table.columns[0]
        tickers = clean_ticker_list(table[column].tolist())
        if len(tickers) >= 450:
            return tickers
        LOGGER.warning("Live S&P 500 source returned only %s symbols.", len(tickers))
    except Exception as exc:
        LOGGER.warning("Live S&P 500 source unavailable; using local fallback: %s", exc)
    return load_universe_csv(SP500_FALLBACK_PATH)


def fetch_nasdaq100_tickers() -> list[str]:
    try:
        candidates: list[str] = []
        for table in _read_html_tables("https://en.wikipedia.org/wiki/Nasdaq-100"):
            for column in table.columns:
                name = str(column).lower()
                if "ticker" in name or "symbol" in name:
                    candidates.extend(table[column].dropna().tolist())
        tickers = clean_ticker_list(candidates)
        if len(tickers) >= 90:
            return tickers
        LOGGER.warning("Live Nasdaq-100 source returned only %s symbols.", len(tickers))
    except Exception as exc:
        LOGGER.warning("Live Nasdaq-100 source unavailable; using local fallback: %s", exc)
    return load_universe_csv(NASDAQ100_FALLBACK_PATH)


def build_scan_universe(
    include_sp500: bool = True,
    include_nasdaq100: bool = True,
    include_watchlist: bool = True,
    include_starter_large_universe: bool = True,
    include_global_liquid: bool = True,
    include_broad_us: bool = True,
    custom_tickers: Iterable[str] | None = None,
    excluded_tickers: Iterable[str] | None = None,
    max_tickers: int | None = 650,
) -> list[str]:
    tickers: list[str] = []

    if include_watchlist:
        tickers.extend(load_universe_csv(PJB_WATCHLIST_PATH))
    if include_global_liquid:
        tickers.extend(load_universe_csv(GLOBAL_LIQUID_PATH))
    if custom_tickers:
        tickers.extend(custom_tickers)
    if include_sp500:
        tickers.extend(fetch_sp500_tickers())
    if include_broad_us:
        tickers.extend(load_universe_csv(BROAD_US_PATH))
    if include_nasdaq100:
        tickers.extend(fetch_nasdaq100_tickers())
    if include_starter_large_universe:
        tickers.extend(load_universe_csv(STARTER_LARGE_UNIVERSE_PATH))

    cleaned = clean_ticker_list(tickers)
    excluded = {clean_ticker(t) for t in (excluded_tickers or [])}
    if excluded:
        cleaned = [t for t in cleaned if t not in excluded]
    requested = int(max_tickers) if max_tickers and max_tickers > 0 else None
    selected = cleaned[:requested] if requested else cleaned

    if requested and len(selected) < requested:
        LOGGER.warning(
            "Requested %s symbols but only %s unique symbols are available.",
            requested,
            len(selected),
        )
    return selected


def universe_source_summary(**kwargs) -> dict:
    total = build_scan_universe(**kwargs)
    return {
        "global_liquid": len(load_universe_csv(GLOBAL_LIQUID_PATH)),
        "sp500": len(fetch_sp500_tickers()) if kwargs.get("include_sp500", True) else 0,
        "nasdaq100": len(fetch_nasdaq100_tickers()) if kwargs.get("include_nasdaq100", True) else 0,
        "broad_us": len(load_universe_csv(BROAD_US_PATH)) if kwargs.get("include_broad_us", True) else 0,
        "total_unique": len(total),
        "max_tickers": kwargs.get("max_tickers", 650),
        "coverage": (
            "US, UK, Europe, Japan, Asia-Pacific, Canada, India, "
            "Latin America, ETFs, rates and commodities"
        ),
    }


def universe_health(tickers: Iterable[str]) -> dict:
    raw = list(tickers or [])
    cleaned = clean_ticker_list(raw)
    return {
        "raw_count": len(raw),
        "clean_count": len(cleaned),
        "duplicates_removed": len(raw) - len(set(raw)),
        "empty": not cleaned,
        "sample": cleaned[:10],
    }
