import numpy as np
import pandas as pd

from data.market_data import _clean_frame
from engine.indicators import enrich_price_frame


def _price_values(rows=80):
    return np.linspace(100.0, 120.0, rows)


def test_clean_frame_removes_duplicate_close_columns():
    frame = pd.DataFrame(
        np.column_stack(
            [_price_values(), _price_values() + 1, np.arange(80)]
        ),
        columns=["Close", "Close", "Volume"],
    )
    cleaned = _clean_frame(frame)
    assert list(cleaned.columns) == ["Close", "Volume"]
    assert isinstance(cleaned["Close"], pd.Series)


def test_clean_frame_flattens_yfinance_multiindex():
    columns = pd.MultiIndex.from_tuples(
        [
            ("Close", "AAA"),
            ("Volume", "AAA"),
        ],
        names=["Price", "Ticker"],
    )
    frame = pd.DataFrame(
        np.column_stack([_price_values(), np.arange(80)]),
        columns=columns,
    )
    cleaned = _clean_frame(frame)
    assert list(cleaned.columns) == ["Close", "Volume"]
    assert len(cleaned) == 80


def test_indicators_accept_duplicate_close_input_without_assignment_error():
    frame = pd.DataFrame(
        np.column_stack(
            [_price_values(), _price_values() + 1, np.arange(80)]
        ),
        columns=["Close", "Close", "Volume"],
    )
    enriched = enrich_price_frame(frame)
    assert "sma_20" in enriched.columns
    assert isinstance(enriched["sma_20"], pd.Series)
    assert len(enriched) == 80
