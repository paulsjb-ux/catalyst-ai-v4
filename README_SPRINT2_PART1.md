# Catalyst AI v4 — Sprint 2 Part 1

Adds forward-return validation.

## New capability

Catalyst can now estimate what happened after a saved BUY/WATCH signal:

- 1 trading day
- 5 trading days
- 10 trading days
- 20 trading days

## Replaces/adds

- engine/validation.py
- ui/validation.py
- ui/reports.py
- ui/dashboard.py
- tests/test_validation.py
- version.py

## Run

```bash
cd ~/Documents/GitHub/catalyst-ai-v4
source .venv/bin/activate
python3 -m pytest
python3 -m streamlit run app.py
```

## Notes

This is an evidence layer. It estimates forward returns from downloaded prices and saved scan entries. It does not place trades and does not provide financial advice.
