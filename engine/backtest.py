from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable
import math

import pandas as pd

from engine.indicators import enrich_price_frame
from engine.risk import atr
from engine.adaptive_risk import adaptive_risk_plan
from engine.confidence_calibration import apply_walk_forward_calibration
from engine.scoring import assign_signal, score_quality


TRADE_COLUMNS = [
    "ticker",
    "signal_date",
    "entry_date",
    "exit_date",
    "signal",
    "score",
    "entry_price",
    "exit_price",
    "return_pct",
    "holding_days",
    "exit_reason",
    "target_price",
    "stop_price",
    "target_atr_multiple",
    "stop_atr_multiple",
    "position_size_pct",
    "portfolio_return_pct",
    "risk_label",
    "risk_rationale",
    "score_band",
    "evidence_label",
    "evidence_multiplier",
    "evidence_trades",
    "evidence_win_rate_pct",
    "evidence_profit_factor",
    "evidence_average_return_pct",
    "calibrated_position_size_pct",
    "calibrated_portfolio_return_pct",
    "evidence_rationale",
]


@dataclass
class BacktestResult:
    trades: pd.DataFrame = field(
        default_factory=lambda: pd.DataFrame(columns=TRADE_COLUMNS)
    )
    equity_curve: pd.DataFrame = field(
        default_factory=lambda: pd.DataFrame(columns=["trade_number", "equity"])
    )
    metrics: dict = field(default_factory=dict)
    assumptions: dict = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)


def _safe_float(value, default: float = 0.0) -> float:
    try:
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return default
        return number
    except (TypeError, ValueError):
        return default


def _indicator_row(row: pd.Series) -> pd.Series:
    values = {
        "close": _safe_float(row.get("Close")),
        "change_1d_pct": _safe_float(row.get("change_1d_pct")),
        "change_20d_pct": _safe_float(row.get("change_20d_pct")),
        "change_60d_pct": _safe_float(row.get("change_60d_pct")),
        "rsi_14": _safe_float(row.get("rsi_14"), 50),
        "volume_ratio": _safe_float(row.get("volume_ratio"), 1),
        "volatility_20d_pct": _safe_float(row.get("volatility_20d_pct")),
        "sma_20": _safe_float(row.get("sma_20")),
        "sma_50": _safe_float(row.get("sma_50")),
        "sma_200": _safe_float(row.get("sma_200")),
        "high_52w": _safe_float(row.get("high_52w")),
    }
    components = score_quality(pd.Series(values))
    values.update(components)
    values["signal"] = assign_signal(pd.Series(values))
    return pd.Series(values)


def _normalise_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    output = frame.copy()
    if isinstance(output.columns, pd.MultiIndex):
        output.columns = output.columns.get_level_values(0)
    output = output.loc[:, ~output.columns.duplicated(keep="first")]
    required = {"Close"}
    if not required.issubset(output.columns):
        return pd.DataFrame()
    for column in ["Open", "High", "Low", "Close", "Volume"]:
        if column in output.columns:
            output[column] = pd.to_numeric(output[column], errors="coerce")
    output = output.dropna(subset=["Close"]).sort_index()
    return output


def _exit_from_path(
    future: pd.DataFrame,
    entry_price: float,
    target_price: float | None,
    stop_price: float | None,
) -> tuple[pd.Timestamp, float, str]:
    """Return first target/stop hit, using stop-first on ambiguous daily bars."""
    for date, row in future.iterrows():
        low = _safe_float(row.get("Low"), _safe_float(row.get("Close")))
        high = _safe_float(row.get("High"), _safe_float(row.get("Close")))

        # Daily bars cannot reveal intraday order. Stop-first is deliberately
        # conservative when both levels are crossed on the same day.
        if stop_price is not None and low <= stop_price:
            return date, stop_price, "STOP"
        if target_price is not None and high >= target_price:
            return date, target_price, "TARGET"

    date = future.index[-1]
    return date, _safe_float(future.iloc[-1].get("Close")), "TIME"


