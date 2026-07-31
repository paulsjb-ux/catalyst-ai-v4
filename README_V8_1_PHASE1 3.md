# Catalyst AI v8.1.0 — Phase 1 Storage Reliability

Phase 1 repairs and hardens the persistent storage layer before performance and UI refactoring.

## Fixed

- Removed recursive cloud storage calls caused by imported function names being shadowed by compatibility aliases.
- Added correct handling for modern `sb_publishable_...` / `sb_secret_...` API keys and legacy JWT keys.
- Added clear diagnostics for invalid keys, missing tables and RLS permission failures.
- Added read/write/delete health probing so `Cloud Ready` means Supabase is genuinely writable.
- Added atomic local JSON writes to prevent corrupted fallback files.
- Added strict JSON conversion for NumPy, pandas, datetime, NaN and infinity values.
- Preserved Supabase-connected status when a requested cloud key does not yet exist.
- Added a 30-second cloud read cache and cache invalidation after writes/deletes.
- Added a 60-second storage health cache to reduce repeated API calls on Streamlit reruns.
- Updated the supplied SQL with explicit anon/authenticated permissions and separate RLS policies.

## Install

Run `supabase_setup.sql` once in the Supabase SQL Editor after deploying this release. It is safe to run repeatedly.

Use the publishable key in Streamlit Secrets:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "sb_publishable_..."
```
