-- Phase 5/6: atomic chunk replacement and PDF processing lifecycle.
begin;

alter table public.knowledge_sources
  drop constraint if exists knowledge_sources_status_check;
alter table public.knowledge_sources
  add constraint knowledge_sources_status_check check (
    status in ('uploaded', 'queued', 'extracting', 'analyzing', 'chunking',
               'embedding', 'indexing', 'ready', 'failed')
  );

create or replace function public.replace_knowledge_chunks_and_complete(
  p_user_id uuid,
  p_source_id uuid,
  p_job_id uuid,
  p_chunks jsonb
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  if not exists (
    select 1 from public.processing_jobs
    where id = p_job_id and source_id = p_source_id and user_id = p_user_id
  ) then
    raise exception 'Processing job not found' using errcode = 'P0002';
  end if;

  delete from public.knowledge_chunks
  where source_id = p_source_id and user_id = p_user_id;

  insert into public.knowledge_chunks (
    user_id, source_id, chunk_index, content, content_type, page_number, section_title, metadata
  )
  select p_user_id, p_source_id,
         (item->>'chunk_index')::integer,
         item->>'content',
         item->>'content_type',
         nullif(item->>'page_number', '')::integer,
         nullif(item->>'section_title', ''),
         coalesce(item->'metadata', '{}'::jsonb)
  from jsonb_array_elements(p_chunks) as item;

  update public.knowledge_sources
  set status = 'ready', error_message = null
  where id = p_source_id and user_id = p_user_id;

  update public.processing_jobs
  set status = 'completed', progress = 100, current_step = 'Completed',
      error_message = null, completed_at = now()
  where id = p_job_id and user_id = p_user_id;
end;
$$;

revoke all on function public.replace_knowledge_chunks_and_complete(uuid, uuid, uuid, jsonb)
  from public, anon, authenticated;
grant execute on function public.replace_knowledge_chunks_and_complete(uuid, uuid, uuid, jsonb)
  to service_role;

commit;
