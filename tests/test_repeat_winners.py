import pandas as pd
from engine.repeat_winners import build_repeat_winners

def test_repeat_winners_detects_priority():
    frames = [
        pd.DataFrame({"ticker": ["AAPL"], "signal": ["BUY"], "score": [80], "close": [100]}),
        pd.DataFrame({"ticker": ["AAPL"], "signal": ["BUY"], "score": [82], "close": [105]}),
        pd.DataFrame({"ticker": ["AAPL"], "signal": ["BUY"], "score": [84], "close": [110]}),
    ]
    winners = build_repeat_winners(frames)
    assert not winners.empty
    assert winners.iloc[0]["ticker"] == "AAPL"
    assert winners.iloc[0]["status"] == "PRIORITY"
