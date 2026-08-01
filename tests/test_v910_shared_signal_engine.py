import numpy as np
import pandas as pd

from engine.backtest import (
    _indicator_row,
    backtest_ticker,
    run_backtest,
)
from engine.indicators import enrich_price_frame
from engine.scanner import score_enriched_row


def _frame(rows=340):
    close = 40 + np.arange(rows) * 0.25
    return pd.DataFrame(
        {
            "Open": close - 0.05,
            "High": close + 0.8,
            "Low": close - 0.8,
            "Close": close,
            "Volume": np.linspace(100_000, 300_000, rows),
        },
        index=pd.date_range(
            "2024-01-01",
            periods=rows,
            freq="B",
        ),
    )


def test_historical_row_matches_live_scanner_row():
    enriched = enrich_price_frame(_frame())
    row = enriched.iloc[-1]
    live = score_enriched_row(
        "AAA",
        row,
        round_values=False,
    )
    historical = _indicator_row("AAA", row).to_dict()
    for field in [
        "score",
        "signal",
        "trend_score",
        "momentum_score",
        "volume_score",
        "relative_strength_score",
        "volatility_penalty",
        "extension_penalty",
    ]:
        assert historical[field] == live[field]


def test_calibration_options_do_not_leak_into_ticker_function():
    result = run_backtest(
        {"AAA": _frame()},
        minimum_score=55,
        signals=("BUY", "WATCH"),
        walk_forward_calibration=True,
        minimum_evidence_trades=20,
        full_size_profit_factor=1.2,
        full_size_win_rate_pct=48,
        full_size_average_return_pct=0.15,
    )
    assert "AAA" not in result.errors
    assert result.diagnostics["tickers_processed"] == 1
    assert result.diagnostics["bars_evaluated"] > 0


def test_diagnostics_explain_zero_trade_result():
    result = run_backtest(
        {"AAA": _frame()},
        minimum_score=100,
        signals=("BUY",),
    )
    assert result.trades.empty
    assert result.diagnostics["bars_evaluated"] > 0
    assert result.diagnostics["accepted_entries"] == 0
    assert result.diagnostics["maximum_score"] < 100


def test_ticker_diagnostics_count_accepted_entries():
    diagnostics = {}
    trades = backtest_ticker(
        "AAA",
        _frame(),
        minimum_score=55,
        signals=("BUY", "WATCH"),
        diagnostics=diagnostics,
        use_target_stop=False,
    )
    assert diagnostics["bars_evaluated"] > 0
    assert diagnostics["accepted_entries"] == len(trades)