def backtest_ticker(
    ticker: str,
    frame: pd.DataFrame,
    *,
    holding_days: int = 20,
    minimum_score: int = 78,
    signals: Iterable[str] = ("BUY",),
    use_target_stop: bool = True,
    target_atr_multiple: float = 2.0,
    stop_atr_multiple: float = 1.3,
    transaction_cost_pct: float = 0.1,
    warmup_rows: int = 200,
    adaptive_risk: bool = True,
    base_position_pct: float = 20.0,
) -> pd.DataFrame:
    """Backtest one ticker with next-bar entry and no overlapping positions."""
    prices = _normalise_frame(frame)
    if prices.empty or len(prices) <= warmup_rows + holding_days + 1:
        return pd.DataFrame(columns=TRADE_COLUMNS)

    enriched = enrich_price_frame(prices)
    atr_series = atr(prices, 14)
    allowed_signals = {str(value).upper() for value in signals}

    rows: list[dict] = []
    index = enriched.index
    position_until = -1

    for signal_position in range(warmup_rows, len(enriched) - 1):
        if signal_position <= position_until:
            continue

        signal_row = _indicator_row(enriched.iloc[signal_position])
        signal = str(signal_row.get("signal", "IGNORE"))
        score = int(_safe_float(signal_row.get("score")))

        if signal not in allowed_signals or score < int(minimum_score):
            continue

        entry_position = signal_position + 1
        entry_row = prices.iloc[entry_position]
        entry_price = _safe_float(
            entry_row.get("Open"),
            _safe_float(entry_row.get("Close")),
        )
        if entry_price <= 0:
            continue

        final_position = min(
            entry_position + max(1, int(holding_days)) - 1,
            len(prices) - 1,
        )
        future = prices.iloc[entry_position : final_position + 1]
        if future.empty:
            continue

        target_price = None
        stop_price = None
        target_multiple = float(target_atr_multiple)
        stop_multiple = float(stop_atr_multiple)
        position_size_pct = float(base_position_pct)
        risk_label = "FIXED"
        risk_rationale = "fixed risk settings"

        if adaptive_risk:
            plan = adaptive_risk_plan(
                score=score,
                volatility_20d_pct=_safe_float(signal_row.get("volatility_20d_pct")),
                change_20d_pct=_safe_float(signal_row.get("change_20d_pct")),
                change_60d_pct=_safe_float(signal_row.get("change_60d_pct")),
                rsi_14=_safe_float(signal_row.get("rsi_14"), 50),
                signal=signal,
                base_target_atr=target_atr_multiple,
                base_stop_atr=stop_atr_multiple,
                base_position_pct=base_position_pct,
            )
            target_multiple = plan.target_atr_multiple
            stop_multiple = plan.stop_atr_multiple
            position_size_pct = plan.position_size_pct
            risk_label = plan.risk_label
            risk_rationale = plan.rationale

        if use_target_stop:
            atr_value = _safe_float(atr_series.iloc[signal_position])
            if atr_value > 0:
                target_price = entry_price + atr_value * target_multiple
                stop_price = entry_price - atr_value * stop_multiple

        exit_date, exit_price, exit_reason = _exit_from_path(
            future,
            entry_price,
            target_price,
            stop_price,
        )
        exit_position = prices.index.get_loc(exit_date)
        gross_return = (exit_price / entry_price - 1) * 100
        net_return = gross_return - max(0.0, float(transaction_cost_pct))
        portfolio_return = net_return * position_size_pct / 100

        rows.append(
            {
                "ticker": str(ticker).upper(),
                "signal_date": index[signal_position],
                "entry_date": index[entry_position],
                "exit_date": exit_date,
                "signal": signal,
                "score": score,
                "entry_price": round(entry_price, 4),
                "exit_price": round(exit_price, 4),
                "return_pct": round(net_return, 4),
                "holding_days": int(exit_position - entry_position + 1),
                "exit_reason": exit_reason,
                "target_price": (
                    round(target_price, 4) if target_price is not None else None
                ),
                "stop_price": (
                    round(stop_price, 4) if stop_price is not None else None
                ),
                "target_atr_multiple": round(target_multiple, 2),
                "stop_atr_multiple": round(stop_multiple, 2),
                "position_size_pct": round(position_size_pct, 2),
                "portfolio_return_pct": round(portfolio_return, 4),
                "risk_label": risk_label,
                "risk_rationale": risk_rationale,
            }
        )
        position_until = exit_position

    return pd.DataFrame(rows, columns=TRADE_COLUMNS)


def _max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    running_high = equity.cummax()
    drawdown = equity / running_high - 1
    return float(drawdown.min() * 100)


