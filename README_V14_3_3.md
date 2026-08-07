# Catalyst AI v14.3.3 — iPhone Navigation Routing Fix

- Fixes the mobile navigation selector opening correctly but failing to change pages on iPhone/Safari.
- Uses the selectbox returned value as the routing source of truth and explicitly reruns the app after a mobile page selection.
- Keeps desktop sidebar navigation unchanged.
- Preserves v14.3.2 Supabase persistent 30-day validation storage and recovery tools.
- Makes no changes to trading, scoring, confidence, risk, or validation logic.
