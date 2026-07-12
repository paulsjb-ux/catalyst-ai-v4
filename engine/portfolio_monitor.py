from __future__ import annotations

import math
import pandas as pd


def _safe_float(value, default: float = 0.0) -> float:
    try:
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return default
        return number
    except Exception:
        return default


def build_portfolio_monitor(
    watchlist: pd.DataFrame,
    price_map: dict[str, pd.DataFrame],
    latest_scan: pd.DataFrame | None = None,
    market_regime: dict | None = None,
) -> pd.DataFrame:
    """Attach live prices, P&L, target/stop distance, signals and alerts."""
    if watchlist is None or watchlist.empty:
        return pd.DataFrame()

    scan_lookup = {}
    if latest_scan is not None and not latest_scan.empty and "ticker" in latest_scan.columns:
        scan_lookup = {
            str(row["ticker"]).upper(): row
            for _, row in latest_scan.iterrows()
        }

    regime_label = (market_regime or {}).get("regime", "UNKNOWN")
    rows = []

    for _, item in watchlist.iterrows():
        ticker = str(item.get("ticker", "")).upper().strip()
        if not ticker:
            continue

        prices = price_map.get(ticker)
        current_price = None
        change_1d_pct = None

        if prices is not None and not prices.empty and "Close" in prices.columns:
            current_price = _safe_float(prices["Close"].iloc[-1], None)
            if len(prices) >= 2:
                previous = _safe_float(prices["Close"].iloc[-2], None)
                if current_price is not None and previous not in (None, 0):
                    change_1d_pct = ((current_price / previous) - 1) * 100

        quantity = _safe_float(item.get("quantity"))
        entry_price = _safe_float(item.get("entry_price"), None)
        target_price = _safe_float(item.get("target_price"), None)
        stop_loss = _safe_float(item.get("stop_loss"), None)

        invested = None
        market_value = None
        unrealised_pnl = None
        unrealised_pnl_pct = None

        if quantity > 0 and entry_price not in (None, 0):
            invested = quantity * entry_price

        if quantity > 0 and current_price is not None:
            market_value = quantity * current_price

        if invested not in (None, 0) and market_value is not None:
            unrealised_pnl = market_value - invested
            unrealised_pnl_pct = (unrealised_pnl / invested) * 100

        distance_to_target_pct = None
        distance_to_stop_pct = None

        if current_price not in (None, 0) and target_price not in (None, 0):
            distance_to_target_pct = ((target_price / current_price) - 1) * 100

        if current_price not in (None, 0) and stop_loss not in (None, 0):
            distance_to_stop_pct = ((current_price / stop_loss) - 1) * 100

        scan_row = scan_lookup.get(ticker)
        signal = str(scan_row.get("signal", "UNSCANNED")) if scan_row is not None else "UNSCANNED"
        score = _safe_float(scan_row.get("score"), None) if scan_row is not None else None

        alerts = []

        if current_price is None:
            alerts.append("PRICE UNAVAILABLE")
        if target_price not in (None, 0) and current_price is not None:
            if current_price >= target_price:
                alerts.append("TARGET REACHED")
            elif distance_to_target_pct is not None and distance_to_target_pct <= 3:
                alerts.append("NEAR TARGET")
        if stop_loss not in (None, 0) and current_price is not None:
            if current_price <= stop_loss:
                alerts.append("STOP BREACHED")
            elif distance_to_stop_pct is not None and distance_to_stop_pct <= 3:
                alerts.append("NEAR STOP")
        if signal == "IGNORE":
            alerts.append("SIGNAL LOST")
        elif signal == "WATCH":
            alerts.append("WATCH ONLY")
        if regime_label in {"RISK_OFF", "DEFENSIVE"}:
            alerts.append("WEAK MARKET")

        if "STOP BREACHED" in alerts or "SIGNAL LOST" in alerts:
            holding_status = "REVIEW"
        elif "NEAR STOP" in alerts or regime_label in {"RISK_OFF", "DEFENSIVE"}:
            holding_status = "CAUTION"
        elif "TARGET REACHED" in alerts:
            holding_status = "TAKE PROFIT"
        elif signal == "BUY":
            holding_status = "HOLD / STRONG"
        elif signal == "WATCH":
            holding_status = "HOLD / WATCH"
        else:
            holding_status = "MONITOR"

        rows.append({
            **item.to_dict(),
            "current_price": round(current_price, 2) if current_price is not None else None,
            "change_1d_pct": round(change_1d_pct, 2) if change_1d_pct is not None else None,
            "invested": round(invested, 2) if invested is not None else None,
            "market_value": round(market_value, 2) if market_value is not None else None,
            "unrealised_pnl": round(unrealised_pnl, 2) if unrealised_pnl is not None else None,
            "unrealised_pnl_pct": round(unrealised_pnl_pct, 2) if unrealised_pnl_pct is not None else None,
            "distance_to_target_pct": round(distance_to_target_pct, 2) if distance_to_target_pct is not None else None,
            "distance_to_stop_pct": round(distance_to_stop_pct, 2) if distance_to_stop_pct is not None else None,
            "latest_signal": signal,
            "latest_score": round(score, 1) if score is not None else None,
            "market_regime": regime_label,
            "holding_status": holding_status,
            "alerts": " · ".join(alerts) if alerts else "NONE",
        })

    return pd.DataFrame(rows)


def portfolio_summary(frame: pd.DataFrame) -> dict:
    if frame is None or frame.empty:
        return {
            "positions": 0,
            "invested": 0.0,
            "market_value": 0.0,
            "unrealised_pnl": 0.0,
            "unrealised_pnl_pct": 0.0,
            "alerts": 0,
        }

    invested = pd.to_numeric(frame.get("invested"), errors="coerce").fillna(0).sum()
    market_value = pd.to_numeric(frame.get("market_value"), errors="coerce").fillna(0).sum()
    pnl = market_value - invested
    pnl_pct = (pnl / invested) * 100 if invested else 0.0
    alerts = int((frame.get("alerts", pd.Series(dtype=str)) != "NONE").sum())

    return {
        "positions": len(frame),
        "invested": round(float(invested), 2),
        "market_value": round(float(market_value), 2),
        "unrealised_pnl": round(float(pnl), 2),
        "unrealised_pnl_pct": round(float(pnl_pct), 2),
        "alerts": alerts,
    }
