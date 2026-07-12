from __future__ import annotations

import pandas as pd

from data.storage_service import dataframe_to_records, get, put, records_to_dataframe


PORTFOLIO_MONITOR_KEY = "portfolio_monitor"
MARKET_REGIME_KEY = "market_regime"


def save_portfolio_monitor(frame: pd.DataFrame) -> str:
    return put(PORTFOLIO_MONITOR_KEY, dataframe_to_records(frame))


def load_portfolio_monitor() -> pd.DataFrame:
    records = get(PORTFOLIO_MONITOR_KEY, [])
    return records_to_dataframe(records if isinstance(records, list) else [])


def save_market_regime(regime: dict | None) -> str:
    return put(MARKET_REGIME_KEY, regime or {})


def load_market_regime() -> dict:
    value = get(MARKET_REGIME_KEY, {})
    return value if isinstance(value, dict) else {}
