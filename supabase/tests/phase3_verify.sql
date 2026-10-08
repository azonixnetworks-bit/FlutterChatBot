-- Phase 3 read-only verification queries.

-- 1. Tables + RLS
select
  tablename,
  rowsecurity as rls_enabled
from pg_tables
where schemaname = 'public'
  and tablename in (
    'knowledge_sources',
    'knowledge_chunks',
    'processing_jobs',
    'conversations',
    'chat_messages'
  )
order by tablename;

-- 2. RLS policies
select
  tablename,
  policyname,
  cmd,
  roles
from pg_policies
where schemaname = 'public'
  and tablename in (
    'knowledge_sources',
    'knowledge_chunks',
    'processing_jobs',
    'conversations',
    'chat_messages'
  )
order by tablename, policyname;

-- 3. Explicit authenticated Data API grants
select
  table_name,
  privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee = 'authenticated'
  and table_name in (
    'knowledge_sources',
    'knowledge_chunks',
    'processing_jobs',
    'conversations',
    'chat_messages'
  )
order by table_name, privilege_type;

-- 4. Storage bucket must be private
select
  id,
  name,
  public
from storage.buckets
where id = 'knowledge-files';

-- 5. Storage policies
select
  policyname,
  cmd,
  roles
from pg_policies
where schemaname = 'storage'
  and tablename = 'objects'
  and policyname like 'knowledge_files_%'
order by policyname;
