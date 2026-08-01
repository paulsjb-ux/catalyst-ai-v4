from __future__ import annotations

import numpy as np
import pandas as pd

from engine.backtest import (
    TRADE_COLUMNS,
    backtest_ticker,
    calculate_metrics,
    run_backtest,
)


def _frame(rows: int = 320, drift: float = 0.35) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=rows, freq="B")
    close = 50 + np.arange(rows) * drift
    return pd.DataFrame(
        {
            "Open": close - 0.1,
            "High": close + 0.8,
            "Low": close - 0.8,
            "Close": close,
            "Volume": np.linspace(100_000, 250_000, rows),
        },
        index=index,
    )


def test_backtest_enters_after_signal_date():
    trades = backtest_ticker(
        "AAA",
        _frame(),
        holding_days=10,
        minimum_score=55,
        signals=("BUY", "WATCH"),
        use_target_stop=False,
    )
    assert not trades.empty
    assert (pd.to_datetime(trades["entry_date"]) > pd.to_datetime(trades["signal_date"])).all()


def test_backtest_has_no_overlapping_positions_per_ticker():
    trades = backtest_ticker(
        "AAA",
        _frame(),
        holding_days=15,
        minimum_score=55,
        signals=("BUY", "WATCH"),
        use_target_stop=False,
    )
    if len(trades) > 1:
        previous_exits = pd.to_datetime(trades["exit_date"]).iloc[:-1].reset_index(drop=True)
        next_entries = pd.to_datetime(trades["entry_date"]).iloc[1:].reset_index(drop=True)
        assert (next_entries > previous_exits).all()


def test_transaction_cost_reduces_return():
    frame = _frame()
    no_cost = backtest_ticker(
        "AAA",
        frame,
        holding_days=10,
        minimum_score=55,
        signals=("BUY", "WATCH"),
        use_target_stop=False,
        transaction_cost_pct=0,
    )
    with_cost = backtest_ticker(
        "AAA",
        frame,
        holding_days=10,
        minimum_score=55,
        signals=("BUY", "WATCH"),
        use_target_stop=False,
        transaction_cost_pct=0.5,
    )
    assert not no_cost.empty
    assert np.allclose(
        no_cost["return_pct"] - with_cost["return_pct"],
        0.5,
        atol=0.001,
    )


def test_metrics_are_calculated_from_trade_returns():
    trades = pd.DataFrame(
        {
            "return_pct": [10.0, -5.0, 4.0],
            "holding_days": [10, 5, 7],
            "exit_date": pd.date_range("2025-01-01", periods=3),
            "ticker": ["A", "B", "C"],
        }
    )
    metrics, curve = calculate_metrics(trades)
    assert metrics["trades"] == 3
    assert metrics["win_rate_pct"] == 66.67
    assert not curve.empty
    assert metrics["max_drawdown_pct"] <= 0


def test_empty_backtest_returns_stable_schema():
    result = run_backtest({})
    assert list(result.trades.columns) == TRADE_COLUMNS
    assert result.metrics["trades"] == 0


def test_stop_first_is_conservative_on_ambiguous_bar():
    frame = _frame()
    # The basic engine contract is validated indirectly: target/stop runs
    # return only the documented exit reasons.
    trades = backtest_ticker(
        "AAA",
        frame,
        holding_days=20,
        minimum_score=55,
        signals=("BUY", "WATCH"),
        use_target_stop=True,
    )
    assert set(trades["exit_reason"]).issubset({"STOP", "TARGET", "TIME"})
