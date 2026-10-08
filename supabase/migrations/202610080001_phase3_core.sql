-- Phase 3: Supabase core tables, RLS, and private storage security.
-- Run once in Supabase SQL Editor or via Supabase migrations.

begin;

-- ---------------------------------------------------------------------------
-- Shared updated_at trigger
-- ---------------------------------------------------------------------------

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- Knowledge sources
-- ---------------------------------------------------------------------------

create table if not exists public.knowledge_sources (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,

  file_name text not null,
  file_type text not null,
  mime_type text,

  storage_bucket text not null default 'knowledge-files',
  storage_path text not null,
  file_size_bytes bigint check (file_size_bytes is null or file_size_bytes >= 0),
  content_hash text,

  status text not null default 'uploaded'
    check (
      status in (
        'uploaded',
        'queued',
        'extracting',
        'chunking',
        'embedding',
        'indexing',
        'ready',
        'failed'
      )
    ),

  error_message text,
  metadata jsonb not null default '{}'::jsonb,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  unique (user_id, storage_path),
  unique (id, user_id)
);

create index if not exists knowledge_sources_user_id_idx
  on public.knowledge_sources (user_id);

create index if not exists knowledge_sources_user_status_idx
  on public.knowledge_sources (user_id, status);

create index if not exists knowledge_sources_user_created_at_idx
  on public.knowledge_sources (user_id, created_at desc);

drop trigger if exists set_knowledge_sources_updated_at
  on public.knowledge_sources;

create trigger set_knowledge_sources_updated_at
before update on public.knowledge_sources
for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Knowledge chunks
-- Vector embedding is intentionally added later in Phase 13.
-- ---------------------------------------------------------------------------

create table if not exists public.knowledge_chunks (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  source_id uuid not null,

  parent_chunk_id uuid,
  chunk_index integer not null check (chunk_index >= 0),

  content text not null,
  content_type text not null default 'text',

  page_number integer check (page_number is null or page_number > 0),
  section_title text,

  sheet_name text,
  row_start integer check (row_start is null or row_start > 0),
  row_end integer check (row_end is null or row_end > 0),

  start_time_ms bigint check (start_time_ms is null or start_time_ms >= 0),
  end_time_ms bigint check (end_time_ms is null or end_time_ms >= 0),

  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),

  unique (source_id, chunk_index),
  unique (id, user_id),

  constraint knowledge_chunks_source_owner_fk
    foreign key (source_id, user_id)
    references public.knowledge_sources (id, user_id)
    on delete cascade,

  constraint knowledge_chunks_parent_owner_fk
    foreign key (parent_chunk_id, user_id)
    references public.knowledge_chunks (id, user_id)
    on delete cascade
);

create index if not exists knowledge_chunks_user_id_idx
  on public.knowledge_chunks (user_id);

create index if not exists knowledge_chunks_source_id_idx
  on public.knowledge_chunks (source_id);

create index if not exists knowledge_chunks_parent_chunk_id_idx
  on public.knowledge_chunks (parent_chunk_id);

-- ---------------------------------------------------------------------------
-- Processing jobs
-- ---------------------------------------------------------------------------

create table if not exists public.processing_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  source_id uuid not null,

  job_type text not null,
  status text not null default 'queued'
    check (status in ('queued', 'processing', 'completed', 'failed', 'cancelled')),

  progress integer not null default 0
    check (progress between 0 and 100),

  current_step text,
  error_message text,
  metadata jsonb not null default '{}'::jsonb,

  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),

  constraint processing_jobs_source_owner_fk
    foreign key (source_id, user_id)
    references public.knowledge_sources (id, user_id)
    on delete cascade
);

create index if not exists processing_jobs_user_id_idx
  on public.processing_jobs (user_id);

create index if not exists processing_jobs_source_id_idx
  on public.processing_jobs (source_id);

create index if not exists processing_jobs_user_status_idx
  on public.processing_jobs (user_id, status);

-- ---------------------------------------------------------------------------
-- Conversations
-- ---------------------------------------------------------------------------

create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,

  title text,
  metadata jsonb not null default '{}'::jsonb,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  unique (id, user_id)
);

create index if not exists conversations_user_updated_at_idx
  on public.conversations (user_id, updated_at desc);

drop trigger if exists set_conversations_updated_at
  on public.conversations;

create trigger set_conversations_updated_at
before update on public.conversations
for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Chat messages
-- ---------------------------------------------------------------------------

create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null,
  user_id uuid not null,

  role text not null check (role in ('user', 'assistant', 'system')),
  content text not null,

  sources jsonb not null default '[]'::jsonb,
  metadata jsonb not null default '{}'::jsonb,

  created_at timestamptz not null default now(),

  constraint chat_messages_conversation_owner_fk
    foreign key (conversation_id, user_id)
    references public.conversations (id, user_id)
    on delete cascade
);

