import pandas as pd

from data.storage_service import dataframe_to_records, records_to_dataframe


def test_dataframe_record_round_trip():
    frame = pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT"],
            "score": [80, None],
        }
    )

    records = dataframe_to_records(frame)
    restored = records_to_dataframe(records)

    assert restored["ticker"].tolist() == ["AAPL", "MSFT"]
    assert records[1]["score"] is None
