import pandas as pd

from engine.paper_trading import (
    new_state,
    performance_by_setup,
    performance_metrics,
    process_day,
    ticker_currency,
    trade_journal,
)


def scan(price=100.0, signal="BUY", trend="TREND"):
    return pd.DataFrame([{
        "ticker": "AAPL", "signal": signal, "score": 85, "close": price,
        "target_price": 110.0, "stop_loss": 95.0, "risk_reward": 2.0,
        "trend": trend,
    }])


def test_sprint3_metrics_include_expectancy_and_average_loser():
    state = process_day(new_state(), scan(), "RISK_ON", "2026-07-20")
    state = process_day(state, scan(111), "RISK_ON", "2026-07-21")
    metrics = performance_metrics(state)
    assert "expectancy" in metrics
    assert "average_loss" in metrics
    assert metrics["expectancy"] > 0


def test_trade_journal_combines_open_and_closed_trades():
    state = process_day(new_state(), scan(), "RISK_ON", "2026-07-20")
    journal = trade_journal(state)
    assert len(journal) == 1
    assert journal.iloc[0]["status"] == "OPEN"
    state = process_day(state, scan(111), "RISK_ON", "2026-07-21")
    journal = trade_journal(state)
    assert journal.iloc[0]["status"] == "CLOSED"


def test_performance_by_setup_groups_closed_trades():
    state = process_day(new_state(), scan(trend="BREAKOUT"), "RISK_ON", "2026-07-20")
    state = process_day(state, scan(111, trend="BREAKOUT"), "RISK_ON", "2026-07-21")
    result = performance_by_setup(state)
    assert result.iloc[0]["setup"] == "BREAKOUT"
    assert result.iloc[0]["trades"] == 1


def test_native_currency_is_inferred_from_ticker_suffix():
    assert ticker_currency("AMGN") == "USD"
    assert ticker_currency("AZN.L") == "GBP"
    assert ticker_currency("MQG.AX") == "AUD"
