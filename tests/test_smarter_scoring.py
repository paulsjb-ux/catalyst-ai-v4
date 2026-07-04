import pandas as pd

from engine.scoring import assign_signal, explain_score, score_quality


def test_score_quality_rewards_clean_trend():
    row = pd.Series(
        {
            "close": 110,
            "sma_20": 105,
            "sma_50": 100,
            "sma_200": 90,
            "change_20d_pct": 10,
            "change_60d_pct": 20,
            "rsi_14": 60,
            "volume_ratio": 1.3,
            "high_52w": 112,
            "volatility_20d_pct": 2,
        }
    )

    result = score_quality(row)

    assert result["score"] >= 70
    assert result["trend_score"] > 0
    assert result["momentum_score"] > 0
    assert result["volume_score"] > 0


def test_score_quality_penalises_overextension():
    row = pd.Series(
        {
            "close": 150,
            "sma_20": 100,
            "sma_50": 95,
            "sma_200": 90,
            "change_20d_pct": 50,
            "change_60d_pct": 80,
            "rsi_14": 82,
            "volume_ratio": 0.7,
            "high_52w": 151,
            "volatility_20d_pct": 7,
        }
    )

    result = score_quality(row)

    assert result["volatility_penalty"] < 0
    assert result["extension_penalty"] < 0
    assert result["score"] < 70


def test_assign_signal_uses_guardrails():
    row = pd.Series(
        {
            "score": 85,
            "trend_score": 30,
            "momentum_score": 18,
            "volatility_penalty": -12,
            "extension_penalty": 0,
        }
    )

    assert assign_signal(row) == "WATCH"


def test_explain_score_returns_text():
    row = pd.Series(
        {
            "trend_score": 25,
            "momentum_score": 18,
            "volume_score": 12,
            "relative_strength_score": 10,
            "volatility_penalty": 0,
            "extension_penalty": 0,
        }
    )

    assert "strong trend" in explain_score(row)
