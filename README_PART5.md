# Catalyst AI v4 — Sprint 1 Part 5

Adds:
- production cleanup
- Streamlit config
- health checks
- test suite
- improved Settings page
- final metric readability polish
- Sprint 1 closeout documentation

## Install

Stop Streamlit, then replace/merge:

- version.py
- requirements.txt
- README.md
- ui/theme.py
- ui/settings.py
- data/health.py
- tests/
- .streamlit/
- docs/
- README_PART5.md

Then run:

```bash
cd ~/Documents/GitHub/catalyst-ai-v4
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m pytest
python3 -m streamlit run app.py
```
