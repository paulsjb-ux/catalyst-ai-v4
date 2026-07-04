import pandas as pd

from engine.validation import calculate_forward_returns, summarise_validation, add_quality_labels


def test_calculate_forward_returns_basic():
    scan = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "signal": ["BUY"],
            "score": [80],
            "close": [100.0],
        }
    )
    prices = {
        "AAPL": pd.DataFrame(
            {
                "Close": [100, 102, 103, 104, 105, 110, 111, 112, 113, 114, 115, 120, 121, 122, 123, 124, 125, 126, 127, 128, 130],
                "Volume": [1] * 21,
            }
        )
    }

    result = calculate_forward_returns(scan, prices)

    assert not result.empty
    assert result.iloc[0]["return_1d_pct"] == 2.0
    assert result.iloc[0]["return_5d_pct"] == 10.0


def test_summarise_validation_adds_quality():
    validation = pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT"],
            "signal": ["BUY", "BUY"],
            "score": [80, 85],
            "return_1d_pct": [1, 2],
            "win_1d": [True, True],
            "return_5d_pct": [3, 4],
            "win_5d": [True, True],
            "return_10d_pct": [5, 6],
            "win_10d": [True, True],
            "return_20d_pct": [7, 8],
            "win_20d": [True, True],
        }
    )

    summary = add_quality_labels(summarise_validation(validation))

    assert not summary.empty
    assert summary.iloc[0]["quality"] == "STRONG"
