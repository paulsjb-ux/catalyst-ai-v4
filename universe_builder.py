from __future__ import annotations

from pathlib import Path
from typing import Iterable
import pandas as pd

UNIVERSE_DIR = Path("data") / "universes"
GLOBAL_LIQUID_PATH = UNIVERSE_DIR / "global_liquid_universe.csv"
PJB_WATCHLIST_PATH = UNIVERSE_DIR / "pjb_watchlist.csv"
STARTER_LARGE_UNIVERSE_PATH = UNIVERSE_DIR / "starter_large_universe.csv"


def clean_ticker(ticker: str) -> str:
    text = str(ticker or "").upper().strip().replace(" ", "")
    # Keep exchange suffixes such as .L, .DE, .PA, .TO and .T.
    # Only convert the US share-class notation used by Yahoo Finance.
    if text in {"BRK.B", "BF.B"}:
        text = text.replace(".", "-")
    return text


def clean_ticker_list(tickers: Iterable[str]) -> list[str]:
    cleaned=[]
    for ticker in tickers:
        value=clean_ticker(ticker)
        if not value or value in {"NAN","NONE","NULL"} or len(value)>18:
            continue
        cleaned.append(value)
    return sorted(set(cleaned))


def load_universe_csv(path: str | Path) -> list[str]:
    file_path=Path(path)
    if not file_path.exists():
        return []
    frame=pd.read_csv(file_path)
    if frame.empty:
        return []
    lowered=[str(c).lower().strip() for c in frame.columns]
    if "ticker" in lowered:
        col=frame.columns[lowered.index("ticker")]
    elif "symbol" in lowered:
        col=frame.columns[lowered.index("symbol")]
    else:
        col=frame.columns[0]
    return clean_ticker_list(frame[col].dropna().tolist())


def fetch_sp500_tickers() -> list[str]:
    try:
        tables=pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        table=tables[0]
        col="Symbol" if "Symbol" in table.columns else table.columns[0]
        return clean_ticker_list(table[col].tolist())
    except Exception:
        return []


def fetch_nasdaq100_tickers() -> list[str]:
    try:
        candidates=[]
        for table in pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100"):
            for col in table.columns:
                name=str(col).lower()
                if "ticker" in name or "symbol" in name:
                    candidates.extend(table[col].dropna().tolist())
        return clean_ticker_list(candidates)
    except Exception:
        return []


def build_scan_universe(
    include_sp500: bool=True,
    include_nasdaq100: bool=True,
    include_watchlist: bool=True,
    include_starter_large_universe: bool=True,
    include_global_liquid: bool=True,
    custom_tickers: Iterable[str] | None=None,
    max_tickers: int | None=650,
) -> list[str]:
    tickers=[]
    if include_sp500:
        tickers.extend(fetch_sp500_tickers() or load_universe_csv(UNIVERSE_DIR / "sp500.csv"))
    if include_nasdaq100:
        tickers.extend(fetch_nasdaq100_tickers() or load_universe_csv(UNIVERSE_DIR / "nasdaq100.csv"))
    if include_global_liquid:
        tickers.extend(load_universe_csv(GLOBAL_LIQUID_PATH))
    if include_watchlist:
        tickers.extend(load_universe_csv(PJB_WATCHLIST_PATH))
    if include_starter_large_universe:
        tickers.extend(load_universe_csv(STARTER_LARGE_UNIVERSE_PATH))
    if custom_tickers:
        tickers.extend(custom_tickers)
    cleaned=clean_ticker_list(tickers)
    return cleaned[:int(max_tickers)] if max_tickers and max_tickers>0 else cleaned


def universe_source_summary(**kwargs) -> dict:
    global_liquid=load_universe_csv(GLOBAL_LIQUID_PATH) if kwargs.get("include_global_liquid", True) else []
    total=build_scan_universe(**kwargs)
    return {
        "global_liquid": len(global_liquid),
        "total_unique": len(total),
        "max_tickers": kwargs.get("max_tickers", 650),
        "coverage": "US, UK, Europe, Japan, Asia-Pacific, Canada, India, Latin America, ETFs, rates and commodities",
    }


def universe_health(tickers: Iterable[str]) -> dict:
    raw=list(tickers or [])
    cleaned=clean_ticker_list(raw)
    return {"raw_count":len(raw),"clean_count":len(cleaned),"duplicates_removed":len(raw)-len(set(raw)),"empty":not cleaned,"sample":cleaned[:10]}
