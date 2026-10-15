# Phase 4 — Upload Manager + Processing Jobs

## What is implemented

Flutter:
- Knowledge Library screen
- cross-platform file picker for Android, iOS and Web
- private Supabase Storage upload
- SHA-256 duplicate detection
- knowledge_sources registration
- upload stage/progress UI
- processing-job queue call to FastAPI
- knowledge source and latest job status display

FastAPI:
- POST /knowledge/jobs
- GET /knowledge/jobs/{job_id}
- verifies the user's Supabase access token
- uses a backend-only Supabase secret key
- never exposes the secret key to Flutter

Database:
- one active processing job per source
- one content hash per user to prevent accidental duplicate uploads
- atomic enqueue_processing_job RPC
- RPC is executable only by service_role

Phase 5 will add the first actual TXT/text processing worker. Until then successfully queued files remain in the queued state.

## 1. Apply Phase 4 migration

From PowerShell:

```powershell
cd G:\FlutterChatBot
git pull origin main
Get-Content -Raw .\supabase\migrations\202610080002_phase4_upload_jobs.sql | Set-Clipboard
```

In Supabase:
SQL Editor -> New query -> Ctrl+V -> Run

Expected:
`Success. No rows returned`

## 2. Configure FastAPI securely

In Supabase Dashboard get a backend Secret key (`sb_secret_...`).

Never put it in Flutter, Git, screenshots, or chat.

Create/update `backend/.env`:

```text
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLISHABLE_KEY
SUPABASE_SECRET_KEY=YOUR_SECRET_KEY
```

Legacy `SUPABASE_SERVICE_ROLE_KEY` remains supported as a fallback.

Run backend:

```powershell
cd G:\FlutterChatBot\backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest
uvicorn app.main:app --reload
```

Expected backend:
`http://127.0.0.1:8001`

## 3. Update Flutter local config

Your existing ignored file `mobile/env/dev.json` should contain:

```json
{
  "SUPABASE_URL": "https://YOUR_PROJECT_REF.supabase.co",
  "SUPABASE_PUBLISHABLE_KEY": "YOUR_PUBLISHABLE_KEY",
  "API_BASE_URL": "http://127.0.0.1:8001",
  "UPLOAD_MAX_BYTES": "52428800"
}
```

For Android emulator use `http://10.0.2.2:8001` for API_BASE_URL.
For a physical phone use your PC's LAN IP and allow the backend through the firewall.

## 4. Run Flutter

```powershell
cd G:\FlutterChatBot\mobile
flutter pub get
flutter run -d chrome --dart-define-from-file=env/dev.json
```

Open:
Home -> Open Knowledge Library -> Upload

## Supported upload types

- txt
- pdf
- docx
- csv
- xls
- xlsx
- jpg/jpeg/png/webp

The default local upload limit is 50 MB and can be changed with `UPLOAD_MAX_BYTES`, subject to the Supabase project/bucket limit.

## Test

For Phase 4 use a small TXT or PDF first.

Expected:
1. File uploads to private `knowledge-files` storage.
2. A `knowledge_sources` row is created.
3. FastAPI creates/returns a processing job.
4. Source status becomes `queued`.
5. Knowledge Library shows `QUEUED` and 0%.

No extraction happens yet; that begins in Phase 5.
