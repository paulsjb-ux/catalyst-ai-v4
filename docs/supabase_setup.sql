-- Catalyst AI v4 persistent storage
-- Run once in the Supabase SQL Editor.

create table if not exists public.catalyst_store (
    key text primary key,
    value jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now()
);

alter table public.catalyst_store enable row level security;

-- Simple single-user policy for a private app using the supplied API key.
-- For a public/multi-user app, replace this with authenticated per-user policies.
drop policy if exists "Catalyst read access" on public.catalyst_store;
drop policy if exists "Catalyst write access" on public.catalyst_store;

create policy "Catalyst read access"
on public.catalyst_store
for select
using (true);

create policy "Catalyst write access"
on public.catalyst_store
for all
using (true)
with check (true);

create index if not exists catalyst_store_updated_at_idx
on public.catalyst_store(updated_at desc);
