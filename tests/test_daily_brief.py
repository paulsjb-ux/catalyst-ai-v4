import pandas as pd
from engine.daily_brief import build_daily_brief, daily_brief_to_markdown, near_stop_positions, near_target_positions, portfolio_alerts, signal_changes, top_buy_candidates


def test_top_buy_candidates_filters_and_sorts():
    frame = pd.DataFrame({"ticker": ["AAPL", "MSFT", "TSLA"], "signal": ["BUY", "BUY", "WATCH"], "score": [80, 90, 95], "close": [100, 200, 300]})
    assert top_buy_candidates(frame)["ticker"].tolist() == ["MSFT", "AAPL"]


def test_portfolio_helpers():
    frame = pd.DataFrame({"ticker": ["AAPL", "MSFT"], "alerts": ["NEAR TARGET", "NONE"], "distance_to_target_pct": [2.0, 8.0], "distance_to_stop_pct": [10.0, 2.5], "current_price": [100, 200], "target_price": [102, 216], "stop_loss": [90, 195]})
    assert portfolio_alerts(frame)["ticker"].tolist() == ["AAPL"]
    assert near_target_positions(frame)["ticker"].tolist() == ["AAPL"]
    assert near_stop_positions(frame)["ticker"].tolist() == ["MSFT"]


def test_signal_changes():
    frame = pd.DataFrame({"ticker": ["AAPL", "MSFT"], "signal_prev": ["WATCH", "BUY"], "signal_now": ["BUY", "BUY"], "signal_change": ["WATCH → BUY", "UNCHANGED"]})
    assert signal_changes(frame)["ticker"].tolist() == ["AAPL"]


def test_build_and_export():
    scan = pd.DataFrame({"ticker": ["AAPL"], "signal": ["BUY"], "score": [85], "close": [100]})
    brief = build_daily_brief({"regime": "RISK_ON", "market_score": 80, "regime_adjustment": 6, "risk_label": "Supportive", "reason": "SPY and QQQ bullish"}, scan, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    markdown = daily_brief_to_markdown(brief)
    assert brief["top_buys"].iloc[0]["ticker"] == "AAPL"
    assert "Catalyst AI Daily Intelligence Brief" in markdown
    assert "AAPL" in markdown
