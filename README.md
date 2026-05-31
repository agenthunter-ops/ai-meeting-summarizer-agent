# AI Meeting Summarizer and Action-Item Generator

This project converts meeting transcripts into structured, evidence-backed meeting notes.

The app can create meeting notes from:

- pasted transcript text
- a small audio upload skeleton
- a simulated recording-completed webhook

The core promise is:

```text
Important decisions and action items should point back to evidence in the original transcript.
```

## Problem Statement

Meeting notes are useful only when they are accurate and actionable.

After meetings, teams often need to reconstruct:

- what was decided
- who owns each task
- which deadlines were mentioned
- what risks or blockers were raised
- what needs follow-up

A generic AI summary can sound correct while inventing details. This project reduces that risk by validating evidence quotes before storing decisions and action items.

## MVP Scope

Built in the current MVP:

- FastAPI backend
- SQLite database with SQLAlchemy models
- Pydantic request and response schemas
- transcript paste flow
- mock summarizer fallback
- optional Gemini summarizer path
- evidence validator
- meeting create/list/detail APIs
- action item update API
- Markdown export
- simple React MVP screen
- audio upload skeleton with sample transcription
- simulated recording-completed webhook
- focused backend tests

Not built as production features:

- real Zoom OAuth
- real Microsoft Teams integration
- authentication
- multi-user permissions
- production deployment
- real transcription provider
- advanced frontend routing
- background job queue

## Tech Stack

- Backend: FastAPI
- Database: SQLite
- ORM: SQLAlchemy
- Validation: Pydantic
- AI: Gemini REST API with mock fallback
- Frontend: React-style Vite-ready components
- Tests: pytest
- Runtime: Windows PowerShell

## Architecture

```text
Frontend
  -> api.js
  -> FastAPI routes
  -> Pydantic schemas
  -> SQLAlchemy models
  -> Summarizer service
  -> Validator service
  -> SQLite database
  -> Exporter service
```

Main backend files:

- `backend/app/main.py`: API routes and workflow coordination
- `backend/app/database.py`: SQLite and SQLAlchemy session setup
- `backend/app/models.py`: database table definitions
- `backend/app/schemas.py`: API request and response shapes
- `backend/app/services/summarizer.py`: mock and Gemini summarization
- `backend/app/services/validator.py`: evidence validation
- `backend/app/services/exporter.py`: Markdown export
- `backend/app/services/transcription.py`: audio-to-transcript abstraction skeleton

## Trust Boundary

The app treats these as untrusted:

- pasted transcript input
- uploaded files
- webhook payloads
- Gemini output
- mock or future LLM output

The validator checks that decisions and action items include evidence quotes found in the transcript before storing them as reliable output.

## Environment Variables

Copy `.env.example` to `.env` for local private configuration.

```text
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
```

Never commit real API keys.

If `GEMINI_API_KEY` is missing or Gemini fails, the app falls back to the mock summarizer.

The project `.gitignore` excludes `.env`, local databases, uploads, caches, build output, and dependency folders.

## Run Backend

From the repository root:

```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8010
```

Then open:

```text
http://127.0.0.1:8010/docs
```

## Run Tests

From the repository root:

```powershell
cd backend
python -m pytest
```

Current focused backend tests cover:

- meeting creation
- meeting list and detail retrieval
- action item updates
- invalid status rejection
- Markdown export
- simulated webhook creation
- validator behavior
- summarizer fallback
- exporter formatting

## Frontend Status

The frontend has:

- `frontend/src/api.js`
- `frontend/src/App.jsx`
- `frontend/src/main.jsx`
- `frontend/index.html`
- `frontend/package.json`

Run the frontend from the repository root:

```powershell
cd frontend
npm install
npm run dev
```

The frontend defaults to:

```text
VITE_API_BASE_URL=http://127.0.0.1:8010
```

Build check:

```powershell
cd frontend
npm run build
```

## API Endpoints

```text
GET    /health
POST   /meetings
GET    /meetings
GET    /meetings/{meeting_id}
PATCH  /action-items/{action_item_id}
GET    /meetings/{meeting_id}/export
POST   /meetings/audio
POST   /webhooks/recording-completed
```

## Sample Transcript

```text
Neha: Abhishek, please create the first working POC by Friday.
Jeevan, please validate the logging fields by Wednesday.
Aditya: The biggest risk is latency.
```

Expected extracted ideas:

- Abhishek owns creating the POC.
- Jeevan owns validating logging fields.
- Latency is a risk.
- Each extracted item should include transcript evidence.

## Key Tradeoffs

- SQLite is used because it is simple for a local MVP.
- Mock summarization exists so the app works without API keys.
- Gemini is optional and guarded by fallback behavior.
- JSON text fields are used for decisions, risks, and follow-up questions to keep the MVP database simple.
- Audio upload and webhook features are skeletons, not production integrations.
- The frontend is intentionally small and single-screen for explainability.

## Failure Modes

- Gemini key missing: use mock summarizer.
- Gemini returns bad JSON: use mock summarizer.
- Evidence quote missing from transcript: validator rejects the item.
- Unknown meeting ID: return 404.
- Invalid action item status: return validation error.
- Unsupported audio extension: reject upload.
- Transcription failure: meeting remains saved with failure status.

## Future Improvements

- Add real transcription provider.
- Add authentication.
- Add owner/status/priority filters.
- Add real platform webhook verification.
- Replace `on_event` with FastAPI lifespan handler.
- Use timezone-aware UTC timestamps.
- Add production database migrations.
- Add deployment documentation.

## Interview Summary

This project is a small, explainable AI workflow app.

The backend does not blindly trust AI output. It stores the original transcript, asks a summarizer for structured notes, validates evidence quotes, stores only supported action items and decisions, and exposes APIs for viewing, updating, and exporting meeting notes.
