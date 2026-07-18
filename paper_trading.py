from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from math import floor
from typing import Any

import pandas as pd


DEFAULT_CONFIG = {
    "starting_cash": 10000.0,
    "trial_days": 30,
    "max_open_trades": 5,
    "max_position_value": 2000.0,
    "risk_per_trade_pct": 1.0,
    "minimum_score": 75.0,
    "minimum_risk_reward": 2.0,
    "maximum_holding_days": 10,
    "entry_slippage_pct": 0.1,
    "exit_slippage_pct": 0.1,
}


@dataclass
class PaperTrade:
    trade_id: str
    ticker: str
    signal_date: str
    entry_date: str
    entry_price: float
    quantity: int
    position_value: float
    score: float
    market_regime: str
    target_price: float
    stop_price: float
    risk_reward: float
    status: str = "OPEN"
    days_held: int = 0
    last_price: float | None = None
    exit_date: str | None = None
    exit_price: float | None = None
    exit_reason: str | None = None
    gross_pnl: float | None = None
    net_pnl: float | None = None
    return_pct: float | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_state(config: dict[str, Any] | None = None) -> dict[str, Any]:
    merged = {**DEFAULT_CONFIG, **(config or {})}
    starting_cash = float(merged["starting_cash"])
    return {
        "active": True,
        "started_at": now_iso(),
        "completed_at": None,
        "config": merged,
        "cash": starting_cash,
        "open_trades": [],
        "closed_trades": [],
        "daily_runs": [],
        "equity_history": [{"date": date.today().isoformat(), "equity": starting_cash, "cash": starting_cash}],
        "benchmark": {"ticker": "SPY", "start_price": None, "latest_price": None},
    }


def _number(row: pd.Series, names: list[str], default: float | None = None) -> float | None:
    for name in names:
        if name in row.index:
            value = pd.to_numeric(pd.Series([row[name]]), errors="coerce").iloc[0]
            if pd.notna(value):
                return float(value)
    return default


def _text(row: pd.Series, names: list[str], default: str = "") -> str:
    for name in names:
        if name in row.index and pd.notna(row[name]):
            return str(row[name])
    return default


def qualifying_candidates(scan: pd.DataFrame, state: dict[str, Any], regime: str = "UNKNOWN") -> pd.DataFrame:
    if scan is None or scan.empty:
        return pd.DataFrame()

    cfg = state["config"]
    if regime.upper() in {"RISK_OFF", "DEFENSIVE"}:
        return pd.DataFrame()

    open_tickers = {trade["ticker"] for trade in state.get("open_trades", [])}
    rows: list[dict[str, Any]] = []
    for _, row in scan.iterrows():
        ticker = _text(row, ["ticker", "symbol"]).upper().strip()
        signal = _text(row, ["signal"]).upper()
        score = _number(row, ["score"], 0.0) or 0.0
        price = _number(row, ["close", "current_price", "price"])
        target = _number(row, ["target_price", "target", "take_profit"])
        stop = _number(row, ["stop_loss", "stop_price", "stop"])
        rr = _number(row, ["risk_reward", "risk_reward_ratio"])

        if not ticker or ticker in open_tickers or signal != "BUY" or price is None:
            continue
        if score < float(cfg["minimum_score"]):
            continue
        if target is None or stop is None or not (stop < price < target):
            continue
        calculated_rr = (target - price) / (price - stop) if price > stop else 0.0
        rr = calculated_rr if rr is None else rr
        if rr < float(cfg["minimum_risk_reward"]):
            continue

        rows.append({
            "ticker": ticker,
            "signal": signal,
            "score": score,
            "price": price,
            "target_price": target,
            "stop_price": stop,
            "risk_reward": rr,
            "market_regime": regime,
        })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["score", "risk_reward"], ascending=[False, False]).reset_index(drop=True)


def calculate_position(entry_price: float, stop_price: float, state: dict[str, Any]) -> tuple[int, float, float]:
    cfg = state["config"]
    available_cash = float(state["cash"])
    risk_budget = float(cfg["starting_cash"]) * float(cfg["risk_per_trade_pct"]) / 100.0
    risk_per_share = max(entry_price - stop_price, 0.0)
    if entry_price <= 0 or risk_per_share <= 0:
        return 0, 0.0, 0.0

    by_risk = floor(risk_budget / risk_per_share)
    by_value = floor(float(cfg["max_position_value"]) / entry_price)
    by_cash = floor(available_cash / entry_price)
    quantity = max(0, min(by_risk, by_value, by_cash))
    value = quantity * entry_price
    actual_risk = quantity * risk_per_share
    return quantity, value, actual_risk


def _price_map(scan: pd.DataFrame) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if scan is None or scan.empty:
        return result
    for _, row in scan.iterrows():
        ticker = _text(row, ["ticker", "symbol"]).upper().strip()
        if not ticker:
            continue
        result[ticker] = {
            "price": _number(row, ["close", "current_price", "price"]),
            "signal": _text(row, ["signal"], "UNKNOWN").upper(),
        }
    return result


def _close_trade(trade: dict[str, Any], raw_exit_price: float, reason: str, state: dict[str, Any], run_date: str) -> None:
    slip = float(state["config"]["exit_slippage_pct"]) / 100.0
    exit_price = raw_exit_price * (1.0 - slip)
    gross = (raw_exit_price - float(trade["entry_price"])) * int(trade["quantity"])
    net = (exit_price - float(trade["entry_price"])) * int(trade["quantity"])
    trade.update({
        "status": "CLOSED",
        "exit_date": run_date,
        "exit_price": round(exit_price, 6),
        "exit_reason": reason,
        "gross_pnl": round(gross, 2),
        "net_pnl": round(net, 2),
        "return_pct": round((exit_price / float(trade["entry_price"]) - 1.0) * 100.0, 3),
        "last_price": raw_exit_price,
    })
    state["cash"] = round(float(state["cash"]) + exit_price * int(trade["quantity"]), 2)
    state["closed_trades"].append(trade)


