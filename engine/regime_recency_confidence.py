from __future__ import annotations

import math
from dataclasses import dataclass
import pandas as pd

V92_COLUMNS = [
    "confidence_regime", "recency_effective_trades", "recency_win_rate_pct",
    "recency_profit_factor", "recency_average_return_pct", "confidence_status",
    "confidence_change", "confidence_direction", "v92_position_cap_pct",
    "v92_position_size_pct", "v92_portfolio_return_pct", "confidence_reason",
]

@dataclass(frozen=True)
class RecencyDecision:
    status: str
    direction: str
    change: int
    effective_trades: float
    win_rate_pct: float
    profit_factor: float | str
    average_return_pct: float
    size_pct: float
    reason: str


def _clean_returns(frame: pd.DataFrame) -> pd.Series:
    if frame is None or frame.empty or "return_pct" not in frame:
        return pd.Series(dtype=float)
    return pd.to_numeric(frame["return_pct"], errors="coerce").dropna()


def exponentially_weighted_stats(history: pd.DataFrame, *, as_of=None, half_life_days: float = 45.0) -> dict:
    """Calculate time-decayed evidence. Recent closed trades carry more weight."""
    returns = _clean_returns(history)
    if returns.empty:
        return {"effective_trades": 0.0, "win_rate_pct": 0.0, "profit_factor": 0.0, "average_return_pct": 0.0}

    work = history.loc[returns.index].copy()
    work["return_pct"] = returns
    if "exit_date" in work:
        dates = pd.to_datetime(work["exit_date"], errors="coerce")
        reference = pd.Timestamp(as_of) if as_of is not None else dates.max()
        age = (reference - dates).dt.days.clip(lower=0).fillna(0)
        decay = math.log(2) / max(float(half_life_days), 1.0)
        weights = (-decay * age).map(math.exp)
    else:
        weights = pd.Series(1.0, index=work.index)

    weight_sum = float(weights.sum())
    if weight_sum <= 0:
        return {"effective_trades": 0.0, "win_rate_pct": 0.0, "profit_factor": 0.0, "average_return_pct": 0.0}

    values = work["return_pct"].astype(float)
    weighted_average = float((values * weights).sum() / weight_sum)
    win_rate = float((weights[values > 0].sum() / weight_sum) * 100)
    gross_profit = float((values.clip(lower=0) * weights).sum())
    gross_loss = abs(float((values.clip(upper=0) * weights).sum()))
    profit_factor = float("inf") if gross_loss == 0 and gross_profit > 0 else (gross_profit / gross_loss if gross_loss else 0.0)
    return {
        "effective_trades": round(weight_sum, 2),
        "win_rate_pct": round(win_rate, 2),
        "profit_factor": profit_factor,
        "average_return_pct": round(weighted_average, 3),
    }


def recency_decision(history: pd.DataFrame, *, previous_status: str = "UNPROVEN", as_of=None, half_life_days: float = 45.0, reduced_cap_pct: float = 15.0) -> RecencyDecision:
    stats = exponentially_weighted_stats(history, as_of=as_of, half_life_days=half_life_days)
    count = stats["effective_trades"]
    win = stats["win_rate_pct"]
    pf_raw = stats["profit_factor"]
    avg = stats["average_return_pct"]

    if count < 5:
        status, size, reason = "UNPROVEN", min(reduced_cap_pct, 7.5), "insufficient recent evidence"
    elif count < 12:
        status, size, reason = "BUILDING", min(reduced_cap_pct, 10.0), "recent evidence is still building"
    elif pf_raw >= 1.25 and win >= 50 and avg >= 0.15:
        status, size, reason = "PROVEN", reduced_cap_pct, "recent regime evidence supports reduced-size deployment"
    elif pf_raw >= 1.05 and avg > 0:
        status, size, reason = "MIXED", min(reduced_cap_pct, 10.0), "recent evidence is positive but not robust"
    else:
        status, size, reason = "WEAK", min(reduced_cap_pct, 5.0), "recent performance no longer supports confidence"

    order = {"WEAK": 0, "UNPROVEN": 1, "BUILDING": 2, "MIXED": 3, "PROVEN": 4}
    change = order.get(status, 0) - order.get(str(previous_status), 1)
    direction = "UPGRADE" if change > 0 else "DOWNGRADE" if change < 0 else "UNCHANGED"
    pf = round(pf_raw, 2) if math.isfinite(pf_raw) else "∞"
    return RecencyDecision(status, direction, change, count, win, pf, avg, round(size, 2), reason)


