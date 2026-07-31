-- Catalyst AI v8.1 persistent storage
-- Run once in the Supabase SQL Editor. Safe to run again.

create table if not exists public.catalyst_store (
    key text primary key,
    value jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now()
);

alter table public.catalyst_store enable row level security;

-- The app uses a publishable/anon key and is intended as a private single-user
-- deployment. Replace these policies with per-user authenticated policies if
-- the application is ever made public or shared with multiple users.
drop policy if exists "Catalyst read access" on public.catalyst_store;
drop policy if exists "Catalyst write access" on public.catalyst_store;

create policy "Catalyst read access"
on public.catalyst_store
for select
to anon, authenticated
using (true);

create policy "Catalyst write access"
on public.catalyst_store
for all
to anon, authenticated
using (true)
with check (true);

-- Explicit table privileges remove ambiguity for projects whose default grants
-- have been customised.
grant select, insert, update, delete on table public.catalyst_store to anon, authenticated;

create index if not exists catalyst_store_updated_at_idx
on public.catalyst_store(updated_at desc);
