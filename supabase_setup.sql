-- Catalyst AI persistent storage — Phase 1 reliability setup
-- Safe to run repeatedly in the Supabase SQL Editor.

create table if not exists public.catalyst_store (
    key text primary key,
    value jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now()
);

alter table public.catalyst_store enable row level security;

drop policy if exists "Catalyst read access" on public.catalyst_store;
drop policy if exists "Catalyst insert access" on public.catalyst_store;
drop policy if exists "Catalyst update access" on public.catalyst_store;
drop policy if exists "Catalyst delete access" on public.catalyst_store;
drop policy if exists "Catalyst write access" on public.catalyst_store;

-- Private, single-user deployment using the project's publishable/anon key.
-- Replace these policies with authenticated per-user rules before making the
-- application publicly accessible to multiple users.
create policy "Catalyst read access"
on public.catalyst_store
for select
to anon, authenticated
using (true);

create policy "Catalyst insert access"
on public.catalyst_store
for insert
to anon, authenticated
with check (true);

create policy "Catalyst update access"
on public.catalyst_store
for update
to anon, authenticated
using (true)
with check (true);

create policy "Catalyst delete access"
on public.catalyst_store
for delete
to anon, authenticated
using (true);

grant usage on schema public to anon, authenticated;
grant select, insert, update, delete on table public.catalyst_store to anon, authenticated;

create index if not exists catalyst_store_updated_at_idx
on public.catalyst_store(updated_at desc);
