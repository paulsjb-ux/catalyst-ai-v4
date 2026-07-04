from __future__ import annotations

DEFAULT_UNIVERSE: list[str] = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","AMD","AVGO","NFLX",
    "CRM","ORCL","ADBE","INTC","QCOM","MU","ARM","PLTR","CRWD","PANW",
    "SHOP","UBER","ABNB","COIN","HOOD","PYPL","SQ","SNOW","NET","DDOG",
    "JPM","BAC","GS","MS","V","MA","AXP","C","WFC","SCHW",
    "LLY","UNH","JNJ","ABBV","MRK","PFE","TMO","ISRG","VRTX","REGN",
    "WMT","COST","HD","LOW","NKE","SBUX","MCD","DIS","BKNG","MAR",
    "XOM","CVX","COP","SLB","CAT","DE","GE","BA","RTX","LMT",
    "SPY","QQQ","IWM","DIA","XLK","XLF","XLE","XLV","SMH","ARKK",
]

def normalise_tickers(raw: str | list[str]) -> list[str]:
    if isinstance(raw, str):
        values = raw.replace("\n", ",").split(",")
    else:
        values = raw
    cleaned = []
    for value in values:
        ticker = str(value).strip().upper()
        if ticker and ticker not in cleaned:
            cleaned.append(ticker)
    return cleaned

def get_default_universe(limit: int | None = None) -> list[str]:
    if limit is None:
        return DEFAULT_UNIVERSE.copy()
    return DEFAULT_UNIVERSE[: max(0, int(limit))]
