# Demo Script

Use this script for a short project walkthrough.

Target length: 8 to 10 minutes.

## 0:00 - 1:00 Problem

Meeting notes are useful only when they are accurate and actionable.

After meetings, teams often need to know:

- what was decided
- who owns each task
- what deadlines were mentioned
- what risks were raised
- what needs follow-up

The hard part is trust. A generic AI summary can sound confident but still invent or misassign action items.

## 1:00 - 2:00 Solution

This project turns meeting transcripts into structured notes.

It extracts:

- executive summary
- key decisions
- risks
- follow-up questions
- action items

The key differentiator is that important decisions and action items include transcript evidence.

Say:

```text
The app does not blindly trust AI output. It checks evidence quotes before storing important extracted items.
```

## 2:00 - 3:30 Architecture

Show `docs/architecture.md`.

Explain the flow:

```text
Frontend
-> FastAPI backend
-> Pydantic schemas
-> SQLAlchemy models
-> SQLite database
-> summarizer
-> validator
-> exporter
```

Point out:

- `main.py` coordinates routes.
- `models.py` defines stored data.
- `schemas.py` defines API contracts.
- `summarizer.py` handles Gemini or mock fallback.
- `validator.py` is the trust layer.
- `exporter.py` creates Markdown.

## 3:30 - 5:30 Main Demo Flow

Use `sample_data/smart_docs_meeting.txt`.

Show the transcript includes clear evidence:

```text
Abhishek, please create the first working POC by Friday.
Jeevan, please validate the logging fields by Wednesday.
The biggest risk is latency.
```

Demo through API docs or TestClient:

```text
POST /meetings
GET /meetings
GET /meetings/{id}
```

Explain that the backend stores the meeting, runs summarization, validates evidence, and returns structured output.

## 5:30 - 6:30 Trust Layer

Open `backend/app/services/validator.py`.

Explain:

```text
Action items need a task.
Evidence quote is required.
Evidence quote must appear in the transcript.
Missing owner becomes Unassigned.
Missing due date becomes Not specified.
```

Say:

```text
This is the anti-hallucination layer. It prevents unsupported AI output from becoming stored reliable data.
```

## 6:30 - 7:15 Action Item Workflow

Show:

```text
PATCH /action-items/{id}
GET /meetings/{id}/action-items?owner=Abhishek
```

Explain:

- action items are not just static summary text
- users can mark work done
- owner filtering is a small useful workflow feature

## 7:15 - 8:00 Export

Show:

```text
GET /meetings/{id}/export
```

Explain that Markdown export makes the notes useful outside the app, such as in email, docs, GitHub issues, or project tools.

Point out that evidence quotes stay visible in the exported notes.

## 8:00 - 8:45 Optional Extensions

Mention:

- audio upload skeleton
- simulated recording-completed webhook

Be honest:

```text
These are MVP skeletons, not production integrations.
```

Explain that they reuse the same transcript workflow after audio transcription or webhook input.

## 8:45 - 9:30 Tests and Verification

Show:

```powershell
cd backend
python -m pytest
```

Current result:

```text
14 passed
```

Explain that tests cover:

- meeting creation
- retrieval
- action item updates
- export
- webhook
- validator
- summarizer fallback

## 9:30 - 10:00 Close

Summarize:

```text
This project is not just an AI summary app. It is a trustworthy meeting workflow app. It stores transcripts, extracts structured notes, validates evidence-backed claims, lets users update action items, and exports useful notes.
```

Future improvements:

- real frontend package setup
- real transcription provider
- authentication
- production database
- webhook verification
- background jobs

End with:

```text
The main engineering decision was to treat AI output as untrusted and validate important claims against the source transcript.
```
