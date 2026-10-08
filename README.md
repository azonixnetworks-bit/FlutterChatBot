# FlutterChatBot

Multimodal knowledge chatbot built with Flutter, FastAPI, and Supabase.

## Current status

Phase 1 — Project Bootstrap & Architecture.

The repository is being built incrementally. See `docs/PROJECT_SPEC.md` for the long-term architecture and `AGENTS.md` for development rules.

## Local setup

### Flutter

After cloning/pulling, if platform folders are not present yet:

```powershell
cd mobile
flutter create --platforms=android,ios,web,windows .
flutter pub get
flutter analyze
flutter run
```

### FastAPI

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Health check:

`GET http://127.0.0.1:8000/health`

Run tests:

```powershell
pytest
```
