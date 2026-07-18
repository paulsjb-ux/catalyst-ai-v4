import pandas as pd

from engine.paper_trading import calculate_position, new_state, performance_metrics, process_day, qualifying_candidates


def scan(price=100.0, signal="BUY", score=80.0):
    return pd.DataFrame({
        "ticker": ["TEST"],
        "signal": [signal],
        "score": [score],
        "close": [price],
        "target_price": [110.0],
        "stop_loss": [95.0],
        "risk_reward": [2.0],
    })


def test_candidate_filtering():
    state = new_state()
    result = qualifying_candidates(scan(), state, "RISK_ON")
    assert result["ticker"].tolist() == ["TEST"]
    assert qualifying_candidates(scan(score=60), state, "RISK_ON").empty
    assert qualifying_candidates(scan(), state, "RISK_OFF").empty


def test_position_is_capped_by_position_value():
    state = new_state()
    quantity, value, risk = calculate_position(100.0, 95.0, state)
    assert quantity == 20
    assert value == 2000.0
    assert risk == 100.0


def test_open_then_target_exit():
    state = new_state()
    process_day(state, scan(), "RISK_ON", "2026-07-20")
    assert len(state["open_trades"]) == 1
    assert state["cash"] < 10000

    process_day(state, scan(price=112.0), "RISK_ON", "2026-07-21")
    assert len(state["open_trades"]) == 0
    assert state["closed_trades"][0]["exit_reason"] == "TARGET HIT"
    assert state["closed_trades"][0]["net_pnl"] > 0


def test_duplicate_day_does_not_reprocess():
    state = new_state()
    process_day(state, scan(), "RISK_ON", "2026-07-20")
    process_day(state, scan(), "RISK_ON", "2026-07-20")
    assert len(state["daily_runs"]) == 1
    assert len(state["open_trades"]) == 1


def test_metrics():
    state = new_state()
    process_day(state, scan(), "RISK_ON", "2026-07-20")
    metrics = performance_metrics(state)
    assert metrics["days_run"] == 1
    assert metrics["open_trades"] == 1
    assert metrics["equity"] > 0
