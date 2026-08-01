import pandas as pd

from engine.ranking import rank_candidates


def _sample():
    return pd.DataFrame(
        [
            {
                "ticker": "LEADER",
                "signal": "BUY",
                "score": 86,
                "change_1d_pct": 1.2,
                "change_20d_pct": 16,
                "change_60d_pct": 35,
                "rsi_14": 64,
                "volume_ratio": 1.5,
                "volatility_20d_pct": 2.2,
                "extension_penalty": 0,
                "volatility_penalty": 0,
                "close": 98,
                "high_52w": 100,
            },
            {
                "ticker": "MIDDLE",
                "signal": "WATCH",
                "score": 70,
                "change_1d_pct": 0.5,
                "change_20d_pct": 6,
                "change_60d_pct": 12,
                "rsi_14": 58,
                "volume_ratio": 1.1,
                "volatility_20d_pct": 3.5,
                "extension_penalty": -4,
                "volatility_penalty": -4,
                "close": 80,
                "high_52w": 100,
            },
            {
                "ticker": "WEAK",
                "signal": "IGNORE",
                "score": 40,
                "change_1d_pct": -4,
                "change_20d_pct": -12,
                "change_60d_pct": -25,
                "rsi_14": 34,
                "volume_ratio": 0.7,
                "volatility_20d_pct": 7,
                "extension_penalty": -12,
                "volatility_penalty": -12,
                "close": 50,
                "high_52w": 100,
            },
        ]
    )


def test_ranking_orders_strongest_candidate_first():
    ranked = rank_candidates(_sample())
    assert list(ranked["ticker"]) == ["LEADER", "MIDDLE", "WEAK"]
    assert list(ranked["priority_rank"]) == [1, 2, 3]


def test_ranking_does_not_change_signal_or_score():
    original = _sample().set_index("ticker")
    ranked = rank_candidates(_sample()).set_index("ticker")
    assert ranked["signal"].to_dict() == original["signal"].to_dict()
    assert ranked["score"].to_dict() == original["score"].to_dict()


def test_confidence_bands_are_explainable():
    ranked = rank_candidates(_sample()).set_index("ticker")
    assert ranked.loc["LEADER", "confidence_band"] in {"A", "B"}
    assert ranked.loc["WEAK", "confidence_band"] == "D"


def test_relative_strength_percentile_is_bounded():
    ranked = rank_candidates(_sample())
    assert ranked["relative_strength_percentile"].between(0, 100).all()
    assert ranked["priority_score"].between(0, 100).all()


def test_empty_frame_returns_ranking_columns():
    ranked = rank_candidates(pd.DataFrame())
    for column in [
        "priority_rank",
        "priority_score",
        "confidence_band",
        "relative_strength_percentile",
        "momentum_consistency",
        "risk_quality",
    ]:
        assert column in ranked.columns
