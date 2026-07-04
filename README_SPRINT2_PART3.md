# Catalyst AI v4 — Sprint 2 Part 3

Adds smarter scoring.

## New capability

The scan engine now scores candidates using:

- trend strength
- momentum quality
- volume confirmation
- relative strength proxy
- volatility penalty
- overextension penalty

## User-facing changes

Market Scan now includes:

- Candidate Results
- Scoring Breakdown
- Target & Stop Plans

## Replaces/adds

- engine/scoring.py
- engine/indicators.py
- engine/scanner.py
- ui/market_scan.py
- ui/dashboard.py
- tests/test_smarter_scoring.py
- tests/test_scanner_smarter.py
- version.py

## Run

```bash
cd ~/Documents/GitHub/catalyst-ai-v4
source .venv/bin/activate
python3 -m pytest
python3 -m streamlit run app.py
```

This is decision-support only and not financial advice.
