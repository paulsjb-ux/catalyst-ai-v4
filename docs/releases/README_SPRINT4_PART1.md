# Catalyst AI — Sprint 4 Part 1

## 30-Day Paper Trading Simulator

This is a forward test, not a historical backtest. Each trading day it uses the latest saved Market Scan or Daily Routine output.

### Rules

- Starting balance: £10,000
- Trial length: 30 trading days
- Maximum open trades: 5
- Maximum position: £2,000
- Minimum BUY score: 75
- Minimum risk/reward: 2:1
- Risk per trade: 1%
- Maximum holding period: 10 trading days
- Entry and exit slippage: 0.1%
- No new trades during RISK_OFF or DEFENSIVE regimes

### Daily use

1. Run Daily Routine or Market Scan.
2. Open **Paper Trading**.
3. Press **Run Today's Paper Trades** once.
4. Review opened trades, exits and portfolio value.

### Install

Copy the patch contents into the repository, then run:

```bash
python3 scripts/install_sprint4_part1.py
python3 -m pytest
python3 -m streamlit run app.py
```

The version should show `6.0.0-sprint4-part1`.
