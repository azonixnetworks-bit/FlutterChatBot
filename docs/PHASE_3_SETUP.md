# Phase 3 — Supabase Tables, RLS & Storage Security

## What this phase creates

Tables:
- `knowledge_sources`
- `knowledge_chunks`
- `processing_jobs`
- `conversations`
- `chat_messages`

Security:
- RLS enabled on all five tables
- authenticated users can access only rows where `user_id = auth.uid()`
- knowledge chunks and processing jobs are client read-only
- assistant/system chat messages are server-write only
- composite foreign keys prevent cross-user source/conversation relationships

Storage:
- private bucket: `knowledge-files`
- required object path: `USER_ID/SOURCE_ID/filename.ext`
- authenticated users can access only their own first-level folder

The vector column is intentionally NOT created in Phase 3. It will be added in Phase 13 together with the selected embedding model/dimension.

## Apply the migration

In PowerShell from the repository root:

```powershell
Get-Content -Raw .\supabase\migrations\202610080001_phase3_core.sql | Set-Clipboard
```

Then open Supabase:

1. SQL Editor
2. New query
3. Paste
4. Run

Expected result:

`Success. No rows returned`

## Verify

Copy this file and run it in a new SQL Editor query:

```powershell
Get-Content -Raw .\supabase\tests\phase3_verify.sql | Set-Clipboard
```

Confirm:
- all five tables report RLS enabled
- policies are present
- authenticated grants are present
- `knowledge-files` exists with `public = false`

## Important

Do not paste database passwords, Supabase secret keys, or service-role keys into Flutter or into Git.

Phase 4 will add the upload manager and processing-job workflow.
