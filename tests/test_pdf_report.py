import pandas as pd

from engine.pdf_report import build_trading_desk_pdf


def test_pdf_report_is_valid_pdf():
    data = build_trading_desk_pdf(
        version="7.0.0",
        summary={"scanned": 323, "buy_count": 2, "watch_count": 14},
        regime={"regime": "DEFENSIVE", "risk_label": "Cautious", "market_score": 38},
        opportunities=pd.DataFrame([
            {"ticker": "AMGN", "signal": "WATCH", "confidence": "A-", "score": 83, "trend": "TREND", "risk_reward": 1.67}
        ]),
    )
    assert data.startswith(b"%PDF")
    assert len(data) > 1000
