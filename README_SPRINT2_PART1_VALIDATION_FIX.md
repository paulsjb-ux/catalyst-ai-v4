# Catalyst AI v4 — Sprint 2 Part 1 Validation Accuracy Fix

Fixes the forward-return validation logic.

## What changed

Previous validation could compare a saved scan entry price against the wrong part of the downloaded price series.

This patch now:

- uses the saved scan timestamp
- finds the nearest market close at or after that timestamp
- calculates 1D / 5D / 10D / 20D from that anchor
- marks unavailable future windows as PENDING
- avoids false negative validation for very recent scans

## Replaces/adds

- engine/validation.py
- ui/validation.py
- ui/reports.py
- tests/test_validation_accuracy.py
- version.py

## Run

```bash
cd ~/Documents/GitHub/catalyst-ai-v4
source .venv/bin/activate
python3 -m pytest
python3 -m streamlit run app.py
```
