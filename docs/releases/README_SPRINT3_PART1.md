# Catalyst AI v4 — Sprint 3 Part 1

Adds persistent cloud storage with Supabase and automatic local fallback.

## Persistent data

- Watchlist and portfolio
- Scan index
- Full saved scan payloads
- Backups
- Restore points

## Setup

1. Create a Supabase project.
2. Open the Supabase SQL Editor.
3. Run `supabase_setup.sql`.
4. Add these values to Streamlit Community Cloud secrets:

```toml
SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
SUPABASE_KEY = "YOUR-SUPABASE-KEY"
```

5. Redeploy the app.
6. Open Settings.
7. Confirm `Cloud Ready: Yes`.
8. Click `Migrate local data to cloud`.
9. Click `Back up all data`.

## Behaviour

When Supabase is configured, Catalyst reads from cloud first and keeps a local cache. Without cloud credentials, it continues using local fallback storage.

## Security note

The supplied SQL is intended for a private single-user app. A public or multi-user deployment should use Supabase Auth and per-user row-level security.
