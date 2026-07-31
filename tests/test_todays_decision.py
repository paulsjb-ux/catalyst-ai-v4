import pandas as pd

from engine.todays_decision import build_todays_decision


def test_no_trade_when_no_candidates():
    scan = pd.DataFrame([{"ticker": "AAA", "signal": "NO TRADE", "score": 40}])
    decision = build_todays_decision(scan, pd.DataFrame(), {"regime": "RISK_OFF", "market_score": 30})
    assert decision.action == "NO TRADE"
    assert decision.buy_count == 0
    assert decision.watch_count == 0


def test_watch_when_watch_candidates_exist():
    scan = pd.DataFrame([{"ticker": "AAA", "signal": "WATCH", "score": 70, "trend": "TREND"}])
    decision = build_todays_decision(scan, pd.DataFrame(), {"regime": "NEUTRAL", "market_score": 55})
    assert decision.action == "WATCH"
    assert decision.best_opportunity["ticker"] == "AAA"


def test_trade_requires_buy_and_supportive_market():
    scan = pd.DataFrame([{"ticker": "AAA", "signal": "BUY", "score": 82, "trend": "TREND"}])
    plans = pd.DataFrame([{"ticker": "AAA", "entry_price": 100, "target_price": 110, "stop_loss": 95, "risk_reward": 2.0}])
    decision = build_todays_decision(scan, plans, {"regime": "RISK_ON", "market_score": 75})
    assert decision.action == "TRADE"
    assert decision.confidence == 82


def test_risk_off_downgrades_buy_to_watch():
    scan = pd.DataFrame([{"ticker": "AAA", "signal": "BUY", "score": 85, "trend": "TREND"}])
    plans = pd.DataFrame([{"ticker": "AAA", "risk_reward": 3.0}])
    decision = build_todays_decision(scan, plans, {"regime": "RISK_OFF", "market_score": 25})
    assert decision.action == "WATCH"
