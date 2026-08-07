# Catalyst AI v4 — Sprint 2 Part 5

Adds a persistent watchlist and portfolio monitor.

## New capability

- Manual watchlist/holding entry
- CSV import
- Quantity and entry price
- Current market price
- Unrealised P&L
- Target and stop monitoring
- Distance to target and stop
- Latest signal and score
- Market regime context
- Action alerts
- CSV exports
- Dashboard portfolio snapshot

## Supported CSV columns

- ticker or symbol
- quantity or shares
- entry_price or average_price
- target_price or target
- stop_loss or stop
- notes

## Run

```bash
cd ~/Documents/GitHub/catalyst-ai-v4
source .venv/bin/activate
python3 -m pytest
python3 -m streamlit run app.py
```
