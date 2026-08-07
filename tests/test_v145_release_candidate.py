from datetime import date

import pandas as pd

from data import release_candidate_store as store
from engine.release_candidate import portfolio_snapshot


def test_add_trading_days_skips_weekend():
    assert store.add_trading_days(date(2026, 8, 7), 1).isoformat() == "2026-08-10"
    assert store.add_trading_days(date(2026, 8, 7), 3).isoformat() == "2026-08-12"


def test_record_recommendations_assigns_expiry(monkeypatch):
    memory = {}
    monkeypatch.setattr(store, "get", lambda key, default=None: memory.get(key, default))
    monkeypatch.setattr(store, "put", lambda key, value: memory.__setitem__(key, value) or "local")
    desk = pd.DataFrame([{"daily_rank": 1, "ticker": "MSFT", "action": "REVIEW", "score": 82, "swing_status": "QUALIFIED"}])
    store.record_recommendations(desk, run_at="2026-08-07T08:00:00+00:00")
    rows = memory[store.RECOMMENDATIONS_KEY]
    assert rows[0]["expires_date"] == "2026-08-12"


def test_portfolio_snapshot_handles_empty_state():
    result = portfolio_snapshot(None)
    assert result["equity"] == 0.0
    assert result["open_trades"] == 0
