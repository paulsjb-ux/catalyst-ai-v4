import pandas as pd
from engine.indicators import enrich_prices
from engine.models import ScanResult
from engine.scoring import score_latest

def scan_ticker(ticker: str, prices: pd.DataFrame) -> ScanResult:
    latest = enrich_prices(prices).iloc[-1]
    score, signal, trend, reason = score_latest(latest)
    return ScanResult(
        ticker=ticker, signal=signal, score=score, close=round(float(latest["Close"]),2),
        change_1d_pct=round(float(latest.get("Change1D",0) or 0),2),
        change_20d_pct=round(float(latest.get("Change20D",0) or 0),2),
        rsi_14=round(float(latest.get("RSI14",50) or 50),1),
        sma_20=round(float(latest.get("SMA20",0) or 0),2),
        sma_50=round(float(latest.get("SMA50",0) or 0),2),
        sma_200=round(float(latest.get("SMA200",0) or 0),2),
        volume_ratio=round(float(latest.get("VolumeRatio",0) or 0),2),
        trend=trend, reason=reason,
    )
def run_scan(price_map: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for ticker, frame in price_map.items():
        try:
            rows.append(scan_ticker(ticker, frame).to_dict())
        except Exception:
            continue
    if not rows:
        return pd.DataFrame()
    result = pd.DataFrame(rows)
    result["_signal_order"] = result["signal"].map({"BUY":0,"WATCH":1,"IGNORE":2}).fillna(9)
    return result.sort_values(["_signal_order","score","change_20d_pct"], ascending=[True,False,False]).drop(columns=["_signal_order"]).reset_index(drop=True)
