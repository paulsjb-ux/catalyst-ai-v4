# Catalyst AI v14.3.2 — Persistent Validation Storage

v14.3.2 fixes the 30-day tracker resetting after Streamlit Cloud restarts/redeploys.

## Durable storage

The tracker now prefers Supabase/PostgreSQL. A local JSON copy is still written as a backup, but the UI clearly warns when only local storage is active.

### 1. Create a Supabase project
Create a free Supabase project, then run `supabase_schema.sql` in **SQL Editor**.

### 2. Add Streamlit secrets
In Streamlit Community Cloud > App > Settings > Secrets add:

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_KEY = "YOUR_SERVICE_ROLE_SERVER_SECRET"
CATALYST_VALIDATION_PROGRAMME_ID = "paul-catalyst-30-day-v1"
```

Use the Supabase **service role/server secret**, stored only in Streamlit Cloud Secrets. Do not use or expose it in browser-side code, GitHub, or source code.

### 3. Redeploy
Open **Validation**. The 30-day panel should show `Persistent storage: SUPABASE`.

## Recovery

Validation now includes a **Recovery & Persistence** panel.

* Import a previously downloaded `catalyst_30_day_auto_validation.json` and Catalyst safely merges unique days/trades.
* If earlier evidence was lost, manually add known completed dates. These dates are explicitly marked `RECOVERED`; Catalyst does not invent trade outcomes.
* Re-running a day cannot increment the 30-day count twice.

## Fail-safe behavior

If Supabase is configured but temporarily unavailable, Catalyst writes the local backup and displays `LOCAL_FALLBACK`. Do not treat a local-fallback run as safely archived until remote storage is healthy again.