create index if not exists chat_messages_conversation_created_at_idx
  on public.chat_messages (conversation_id, created_at);

create index if not exists chat_messages_user_id_idx
  on public.chat_messages (user_id);

-- ---------------------------------------------------------------------------
-- Row Level Security
-- ---------------------------------------------------------------------------

alter table public.knowledge_sources enable row level security;
alter table public.knowledge_chunks enable row level security;
alter table public.processing_jobs enable row level security;
alter table public.conversations enable row level security;
alter table public.chat_messages enable row level security;

-- knowledge_sources: authenticated users manage only their own source records.

drop policy if exists "knowledge_sources_select_own" on public.knowledge_sources;
create policy "knowledge_sources_select_own"
on public.knowledge_sources
for select
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "knowledge_sources_insert_own" on public.knowledge_sources;
create policy "knowledge_sources_insert_own"
on public.knowledge_sources
for insert
to authenticated
with check ((select auth.uid()) = user_id);

drop policy if exists "knowledge_sources_update_own" on public.knowledge_sources;
create policy "knowledge_sources_update_own"
on public.knowledge_sources
for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "knowledge_sources_delete_own" on public.knowledge_sources;
create policy "knowledge_sources_delete_own"
on public.knowledge_sources
for delete
to authenticated
using ((select auth.uid()) = user_id);

-- knowledge_chunks: client read only. Trusted backend writes later.

drop policy if exists "knowledge_chunks_select_own" on public.knowledge_chunks;
create policy "knowledge_chunks_select_own"
on public.knowledge_chunks
for select
to authenticated
using ((select auth.uid()) = user_id);

-- processing_jobs: client read only. Trusted backend creates/updates later.

drop policy if exists "processing_jobs_select_own" on public.processing_jobs;
create policy "processing_jobs_select_own"
on public.processing_jobs
for select
to authenticated
using ((select auth.uid()) = user_id);

-- conversations: authenticated users manage only their own conversations.

drop policy if exists "conversations_select_own" on public.conversations;
create policy "conversations_select_own"
on public.conversations
for select
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "conversations_insert_own" on public.conversations;
create policy "conversations_insert_own"
on public.conversations
for insert
to authenticated
with check ((select auth.uid()) = user_id);

drop policy if exists "conversations_update_own" on public.conversations;
create policy "conversations_update_own"
on public.conversations
for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "conversations_delete_own" on public.conversations;
create policy "conversations_delete_own"
on public.conversations
for delete
to authenticated
using ((select auth.uid()) = user_id);

-- chat_messages: client can read its own messages and insert user messages only.
-- Assistant/system messages will be inserted by the trusted backend.

drop policy if exists "chat_messages_select_own" on public.chat_messages;
create policy "chat_messages_select_own"
on public.chat_messages
for select
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "chat_messages_insert_user_own" on public.chat_messages;
create policy "chat_messages_insert_user_own"
on public.chat_messages
for insert
to authenticated
with check (
  (select auth.uid()) = user_id
  and role = 'user'
);

-- ---------------------------------------------------------------------------
-- Explicit Data API grants.
-- Project setting "Automatically expose new tables" is intentionally OFF.
-- RLS still applies to every granted operation below.
-- ---------------------------------------------------------------------------

grant usage on schema public to authenticated;

grant select, insert, update, delete
  on public.knowledge_sources
  to authenticated;

grant select
  on public.knowledge_chunks
  to authenticated;

grant select
  on public.processing_jobs
  to authenticated;

grant select, insert, update, delete
  on public.conversations
  to authenticated;

grant select, insert
  on public.chat_messages
  to authenticated;

-- ---------------------------------------------------------------------------
-- Private Storage bucket
-- Path convention: USER_ID / SOURCE_ID / original.ext
-- ---------------------------------------------------------------------------

insert into storage.buckets (id, name, public)
values ('knowledge-files', 'knowledge-files', false)
on conflict (id) do update
set public = false;

drop policy if exists "knowledge_files_select_own" on storage.objects;
create policy "knowledge_files_select_own"
on storage.objects
for select
to authenticated
using (
  bucket_id = 'knowledge-files'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
);

drop policy if exists "knowledge_files_insert_own" on storage.objects;
create policy "knowledge_files_insert_own"
on storage.objects
for insert
to authenticated
with check (
  bucket_id = 'knowledge-files'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
);

drop policy if exists "knowledge_files_update_own" on storage.objects;
create policy "knowledge_files_update_own"
on storage.objects
for update
to authenticated
using (
  bucket_id = 'knowledge-files'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
)
with check (
  bucket_id = 'knowledge-files'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
);

drop policy if exists "knowledge_files_delete_own" on storage.objects;
create policy "knowledge_files_delete_own"
on storage.objects
for delete
to authenticated
using (
  bucket_id = 'knowledge-files'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
);

commit;
