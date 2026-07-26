import pandas as pd

from engine.paper_trading import new_state, process_day, performance_metrics


def scan(price=100.0, signal="BUY"):
    return pd.DataFrame([{
        "ticker": "AAPL", "signal": signal, "score": 85, "close": price,
        "target_price": 110.0, "stop_loss": 95.0, "risk_reward": 2.0,
    }])


def test_real_engine_opens_qualifying_trade():
    state = process_day(new_state(), scan(), "RISK_ON", "2026-07-20")
    assert len(state["open_trades"]) == 1
    assert state["cash"] < 10000
    assert state["daily_runs"][-1]["opened"] == ["AAPL"]


def test_real_engine_marks_position_to_market():
    state = process_day(new_state(), scan(), "RISK_ON", "2026-07-20")
    state = process_day(state, scan(104), "RISK_ON", "2026-07-21")
    assert state["open_trades"][0]["unrealised_pnl"] > 0
    assert performance_metrics(state)["equity"] > 10000


def test_real_engine_closes_at_target():
    state = process_day(new_state(), scan(), "RISK_ON", "2026-07-20")
    state = process_day(state, scan(111), "RISK_ON", "2026-07-21")
    assert not state["open_trades"]
    assert state["closed_trades"][0]["exit_reason"] == "TARGET HIT"
    assert state["closed_trades"][0]["net_pnl"] > 0


def test_real_engine_closes_at_stop():
    state = process_day(new_state(), scan(), "RISK_ON", "2026-07-20")
    state = process_day(state, scan(94), "RISK_ON", "2026-07-21")
    assert state["closed_trades"][0]["exit_reason"] == "STOP HIT"
    assert state["closed_trades"][0]["net_pnl"] < 0


def test_real_engine_closes_when_signal_lost():
    state = process_day(new_state(), scan(), "RISK_ON", "2026-07-20")
    state = process_day(state, scan(102, "WATCH"), "RISK_ON", "2026-07-21")
    assert state["closed_trades"][0]["exit_reason"] == "SIGNAL LOST"
