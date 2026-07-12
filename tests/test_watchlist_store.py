import pandas as pd

from data.watchlist_store import _normalise


def test_normalise_watchlist_aliases():
    frame = pd.DataFrame(
        {
            "Symbol": ["aapl"],
            "Shares": [10],
            "Average_Price": [100],
            "Target": [120],
            "Stop": [90],
        }
    )

    result = _normalise(frame)

    assert result.iloc[0]["ticker"] == "AAPL"
    assert result.iloc[0]["quantity"] == 10
    assert result.iloc[0]["entry_price"] == 100
    assert result.iloc[0]["target_price"] == 120
    assert result.iloc[0]["stop_loss"] == 90
