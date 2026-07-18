from __future__ import annotations

import pandas as pd

from engine.risk import atr, build_trade_plan


def build_trade_plans(
    scan_frame: pd.DataFrame,
    price_map: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Add target/stop planning to a scan result frame."""
    if scan_frame is None or scan_frame.empty:
        return pd.DataFrame()

    rows: list[dict] = []

    for _, row in scan_frame.iterrows():
        ticker = str(row.get("ticker", "")).upper().strip()
        if not ticker:
            continue

        output = row.to_dict()
        prices = price_map.get(ticker)

        atr_value = None
        if prices is not None and not prices.empty and {"High", "Low", "Close"}.issubset(prices.columns):
            atr_series = atr(prices, 14).dropna()
            if not atr_series.empty:
                atr_value = float(atr_series.iloc[-1])

        plan = build_trade_plan(
            ticker=ticker,
            signal=str(row.get("signal", "")),
            score=float(row.get("score", 0) or 0),
            close=float(row.get("close", 0) or 0),
            atr_value=float(atr_value or 0),
            sma_20=float(row.get("sma_20", 0) or 0),
            sma_50=float(row.get("sma_50", 0) or 0),
        )

        output.update(plan)
        rows.append(output)

    return pd.DataFrame(rows)


def filter_trade_plan_candidates(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep rows suitable for trade planning."""
    if frame is None or frame.empty or "signal" not in frame.columns:
        return pd.DataFrame()
    return frame[frame["signal"].isin(["BUY", "WATCH"])].copy()
