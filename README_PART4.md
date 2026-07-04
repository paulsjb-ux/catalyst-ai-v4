# Catalyst AI v4 — Sprint 1 Part 4

Adds:
- Local scan history storage
- Automatic save after each Market Scan
- Previous scan comparison
- Repeat Winners engine
- Validation Centre history view
- Reports page with scan index export
- Repeat winner report export

## Install

Stop Streamlit, then replace these files/folders in your existing repository:

- app.py
- version.py
- data/history_store.py
- engine/repeat_winners.py
- ui/dashboard.py
- ui/market_scan.py
- ui/repeat_winners.py
- ui/validation.py
- ui/reports.py
- storage/
- reports/

Then run:

```bash
source .venv/bin/activate
python3 -m streamlit run app.py
```

Run Market Scan once. The scan will be saved automatically under:

```text
storage/scans/
```
