import pandas as pd

from engine.portfolio_monitor import build_portfolio_monitor, portfolio_summary


def test_build_portfolio_monitor_calculates_pnl_and_alerts():
    watchlist = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "quantity": [10],
            "entry_price": [100],
            "target_price": [110],
            "stop_loss": [95],
            "notes": [""],
            "added_at": ["2026-01-01"],
        }
    )

    prices = {
        "AAPL": pd.DataFrame(
            {"Close": [100, 108]},
            index=pd.date_range("2026-01-01", periods=2),
        )
    }

    scan = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "signal": ["BUY"],
            "score": [82],
        }
    )

    result = build_portfolio_monitor(
        watchlist=watchlist,
        price_map=prices,
        latest_scan=scan,
        market_regime={"regime": "RISK_ON"},
    )

    assert result.iloc[0]["market_value"] == 1080
    assert result.iloc[0]["unrealised_pnl"] == 80
    assert result.iloc[0]["latest_signal"] == "BUY"
    assert result.iloc[0]["holding_status"] in {"HOLD / STRONG", "TAKE PROFIT"}


def test_portfolio_summary():
    frame = pd.DataFrame(
        {
            "invested": [1000, 500],
            "market_value": [1100, 450],
            "alerts": ["NONE", "NEAR STOP"],
        }
    )

    summary = portfolio_summary(frame)

    assert summary["positions"] == 2
    assert summary["invested"] == 1500
    assert summary["market_value"] == 1550
    assert summary["unrealised_pnl"] == 50
    assert summary["alerts"] == 1
