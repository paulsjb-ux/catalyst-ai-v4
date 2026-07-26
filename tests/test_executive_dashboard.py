import pandas as pd

from engine.executive_dashboard import confidence_grade, market_health, ranked_opportunities, vix_snapshot


def test_confidence_grades_cover_top_and_low_scores():
    assert confidence_grade(91) == "A+"
    assert confidence_grade(79) == "A-"
    assert confidence_grade(40) == "D"


def test_market_health_combines_regime_and_breadth():
    scan = pd.DataFrame({
        "close": [110, 90],
        "sma_50": [100, 100],
        "trend": ["TREND", "WEAK"],
    })
    result = market_health({"market_score": 60, "regime": "CONSTRUCTIVE"}, scan)
    assert result["risk_state"] == "RISK ON"
    assert result["above_50_pct"] == 50.0
    assert 0 <= result["score"] <= 100


def test_vix_snapshot_labels_high_volatility():
    result = vix_snapshot({"vix": {"close": 28.5}})
    assert result["level"] == 28.5
    assert result["label"] == "High"


def test_ranked_opportunities_adds_confidence_and_plan_data():
    scan = pd.DataFrame({
        "ticker": ["AAA", "BBB"],
        "signal": ["BUY", "WATCH"],
        "score": [82, 70],
        "trend": ["TREND", "RECOVERING"],
        "change_20d_pct": [8.0, 4.0],
        "rsi_14": [60, 55],
    })
    plans = pd.DataFrame({
        "ticker": ["AAA", "BBB"],
        "entry_price": [10, 20],
        "target_price": [12, 23],
        "stop_loss": [9, 18],
        "risk_reward": [2.0, 1.5],
    })
    result = ranked_opportunities(scan, plans)
    assert result.iloc[0]["ticker"] == "AAA"
    assert result.iloc[0]["confidence"] == "A-"
    assert "target_price" in result.columns
