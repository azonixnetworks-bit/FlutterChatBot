-- Phase 4: trusted backend grants + atomic processing-job enqueue.

begin;

grant usage on schema public to service_role;

grant select, insert, update, delete
  on public.knowledge_sources,
     public.knowledge_chunks,
     public.processing_jobs,
     public.conversations,
     public.chat_messages
  to service_role;

-- Prevent multiple active ingestion jobs for the same source.
create unique index if not exists processing_jobs_one_active_per_source_idx
  on public.processing_jobs (source_id)
  where status in ('queued', 'processing');

-- Prevent accidental duplicate source content per user when a SHA-256 hash exists.
create unique index if not exists knowledge_sources_user_content_hash_uidx
  on public.knowledge_sources (user_id, content_hash)
  where content_hash is not null;

create or replace function public.enqueue_processing_job(
  p_user_id uuid,
  p_source_id uuid,
  p_job_type text default 'ingest'
)
returns public.processing_jobs
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_job public.processing_jobs;
begin
  if not exists (
    select 1
    from public.knowledge_sources
    where id = p_source_id
      and user_id = p_user_id
  ) then
    raise exception 'Knowledge source not found'
      using errcode = 'P0002';
  end if;

  select *
  into v_job
  from public.processing_jobs
  where source_id = p_source_id
    and user_id = p_user_id
    and status in ('queued', 'processing')
  order by created_at desc
  limit 1;

  if found then
    return v_job;
  end if;

  begin
    insert into public.processing_jobs (
      user_id,
      source_id,
      job_type,
      status,
      progress,
      current_step
    )
    values (
      p_user_id,
      p_source_id,
      p_job_type,
      'queued',
      0,
      'Waiting for processing worker'
    )
    returning * into v_job;
  exception
    when unique_violation then
      select *
      into v_job
      from public.processing_jobs
      where source_id = p_source_id
        and user_id = p_user_id
        and status in ('queued', 'processing')
      order by created_at desc
      limit 1;
  end;

  update public.knowledge_sources
  set status = 'queued',
      error_message = null
  where id = p_source_id
    and user_id = p_user_id;

  return v_job;
end;
$$;

revoke all
  on function public.enqueue_processing_job(uuid, uuid, text)
  from public, anon, authenticated;

grant execute
  on function public.enqueue_processing_job(uuid, uuid, text)
  to service_role;

commit;
