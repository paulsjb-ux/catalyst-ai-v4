from __future__ import annotations
import math
import pandas as pd

def ticker_performance(trades: pd.DataFrame) -> pd.DataFrame:
    if trades is None or trades.empty:
        return pd.DataFrame(columns=["ticker","trades","win_rate_pct","average_return_pct","total_return_pct","profit_factor","portfolio_return_pct"])
    rows=[]
    for ticker, group in trades.groupby("ticker", sort=True):
        returns=pd.to_numeric(group["return_pct"], errors="coerce").fillna(0)
        portfolio=pd.to_numeric(group["portfolio_return_pct"] if "portfolio_return_pct" in group.columns else returns, errors="coerce").fillna(0)
        winners=returns[returns>0]; losers=returns[returns<=0]
        gp=float(winners.sum()); gl=abs(float(losers.sum()))
        pf=gp/gl if gl>0 else (float("inf") if gp>0 else 0.0)
        rows.append({
            "ticker":ticker,
            "trades":int(len(group)),
            "win_rate_pct":round(float((returns>0).mean()*100),2),
            "average_return_pct":round(float(returns.mean()),2),
            "total_return_pct":round(float(returns.sum()),2),
            "profit_factor":round(pf,2) if math.isfinite(pf) else "∞",
            "portfolio_return_pct":round(float(portfolio.sum()),2),
        })
    return pd.DataFrame(rows).sort_values(["portfolio_return_pct","average_return_pct"], ascending=[False,False]).reset_index(drop=True)
