# Catalyst AI v8.1.0 — Reliability and Performance

This release hardens persistent storage and improves runtime performance without changing trading rules.

## Changes
- Supabase modern-key compatibility retained (`apikey` only for `sb_publishable_` / `sb_secret_` keys).
- Short-lived cloud read cache to reduce repeated REST calls during Streamlit reruns.
- Batched cloud backup writes.
- Robust JSON serialization for pandas, NumPy, dates, paths, sets, NaN and infinity.
- Atomic local fallback writes to prevent partial JSON files.
- Accurate cloud status when a requested cloud key does not yet exist.
- Concurrent retry pool for failed market-data symbols.
- Lazy page imports for faster startup and isolation of page errors.
- Remaining duplicate root `indicators.py` converted to a compatibility wrapper.
- Version references aligned to 8.1.0.
