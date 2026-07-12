# Catalyst AI v4

Catalyst AI v4 is a Streamlit-based market intelligence app for scanning US equities, tracking repeat winners, validating signals, and building target/stop trade plans.

## Version

`4.3.2-sprint2-part3-score-latest-return`

## Current status

- Sprint 1 complete
- Sprint 2 Part 1 complete — forward validation
- Sprint 2 Part 1 accuracy fix complete — validation date anchoring
- Sprint 2 Part 2 complete — targets and stops
- Sprint 2 Part 2 compatibility patch complete
- Sprint 2 Part 3 complete — smarter scoring
- Sprint 2 Part 3 compatibility patch complete
- Tests passing: `19 passed`

## Sprint 1 included

1. Core application foundation
2. UI package
3. Live market scanner
4. Local scan history and repeat winners
5. Production cleanup, tests and deployment readiness

## Sprint 2 includes

### Part 1 — Forward Validation

- 1D / 5D / 10D / 20D forward-return validation
- BUY vs WATCH validation summary
- Win-rate calculations
- Validation quality labels
- Pending-window handling for recent scans

### Part 2 — Targets and Stops

- ATR volatility calculation
- Entry price
- Target price
- Stop loss
- Risk %
- Reward %
- Risk/reward ratio
- Position quality
- Trade-plan export

### Part 3 — Smarter Scoring

- Trend strength scoring
- Momentum quality scoring
- Volume confirmation
- Relative strength proxy
- Volatility penalty
- Overextension penalty
- Smarter BUY / WATCH / IGNORE guardrails
- Scoring breakdown table

## App pages

- Dashboard
- Market Scan
- Repeat Winners
- Validation
- Reports
- Settings

## Run locally

```bash
cd ~/Documents/GitHub/catalyst-ai-v4
source .venv/bin/activate
python3 -m streamlit run app.py
```

## Run tests

```bash
cd ~/Documents/GitHub/catalyst-ai-v4
source .venv/bin/activate
python3 -m pytest
```

Expected result:

```text
19 passed
```

## Entry point

```text
app.py
```

## Important note

Catalyst AI v4 is decision-support software only. It does not place trades and does not provide financial advice.
