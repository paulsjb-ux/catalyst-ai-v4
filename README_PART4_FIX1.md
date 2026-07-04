# Catalyst AI v4 — Part 4 Repeat Winners Fix

Fixes:
- Streamlit slider crash when exactly 2 saved scans exist.

Replaces:
- ui/repeat_winners.py
- version.py

Install:
1. Stop Streamlit.
2. Copy these files into the existing repository.
3. Choose Replace.
4. Restart:
   source .venv/bin/activate
   python3 -m streamlit run app.py
