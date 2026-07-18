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
    values = raw.replace("\n", ",").split(",") if isinstance(raw, str) else raw
    cleaned = []
    for value in values:
        ticker = str(value).strip().upper()
        if ticker and ticker not in cleaned:
            cleaned.append(ticker)
    return cleaned
def get_default_universe(limit: int | None = None) -> list[str]:
    return DEFAULT_UNIVERSE.copy() if limit is None else DEFAULT_UNIVERSE[:max(0, int(limit))]
