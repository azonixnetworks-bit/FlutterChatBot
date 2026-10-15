-- Phase 12: atomically persist deterministic parent/child chunk trees.
begin;

create or replace function public.replace_knowledge_chunks_and_complete(
  p_user_id uuid, p_source_id uuid, p_job_id uuid, p_chunks jsonb
) returns void language plpgsql security definer set search_path = '' as $$
begin
  if not exists (
    select 1 from public.processing_jobs
    where id = p_job_id and source_id = p_source_id and user_id = p_user_id
  ) then
    raise exception 'Processing job not found' using errcode = 'P0002';
  end if;

  if exists (
    select 1 from jsonb_array_elements(p_chunks) child
    where nullif(child->>'parent_chunk_index', '') is not null
      and not exists (
        select 1 from jsonb_array_elements(p_chunks) parent
        where (parent->>'chunk_index')::integer = (child->>'parent_chunk_index')::integer
      )
  ) then
    raise exception 'Chunk tree contains an unknown parent index' using errcode = '23503';
  end if;

  delete from public.knowledge_chunks
  where source_id = p_source_id and user_id = p_user_id;

  -- Parents and independent chunks first, followed by children that reference
  -- the newly inserted parent within this transaction.
  insert into public.knowledge_chunks (
    user_id, source_id, chunk_index, content, content_type, page_number,
    section_title, start_time_ms, end_time_ms, metadata
  )
  select p_user_id, p_source_id, (item->>'chunk_index')::integer,
         item->>'content', item->>'content_type', nullif(item->>'page_number', '')::integer,
         nullif(item->>'section_title', ''), nullif(item->>'start_time_ms', '')::bigint,
         nullif(item->>'end_time_ms', '')::bigint, coalesce(item->'metadata', '{}'::jsonb)
  from jsonb_array_elements(p_chunks) item
  where nullif(item->>'parent_chunk_index', '') is null;

  insert into public.knowledge_chunks (
    user_id, source_id, parent_chunk_id, chunk_index, content, content_type,
    page_number, section_title, start_time_ms, end_time_ms, metadata
  )
  select p_user_id, p_source_id, parent.id, (item->>'chunk_index')::integer,
         item->>'content', item->>'content_type', nullif(item->>'page_number', '')::integer,
         nullif(item->>'section_title', ''), nullif(item->>'start_time_ms', '')::bigint,
         nullif(item->>'end_time_ms', '')::bigint, coalesce(item->'metadata', '{}'::jsonb)
  from jsonb_array_elements(p_chunks) item
  join public.knowledge_chunks parent
    on parent.user_id = p_user_id and parent.source_id = p_source_id
   and parent.chunk_index = (item->>'parent_chunk_index')::integer
  where nullif(item->>'parent_chunk_index', '') is not null;

  update public.knowledge_sources set status = 'ready', error_message = null
  where id = p_source_id and user_id = p_user_id;
  update public.processing_jobs
  set status = 'completed', progress = 100, current_step = 'Completed',
      error_message = null, completed_at = now()
  where id = p_job_id and user_id = p_user_id;
end; $$;

revoke all on function public.replace_knowledge_chunks_and_complete(uuid,uuid,uuid,jsonb)
  from public, anon, authenticated;
grant execute on function public.replace_knowledge_chunks_and_complete(uuid,uuid,uuid,jsonb)
  to service_role;
commit;
