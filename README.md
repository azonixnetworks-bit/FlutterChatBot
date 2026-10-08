# FlutterChatBot

Multimodal knowledge chatbot built with Flutter, FastAPI, and Supabase.

## Current status

Phase 2 — Supabase Connection + Authentication.

## Supabase setup

Create a Supabase project and copy:
- Project URL
- Publishable/anon key
- Service-role key (server only)

Do not put the service-role key in Flutter.

### Flutter

Run from `mobile/`:

```powershell
flutter pub get
flutter run -d chrome --web-port 3000 --dart-define=SUPABASE_URL="YOUR_URL" --dart-define=SUPABASE_ANON_KEY="YOUR_ANON_KEY"
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
SUPABASE_ANON_KEY=
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
