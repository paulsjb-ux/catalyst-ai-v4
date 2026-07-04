import pandas as pd

from engine.validation import calculate_forward_returns, summarise_validation, add_quality_labels


def test_forward_returns_anchor_to_saved_at_date():
    scan = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "signal": ["BUY"],
            "score": [80],
            "close": [100.0],
            "saved_at": ["2026-01-03T12:00:00+00:00"],
        }
    )

    prices = {
        "AAPL": pd.DataFrame(
            {
                "Close": [90, 100, 105, 110, 115, 120],
                "Volume": [1, 1, 1, 1, 1, 1],
            },
            index=pd.to_datetime(
                [
                    "2026-01-01",
                    "2026-01-03",
                    "2026-01-04",
                    "2026-01-05",
                    "2026-01-06",
                    "2026-01-07",
                ],
                utc=True,
            ),
        )
    }

    result = calculate_forward_returns(scan, prices, windows=[1, 2])

    assert not result.empty
    assert result.iloc[0]["entry_price"] == 100
    assert result.iloc[0]["return_1d_pct"] == 5.0
    assert result.iloc[0]["return_2d_pct"] == 10.0


def test_forward_returns_pending_when_window_not_available():
    scan = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "signal": ["BUY"],
            "score": [80],
            "close": [100.0],
            "saved_at": ["2026-01-03T12:00:00+00:00"],
        }
    )

    prices = {
        "AAPL": pd.DataFrame(
            {
                "Close": [100, 105],
                "Volume": [1, 1],
            },
            index=pd.to_datetime(["2026-01-03", "2026-01-04"], utc=True),
        )
    }

    result = calculate_forward_returns(scan, prices, windows=[1, 5])

    assert result.iloc[0]["status_1d"] == "COMPLETE"
    assert result.iloc[0]["status_5d"] == "PENDING"
    assert pd.isna(result.iloc[0]["return_5d_pct"])


def test_summary_marks_pending_when_no_completed_5d():
    validation = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "signal": ["BUY"],
            "score": [80],
            "return_1d_pct": [1.0],
            "win_1d": [True],
            "status_1d": ["COMPLETE"],
            "return_5d_pct": [None],
            "win_5d": [None],
            "status_5d": ["PENDING"],
            "return_10d_pct": [None],
            "win_10d": [None],
            "status_10d": ["PENDING"],
            "return_20d_pct": [None],
            "win_20d": [None],
            "status_20d": ["PENDING"],
        }
    )

    summary = add_quality_labels(summarise_validation(validation))

    assert summary.iloc[0]["complete_5d"] == 0
    assert summary.iloc[0]["quality"] == "PENDING"