def apply_regime_recency_confidence(trades: pd.DataFrame, *, enabled: bool = True, half_life_days: float = 45.0, reduced_cap_pct: float = 15.0) -> pd.DataFrame:
    """Walk-forward v9.2 overlay grouped by score band and market regime."""
    if trades is None or trades.empty:
        output = trades.copy() if isinstance(trades, pd.DataFrame) else pd.DataFrame()
        for column in V92_COLUMNS:
            output[column] = pd.Series(dtype="object")
        return output

    output = trades.copy()
    output["entry_date"] = pd.to_datetime(output["entry_date"])
    output["exit_date"] = pd.to_datetime(output["exit_date"])
    if "market_regime" not in output:
        output["market_regime"] = "ALL"
    output["_v92_order"] = range(len(output))
    rows = []
    statuses: dict[tuple[str, str], str] = {}

    for _, trade in output.sort_values(["entry_date", "ticker", "_v92_order"]).iterrows():
        regime = str(trade.get("market_regime", "ALL") or "ALL")
        band = str(trade.get("score_band", "") or "")
        eligible = output[(output["exit_date"] < trade["entry_date"]) & (output["score_band"].astype(str) == band)]
        regime_history = eligible[eligible["market_regime"].astype(str) == regime]
        key = (band, regime)
        decision = recency_decision(
            regime_history,
            previous_status=statuses.get(key, "UNPROVEN"),
            as_of=trade["entry_date"],
            half_life_days=half_life_days,
            reduced_cap_pct=reduced_cap_pct,
        )
        statuses[key] = decision.status
        legacy_size = float(trade.get("calibrated_position_size_pct", trade.get("position_size_pct", reduced_cap_pct)) or 0)
        size = min(legacy_size, decision.size_pct, reduced_cap_pct) if enabled else legacy_size
        raw_return = float(trade.get("return_pct", 0.0) or 0.0)
        row = trade.to_dict()
        row.update({
            "confidence_regime": regime,
            "recency_effective_trades": decision.effective_trades,
            "recency_win_rate_pct": decision.win_rate_pct,
            "recency_profit_factor": decision.profit_factor,
            "recency_average_return_pct": decision.average_return_pct,
            "confidence_status": decision.status if enabled else "OFF",
            "confidence_change": decision.change if enabled else 0,
            "confidence_direction": decision.direction if enabled else "OFF",
            "v92_position_cap_pct": reduced_cap_pct,
            "v92_position_size_pct": round(size, 2),
            "v92_portfolio_return_pct": round(raw_return * size / 100, 4),
            "confidence_reason": decision.reason if enabled else "v9.2 confidence overlay disabled",
        })
        rows.append(row)
    return pd.DataFrame(rows).sort_values("_v92_order").drop(columns=["_v92_order"]).reset_index(drop=True)


def score_band_diagnostics(trades: pd.DataFrame) -> pd.DataFrame:
    if trades is None or trades.empty or "score_band" not in trades:
        return pd.DataFrame(columns=["score_band", "market_regime", "trades", "win_rate_pct", "average_return_pct", "profit_factor", "latest_confidence", "confidence_trend"])
    work = trades.copy()
    if "market_regime" not in work:
        work["market_regime"] = "ALL"
    rows = []
    for (band, regime), group in work.groupby(["score_band", "market_regime"], dropna=False):
        returns = _clean_returns(group)
        gross_profit = float(returns[returns > 0].sum())
        gross_loss = abs(float(returns[returns <= 0].sum()))
        pf = "∞" if gross_loss == 0 and gross_profit > 0 else round(gross_profit / gross_loss, 2) if gross_loss else 0.0
        latest = group.sort_values("entry_date").iloc[-1]
        rows.append({
            "score_band": band, "market_regime": regime, "trades": len(returns),
            "win_rate_pct": round(float((returns > 0).mean() * 100), 2) if len(returns) else 0.0,
            "average_return_pct": round(float(returns.mean()), 3) if len(returns) else 0.0,
            "profit_factor": pf,
            "latest_confidence": latest.get("confidence_status", "—"),
            "confidence_trend": latest.get("confidence_direction", "—"),
        })
    return pd.DataFrame(rows).sort_values(["score_band", "market_regime"]).reset_index(drop=True)
