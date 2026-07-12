import pandas as pd

from engine.market_regime import analyse_index, apply_market_regime, build_market_regime


def _trend_prices(start=100, days=260, step=0.2):
    closes = [start + (i * step) for i in range(days)]
    return pd.DataFrame(
        {
            "Open": closes,
            "High": [c + 1 for c in closes],
            "Low": [c - 1 for c in closes],
            "Close": closes,
            "Volume": [1000000 + (i * 1000) for i in range(days)],
        },
        index=pd.date_range("2025-01-01", periods=days, freq="D"),
    )


def test_analyse_index_returns_regime_fields():
    result = analyse_index("SPY", _trend_prices())
    assert result["status"] == "READY"
    assert result["score"] > 0
    assert result["trend"] in {"BULLISH", "NEUTRAL", "BEARISH"}


def test_build_market_regime_returns_adjustment():
    regime = build_market_regime({"SPY": _trend_prices(), "QQQ": _trend_prices(start=120, step=0.3)})
    assert regime["regime"] in {"RISK_ON", "CONSTRUCTIVE", "NEUTRAL", "DEFENSIVE", "RISK_OFF"}
    assert isinstance(regime["regime_adjustment"], int)
    assert len(regime["indices"]) == 2


def test_apply_market_regime_changes_scores():
    frame = pd.DataFrame({"ticker": ["AAPL", "MSFT"], "signal": ["WATCH", "BUY"], "score": [60, 80]})
    regime = {"regime": "RISK_ON", "market_score": 80, "regime_adjustment": 6, "reason": "SPY BULLISH 80; QQQ BULLISH 80"}
    adjusted = apply_market_regime(frame, regime)
    assert "base_score" in adjusted.columns
    assert "market_adjustment" in adjusted.columns
    assert adjusted.iloc[0]["score"] == 66
