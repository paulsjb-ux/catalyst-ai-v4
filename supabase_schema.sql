-- Catalyst AI v14.3.2 durable 30-day validation storage
-- Run this once in Supabase > SQL Editor.

create table if not exists public.catalyst_auto_validation (
  programme_id text primary key,
  payload jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.catalyst_auto_validation enable row level security;

-- No public/anon policy is created intentionally.
-- Use the Supabase service-role/server secret ONLY in Streamlit Cloud Secrets.
-- The service role bypasses RLS on the server. Never commit or expose this key.
