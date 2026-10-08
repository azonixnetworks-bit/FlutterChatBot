-- Phase 4 read-only verification.

-- Active-job uniqueness.
select indexname, indexdef
from pg_indexes
where schemaname = 'public'
  and indexname in (
    'processing_jobs_one_active_per_source_idx',
    'knowledge_sources_user_content_hash_uidx'
  )
order by indexname;

-- Backend RPC exists.
select
  p.proname,
  pg_get_function_identity_arguments(p.oid) as arguments
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
  and p.proname = 'enqueue_processing_job';

-- Only service_role should have explicit execute access for the enqueue RPC.
select
  has_function_privilege(
    'service_role',
    'public.enqueue_processing_job(uuid,uuid,text)',
    'EXECUTE'
  ) as service_role_can_execute,
  has_function_privilege(
    'authenticated',
    'public.enqueue_processing_job(uuid,uuid,text)',
    'EXECUTE'
  ) as authenticated_can_execute;

-- Backend table grants.
select table_name, privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee = 'service_role'
  and table_name in (
    'knowledge_sources',
    'knowledge_chunks',
    'processing_jobs',
    'conversations',
    'chat_messages'
  )
order by table_name, privilege_type;
