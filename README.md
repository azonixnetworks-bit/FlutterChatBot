# FlutterChatBot

Multimodal knowledge chatbot built with Flutter, FastAPI, and Supabase.

## Current status

Phase 6 — PDF Multimodal Ingestion.

## Supabase setup

Create a Supabase project and copy:
- Project URL
- Publishable key
- Secret/service-role key (server only)

Do not put the service-role key in Flutter.

### Flutter

Run from `mobile/`:

```powershell
flutter pub get
flutter run -d chrome --web-port 3000 --dart-define=SUPABASE_URL="YOUR_URL" --dart-define=SUPABASE_PUBLISHABLE_KEY="YOUR_PUBLISHABLE_KEY"
```

For Android, use the same `--dart-define` values with your Android device ID.

iOS project files are included, but iOS builds require macOS + Xcode.

Without Supabase dart-defines the app intentionally shows a configuration-required screen.

### FastAPI

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill these values in `backend/.env`:

```text
SUPABASE_URL=
SUPABASE_PUBLISHABLE_KEY=
SUPABASE_SECRET_KEY=
SUPABASE_SERVICE_ROLE_KEY=
```

Then run:

```powershell
pytest
uvicorn app.main:app --reload
```

Endpoints:
- `GET /health`
- `GET /auth/me` with `Authorization: Bearer <Supabase access token>`

## Authentication flow

Flutter supports:
- email/password registration
- email/password sign in
- restored Supabase sessions
- protected Home route
- sign out

Supabase email confirmation behavior follows the project's Auth settings.

See `docs/PROJECT_SPEC.md` for the 20-phase roadmap.


## Easier local Flutter config

Create `mobile/env/dev.json` from `mobile/env/dev.json.example` and fill only your local Supabase public values.

Then run:

```powershell
cd mobile
flutter run -d chrome --dart-define-from-file=env/dev.json
```

`mobile/env/dev.json` is git-ignored and must not be committed.


## Phase 3 database setup

The Phase 3 migration is stored at:

`supabase/migrations/202610080001_phase3_core.sql`

Copy it to the clipboard from PowerShell:

```powershell
cd G:\FlutterChatBot
Get-Content -Raw .\supabase\migrations\202610080001_phase3_core.sql | Set-Clipboard
```

Paste it into Supabase SQL Editor and run it.

Then verify with:

```powershell
Get-Content -Raw .\supabase\tests\phase3_verify.sql | Set-Clipboard
```

See `docs/PHASE_3_SETUP.md` for expected results.


## Phase 4

Apply `supabase/migrations/202610080002_phase4_upload_jobs.sql`, configure the FastAPI backend secret key locally, and run the Knowledge Library upload flow.

Full instructions: `docs/PHASE_4_SETUP.md`

## Phase 5 and 6

Apply `supabase/migrations/202610080003_phase5_phase6_ingestion.sql` after the Phase 3 and 4 migrations. It enables atomic text/PDF chunk replacement and the PDF processing lifecycle.

See `docs/PHASE_5_SETUP.md` and `docs/PHASE_6_SETUP.md`. PDF OCR additionally requires the Tesseract executable on the backend worker host.
