# Architecture

This project is a small AI meeting workflow app.

It accepts meeting transcript input, stores the meeting, creates structured notes, validates evidence-backed output, and returns meeting details through a FastAPI backend.

## High-Level Shape

```text
React UI
  -> frontend/src/api.js
  -> FastAPI routes in backend/app/main.py
  -> Pydantic schemas in backend/app/schemas.py
  -> SQLAlchemy models in backend/app/models.py
  -> SQLite database
  -> service layer
       - summarizer.py
       - validator.py
       - exporter.py
       - transcription.py
```

## Main Transcript Paste Flow

```text
User pastes transcript
-> Frontend calls createMeeting
-> POST /meetings receives MeetingCreateRequest
-> Backend creates Meeting row
-> Backend stores TranscriptSegment row
-> Summarizer creates structured notes
-> Validator checks decisions and action item evidence
-> Backend stores MeetingSummary and ActionItem rows
-> Backend returns MeetingDetailResponse
```

The important design point is that summarizer output is not trusted automatically. Decisions and action items pass through the validator before storage.

## Backend Components

### `main.py`

Coordinates API workflows.

It exposes routes for:

```text
GET /health
POST /meetings
GET /meetings
GET /meetings/{meeting_id}
PATCH /action-items/{action_item_id}
GET /meetings/{meeting_id}/export
POST /meetings/audio
POST /webhooks/recording-completed
```

It should coordinate work, not hide all business logic inside one giant function.

### `database.py`

Defines:

```text
DATABASE_URL
engine
SessionLocal
Base
get_db
```

This gives the rest of the backend a consistent way to use SQLite through SQLAlchemy.

### `models.py`

Defines database tables:

```text
Meeting
TranscriptSegment
MeetingSummary
ActionItem
```

`Meeting` is the parent record. Transcript segments, one summary, and many action items point back to a meeting with `meeting_id`.

### `schemas.py`

Defines API request and response contracts.

Models describe database storage. Schemas describe what the API accepts and returns.

## Service Layer

### Summarizer

`summarizer.py` exposes:

```text
summarize_transcript(transcript_text)
```

It tries Gemini when `GEMINI_API_KEY` is configured, then falls back to the mock summarizer if Gemini is unavailable, invalid, or returns unusable output.

The rest of the app calls the same function whether the result comes from Gemini or the mock fallback.

### Validator

`validator.py` is the trust layer.

It checks:

```text
task is present
evidence_quote is present
evidence_quote appears in transcript
missing owner becomes Unassigned
missing due date becomes Not specified
missing priority becomes medium
```

Unsupported decisions or action items are rejected.

### Exporter

`exporter.py` converts stored meeting data into Markdown.

It includes:

```text
title
executive summary
decisions
risks
follow-up questions
action item table
evidence quotes
```

### Transcription

`transcription.py` is a placeholder abstraction.

It currently returns sample transcript text after confirming the saved audio file exists. A real transcription provider can be added later behind the same service boundary.

## Database Model

```text
Meeting
  id
  title
  participants
  source_type
  status
  error_message
  created_at
  processed_at

TranscriptSegment
  id
  meeting_id
  speaker
  start_time
  end_time
  text

MeetingSummary
  id
  meeting_id
  executive_summary
  key_decisions_json
  risks_json
  follow_up_questions_json
  created_at

ActionItem
  id
  meeting_id
  owner
  task
  due_date
  priority
  status
  evidence_quote
  confidence
  created_at
```

Lists such as decisions and risks are stored as JSON text fields for the MVP. This keeps the database small and explainable.

## Trust Boundary

The app treats these inputs as untrusted:

```text
pasted transcripts
uploaded files
webhook payloads
Gemini output
mock or future LLM output
```

Validation happens after summarization and before storing extracted decisions and action items.

The central rule is:

```text
Do not store important extracted claims as reliable output unless they include transcript evidence.
```

## Optional Audio Upload Flow

```text
User uploads audio
-> POST /meetings/audio validates extension
-> Backend saves file with generated filename
-> TranscriptionService returns transcript text
-> Existing summarization workflow runs
```

This is a skeleton, not real speech-to-text integration.

## Simulated Webhook Flow

```text
External-like event
-> POST /webhooks/recording-completed
-> Backend creates meeting with source_type webhook:<platform>
-> Transcript is processed if present
-> Existing summarization workflow runs
```

This demonstrates event-driven design without real Zoom or Teams OAuth.

## Frontend Components

The current frontend is intentionally small:

```text
frontend/src/api.js
frontend/src/App.jsx
```

`api.js` centralizes calls to backend endpoints.

`App.jsx` is a single MVP screen for creating meetings, viewing details, updating action items, and exporting Markdown.

The Vite package setup is still future work.

## Testing Strategy

Backend tests cover:

```text
API workflows
validator rules
summarizer fallback
export formatting
simulated webhook creation
```

The API tests use an in-memory SQLite database and a deterministic fake summarizer so tests avoid writing to the local database or calling Gemini.

## Key Tradeoffs

- SQLite instead of PostgreSQL keeps local setup simple.
- Mock fallback keeps the app usable without AI credentials.
- Gemini JSON mode plus Python normalization is used for MVP reliability.
- JSON text fields avoid extra summary child tables early.
- Audio and webhook features are skeletons, not production integrations.
- The frontend is kept simple and single-screen for explainability.

## Production Changes

In production, this architecture would likely need:

- authentication and authorization
- real transcription provider
- webhook signature verification
- background jobs for long-running audio processing
- PostgreSQL
- database migrations
- structured logging without sensitive transcript content
- cloud deployment
- stronger monitoring and retry behavior