def process_day(state: dict[str, Any], scan: pd.DataFrame, regime: str = "UNKNOWN", run_date: str | None = None) -> dict[str, Any]:
    if not state.get("active", False):
        return state

    run_date = run_date or date.today().isoformat()
    if any(item.get("date") == run_date for item in state.get("daily_runs", [])):
        return state

    prices = _price_map(scan)
    still_open: list[dict[str, Any]] = []
    closed_today: list[str] = []

    for trade in state.get("open_trades", []):
        market = prices.get(trade["ticker"], {})
        price = market.get("price")
        signal = market.get("signal", "UNKNOWN")
        trade["days_held"] = int(trade.get("days_held", 0)) + 1
        if price is None:
            still_open.append(trade)
            continue
        trade["last_price"] = price

        reason = None
        exit_at = price
        if price <= float(trade["stop_price"]):
            reason, exit_at = "STOP HIT", float(trade["stop_price"])
        elif price >= float(trade["target_price"]):
            reason, exit_at = "TARGET HIT", float(trade["target_price"])
        elif signal not in {"BUY", "UNKNOWN", ""}:
            reason = "SIGNAL LOST"
        elif trade["days_held"] >= int(state["config"]["maximum_holding_days"]):
            reason = "MAX HOLD"

        if reason:
            _close_trade(trade, exit_at, reason, state, run_date)
            closed_today.append(trade["ticker"])
        else:
            still_open.append(trade)

    state["open_trades"] = still_open

    candidates = qualifying_candidates(scan, state, regime)
    opened_today: list[str] = []
    capacity = int(state["config"]["max_open_trades"]) - len(state["open_trades"])
    if capacity > 0 and not candidates.empty:
        for _, candidate in candidates.head(capacity).iterrows():
            slip = float(state["config"]["entry_slippage_pct"]) / 100.0
            entry = float(candidate["price"]) * (1.0 + slip)
            qty, value, _ = calculate_position(entry, float(candidate["stop_price"]), state)
            if qty <= 0:
                continue
            trade = PaperTrade(
                trade_id=f"{run_date}:{candidate['ticker']}",
                ticker=str(candidate["ticker"]),
                signal_date=run_date,
                entry_date=run_date,
                entry_price=round(entry, 6),
                quantity=qty,
                position_value=round(value, 2),
                score=float(candidate["score"]),
                market_regime=regime,
                target_price=float(candidate["target_price"]),
                stop_price=float(candidate["stop_price"]),
                risk_reward=float(candidate["risk_reward"]),
                last_price=float(candidate["price"]),
            )
            state["cash"] = round(float(state["cash"]) - value, 2)
            state["open_trades"].append(asdict(trade))
            opened_today.append(trade.ticker)

    equity = portfolio_equity(state)
    state["daily_runs"].append({
        "date": run_date,
        "regime": regime,
        "opened": opened_today,
        "closed": closed_today,
        "open_count": len(state["open_trades"]),
        "equity": round(equity, 2),
    })
    state["equity_history"].append({"date": run_date, "equity": round(equity, 2), "cash": round(float(state["cash"]), 2)})

    if len(state["daily_runs"]) >= int(state["config"]["trial_days"]):
        state["active"] = False
        state["completed_at"] = now_iso()
    return state


def portfolio_equity(state: dict[str, Any]) -> float:
    open_value = 0.0
    for trade in state.get("open_trades", []):
        price = trade.get("last_price") or trade.get("entry_price") or 0.0
        open_value += float(price) * int(trade.get("quantity", 0))
    return float(state.get("cash", 0.0)) + open_value


def performance_metrics(state: dict[str, Any]) -> dict[str, float | int]:
    closed = state.get("closed_trades", [])
    equity = portfolio_equity(state)
    start = float(state["config"]["starting_cash"])
    pnls = [float(item.get("net_pnl", 0.0) or 0.0) for item in closed]
    winners = [p for p in pnls if p > 0]
    losers = [p for p in pnls if p < 0]
    gross_profit = sum(winners)
    gross_loss = abs(sum(losers))

    history = [float(item.get("equity", start)) for item in state.get("equity_history", [])]
    peak = start
    max_drawdown = 0.0
    for value in history:
        peak = max(peak, value)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - value) / peak * 100.0)

    return {
        "days_run": len(state.get("daily_runs", [])),
        "days_remaining": max(0, int(state["config"]["trial_days"]) - len(state.get("daily_runs", []))),
        "open_trades": len(state.get("open_trades", [])),
        "closed_trades": len(closed),
        "wins": len(winners),
        "losses": len(losers),
        "win_rate_pct": round(len(winners) / len(closed) * 100.0, 2) if closed else 0.0,
        "net_pnl": round(equity - start, 2),
        "return_pct": round((equity / start - 1.0) * 100.0, 2) if start else 0.0,
        "average_win": round(sum(winners) / len(winners), 2) if winners else 0.0,
        "average_loss": round(sum(losers) / len(losers), 2) if losers else 0.0,
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss else (999.0 if gross_profit else 0.0),
        "max_drawdown_pct": round(max_drawdown, 2),
        "cash": round(float(state.get("cash", 0.0)), 2),
        "equity": round(equity, 2),
    }


def trades_frame(state: dict[str, Any], status: str) -> pd.DataFrame:
    records = state.get("open_trades" if status.upper() == "OPEN" else "closed_trades", [])
    return pd.DataFrame(records)