def calculate_metrics(trades: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    if trades is None or trades.empty:
        metrics = {
            "trades": 0,
            "win_rate_pct": 0.0,
            "average_return_pct": 0.0,
            "median_return_pct": 0.0,
            "compounded_return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "profit_factor": 0.0,
            "expectancy_pct": 0.0,
            "average_holding_days": 0.0,
            "portfolio_compounded_return_pct": 0.0,
            "portfolio_max_drawdown_pct": 0.0,
            "average_position_size_pct": 0.0,
            "calibrated_compounded_return_pct": 0.0,
            "calibrated_max_drawdown_pct": 0.0,
            "average_calibrated_position_size_pct": 0.0,
        }
        return metrics, pd.DataFrame(columns=["trade_number", "equity"])

    ordered = trades.sort_values(["exit_date", "ticker"]).reset_index(drop=True)
    returns = pd.to_numeric(ordered["return_pct"], errors="coerce").fillna(0)
    portfolio_returns = pd.to_numeric(
        ordered["portfolio_return_pct"]
        if "portfolio_return_pct" in ordered.columns
        else ordered["return_pct"],
        errors="coerce",
    ).fillna(0)
    position_sizes = pd.to_numeric(
        ordered["position_size_pct"]
        if "position_size_pct" in ordered.columns
        else pd.Series(100.0, index=ordered.index),
        errors="coerce",
    ).fillna(100.0)
    calibrated_returns = pd.to_numeric(
        ordered["calibrated_portfolio_return_pct"]
        if "calibrated_portfolio_return_pct" in ordered.columns
        else portfolio_returns,
        errors="coerce",
    ).fillna(0)
    calibrated_sizes = pd.to_numeric(
        ordered["calibrated_position_size_pct"]
        if "calibrated_position_size_pct" in ordered.columns
        else position_sizes,
        errors="coerce",
    ).fillna(position_sizes)
    equity = (1 + returns / 100).cumprod()
    portfolio_equity = (1 + portfolio_returns / 100).cumprod()
    calibrated_equity = (1 + calibrated_returns / 100).cumprod()
    winners = returns[returns > 0]
    losers = returns[returns <= 0]
    gross_profit = float(winners.sum())
    gross_loss = abs(float(losers.sum()))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (
        float("inf") if gross_profit > 0 else 0.0
    )

    metrics = {
        "trades": int(len(ordered)),
        "win_rate_pct": round(float((returns > 0).mean() * 100), 2),
        "average_return_pct": round(float(returns.mean()), 2),
        "median_return_pct": round(float(returns.median()), 2),
        "compounded_return_pct": round(float((equity.iloc[-1] - 1) * 100), 2),
        "max_drawdown_pct": round(_max_drawdown(equity), 2),
        "profit_factor": (
            round(profit_factor, 2) if math.isfinite(profit_factor) else "∞"
        ),
        "expectancy_pct": round(float(returns.mean()), 2),
        "average_holding_days": round(
            float(pd.to_numeric(ordered["holding_days"]).mean()),
            1,
        ),
        "portfolio_compounded_return_pct": round(float((portfolio_equity.iloc[-1] - 1) * 100), 2),
        "portfolio_max_drawdown_pct": round(_max_drawdown(portfolio_equity), 2),
        "average_position_size_pct": round(float(position_sizes.mean()), 2),
        "calibrated_compounded_return_pct": round(
            float((calibrated_equity.iloc[-1] - 1) * 100),
            2,
        ),
        "calibrated_max_drawdown_pct": round(
            _max_drawdown(calibrated_equity),
            2,
        ),
        "average_calibrated_position_size_pct": round(
            float(calibrated_sizes.mean()),
            2,
        ),
    }
    curve = pd.DataFrame(
        {
            "trade_number": range(1, len(equity) + 1),
            "equity": equity.values,
            "portfolio_equity": portfolio_equity.values,
            "calibrated_equity": calibrated_equity.values,
        }
    )
    return metrics, curve


def run_backtest(
    price_map: dict[str, pd.DataFrame],
    **kwargs,
) -> BacktestResult:
    all_trades: list[pd.DataFrame] = []
    errors: dict[str, str] = {}

    for ticker, frame in price_map.items():
        if str(ticker).upper() in {"SPY", "QQQ"}:
            continue
        try:
            trades = backtest_ticker(ticker, frame, **kwargs)
            if not trades.empty:
                all_trades.append(trades)
        except Exception as exc:
            errors[str(ticker).upper()] = str(exc)

    combined = (
        pd.concat(all_trades, ignore_index=True)
        if all_trades
        else pd.DataFrame(columns=TRADE_COLUMNS)
    )
    combined = apply_walk_forward_calibration(
        combined,
        enabled=bool(kwargs.get("walk_forward_calibration", True)),
        minimum_evidence_trades=int(
            kwargs.get("minimum_evidence_trades", 20)
        ),
        full_size_profit_factor=float(
            kwargs.get("full_size_profit_factor", 1.20)
        ),
        full_size_win_rate_pct=float(
            kwargs.get("full_size_win_rate_pct", 48.0)
        ),
        full_size_average_return_pct=float(
            kwargs.get("full_size_average_return_pct", 0.15)
        ),
    )
    metrics, curve = calculate_metrics(combined)

    assumptions = {
        "entry": "Next trading day's open after the signal",
        "overlap": "One open position per ticker",
        "ambiguous_bar": "Stop is assumed to trigger before target",
        "transaction_cost_pct": kwargs.get("transaction_cost_pct", 0.1),
        "holding_days": kwargs.get("holding_days", 20),
        "minimum_score": kwargs.get("minimum_score", 78),
        "signals": list(kwargs.get("signals", ("BUY",))),
        "target_stop": bool(kwargs.get("use_target_stop", True)),
        "adaptive_risk": bool(kwargs.get("adaptive_risk", True)),
        "base_position_pct": kwargs.get("base_position_pct", 20.0),
        "walk_forward_calibration": bool(
            kwargs.get("walk_forward_calibration", True)
        ),
        "minimum_evidence_trades": kwargs.get(
            "minimum_evidence_trades", 20
        ),
        "full_size_evidence_thresholds": {
            "profit_factor": kwargs.get("full_size_profit_factor", 1.20),
            "win_rate_pct": kwargs.get("full_size_win_rate_pct", 48.0),
            "average_return_pct": kwargs.get(
                "full_size_average_return_pct", 0.15
            ),
        },
    }
    return BacktestResult(
        trades=combined,
        equity_curve=curve,
        metrics=metrics,
        assumptions=assumptions,
        errors=errors,
    )
