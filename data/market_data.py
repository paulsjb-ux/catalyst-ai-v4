from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
import pandas as pd
import yfinance as yf

@dataclass(frozen=True)
class MarketDataResult:
    prices: dict[str, pd.DataFrame]
    errors: dict[str, str]
    fetched_at: datetime

def _clean_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    cleaned = frame.copy()
    cleaned.columns = [str(col).title() for col in cleaned.columns]
    expected = ["Open","High","Low","Close","Adj Close","Volume"]
    available = [col for col in expected if col in cleaned.columns]
    cleaned = cleaned[available]
    if "Close" in cleaned.columns:
        cleaned = cleaned.dropna(subset=["Close"])
    return cleaned

def download_history(tickers: Iterable[str], period: str = "1y", interval: str = "1d") -> MarketDataResult:
    prices, errors = {}, {}
    for ticker in [str(t).strip().upper() for t in tickers if str(t).strip()]:
        try:
            frame = yf.download(ticker, period=period, interval=interval, auto_adjust=False, progress=False, threads=False)
            if isinstance(frame.columns, pd.MultiIndex):
                frame.columns = frame.columns.get_level_values(0)
            frame = _clean_frame(frame)
            if frame.empty or len(frame) < 60:
                errors[ticker] = "Insufficient price history"
                continue
            prices[ticker] = frame
        except Exception as exc:
            errors[ticker] = str(exc)
    return MarketDataResult(prices=prices, errors=errors, fetched_at=datetime.now(timezone.utc))
