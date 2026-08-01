import pandas as pd
from engine.adaptive_risk import adaptive_risk_plan
from engine.backtest import calculate_metrics
from engine.backtest_analysis import ticker_performance

def test_high_volatility_reduces_position_size():
    calm=adaptive_risk_plan(score=88,volatility_20d_pct=2,change_20d_pct=8,change_60d_pct=20,rsi_14=60)
    vol=adaptive_risk_plan(score=88,volatility_20d_pct=6,change_20d_pct=8,change_60d_pct=20,rsi_14=60)
    assert vol.position_size_pct < calm.position_size_pct
    assert vol.stop_atr_multiple > calm.stop_atr_multiple

def test_weaker_setup_is_smaller_than_strong_setup():
    strong=adaptive_risk_plan(score=92,volatility_20d_pct=2.5,change_20d_pct=12,change_60d_pct=30,rsi_14=64)
    weak=adaptive_risk_plan(score=78,volatility_20d_pct=2.5,change_20d_pct=-1,change_60d_pct=2,rsi_14=74)
    assert strong.position_size_pct > weak.position_size_pct

def test_watch_signal_gets_smaller_position():
    buy=adaptive_risk_plan(score=82,volatility_20d_pct=3,change_20d_pct=5,change_60d_pct=12,rsi_14=58,signal="BUY")
    watch=adaptive_risk_plan(score=82,volatility_20d_pct=3,change_20d_pct=5,change_60d_pct=12,rsi_14=58,signal="WATCH")
    assert watch.position_size_pct < buy.position_size_pct

def test_portfolio_metrics_support_old_trade_schema():
    trades=pd.DataFrame({"return_pct":[10,-10],"holding_days":[5,5],"exit_date":pd.date_range("2026-01-01",periods=2),"ticker":["A","B"]})
    metrics,curve=calculate_metrics(trades)
    assert metrics["average_position_size_pct"] == 100.0
    assert "portfolio_equity" in curve.columns

def test_ticker_performance_is_diagnostic():
    trades=pd.DataFrame({"ticker":["AAA","AAA","BBB"],"return_pct":[5,-2,1],"portfolio_return_pct":[1,-.4,.2]})
    result=ticker_performance(trades)
    assert set(result["ticker"])=={"AAA","BBB"}
