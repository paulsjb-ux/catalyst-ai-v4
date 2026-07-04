# Catalyst AI v4

Catalyst AI v4 is a Streamlit-based market intelligence app.

## Version

`4.0.0-sprint1-part5`

## Sprint 1 includes

1. Core application foundation
2. UI package
3. Live market scanner
4. Local scan history and repeat winners
5. Production cleanup, tests and deployment readiness

## Run locally

```bash
cd ~/Documents/GitHub/catalyst-ai-v4
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

## Run tests

```bash
python3 -m pytest
```

## Entry point

```text
app.py
```

Catalyst AI v4 is decision-support software only. It does not place trades and does not provide financial advice.
