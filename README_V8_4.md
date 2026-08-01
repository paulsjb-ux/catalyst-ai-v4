# Catalyst AI v8.4.0 — Data Integrity & Release Cleanup

## Delivered

- Latest Daily Routine payload persisted through Supabase/local storage service
- Automatic restoration after Streamlit instance replacement
- Correct custom market-cache TTL handling
- Collision-resistant scan IDs
- Atomic scan CSV and scan-index writes
- Warning logs for degraded or corrupt fallback paths
- Publishable Supabase key preferred over secret keys
- Visible warning when multiple Supabase keys are configured
- Clean release ZIP builder excluding runtime data, caches and compiled files
- Version aligned to 8.4.0
