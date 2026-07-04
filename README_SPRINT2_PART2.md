# Catalyst AI v4 — Sprint 2 Part 2

Adds target and stop planning.

## New capability

For BUY/WATCH candidates, Catalyst now estimates:

- entry price
- target price
- stop loss
- risk %
- reward %
- risk/reward ratio
- position quality

## Replaces/adds

- engine/risk.py
- engine/trade_plans.py
- ui/market_scan.py
- ui/dashboard.py
- ui/reports.py
- tests/test_risk.py
- tests/test_trade_plans.py
- version.py

## Run

```bash
cd ~/Documents/GitHub/catalyst-ai-v4
source .venv/bin/activate
python3 -m pytest
python3 -m streamlit run app.py
```

This is decision-support only and not financial advice.
