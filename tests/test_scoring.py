import pandas as pd
from engine.scoring import score_latest

def test_score_latest_returns_valid_signal():
    row = pd.Series({
        "Close": 110,
        "SMA20": 105,
        "SMA50": 100,
        "SMA200": 90,
        "RSI14": 60,
        "VolumeRatio": 1.3,
        "Change20D": 8,
    })
    score, signal, trend, reason = score_latest(row)
    assert 0 <= score <= 100
    assert signal in {"BUY", "WATCH", "IGNORE"}
    assert trend in {"TREND", "RECOVERING", "WEAK"}
    assert isinstance(reason, str)
