# Interview Defense

## 1. Why This Problem?

Meeting notes are useful only when they are accurate and actionable.

A normal AI summary can sound confident while inventing ownership, deadlines, or decisions. This project focuses on trustworthy meeting notes by requiring important decisions and action items to include evidence quotes from the transcript.

## 2. What Is the Core Value?

The core value is converting raw meeting transcripts into structured notes:

- executive summary
- key decisions
- risks
- follow-up questions
- action items

The differentiator is evidence-backed output. The app does not blindly trust AI output.

## 3. Why FastAPI?

FastAPI is lightweight, readable, and good for building APIs quickly.

It also gives automatic docs at `/docs`, which makes the backend easy to test and explain during a demo.

## 4. Why React?

React is useful because the UI has changing state:

- form input
- meeting list
- selected meeting detail
- action item status
- exported Markdown

For the MVP, a single-screen React UI keeps the frontend explainable.

## 5. Why SQLite?

SQLite keeps local setup simple.

The MVP does not need a separate database server. SQLite is enough to demonstrate meeting storage, summaries, action items, and exports.

In production, I would consider PostgreSQL for concurrency, backups, migrations, and operational reliability.

## 6. Why SQLAlchemy?

SQLAlchemy gives explicit database models and relationships in Python.

It lets the backend model meetings, transcript segments, summaries, and action items as Python classes while storing them in relational tables.

## 7. Why Pydantic Schemas?

Schemas define the API contract.

Database models describe how data is stored. Pydantic schemas describe what requests and responses look like.

They also validate untrusted input before the backend processes it.

## 8. Why Mock First?

Mock summarization makes the workflow deterministic.

Before adding real AI, I wanted to prove:

- meeting creation works
- database storage works
- validation works
- action item updates work
- export works
- tests work

That avoids debugging API keys, network failures, invalid JSON, and model behavior at the same time as backend logic.

## 9. Why Gemini With Fallback?

Gemini gives a real AI path when `GEMINI_API_KEY` is configured.

But the app should still work without credentials or network access, so the summarizer falls back to mock output when Gemini is missing or fails.

This makes the app easier to run locally and safer to demo.

## 10. Why Evidence Quotes?

Evidence quotes are the trust feature.

If the app says someone owns a task, the user should be able to see the transcript sentence that supports it.

That reduces hallucination risk and makes the output easier to verify.

## 11. What If Gemini Fails?

The summarizer catches expected Gemini and parsing failures and falls back to the mock summarizer.

This means the meeting workflow can still complete locally even if:

- the API key is missing
- the network is unavailable
- Gemini returns invalid JSON
- the response shape is unexpected

## 12. What If Gemini Invents an Action Item?

The validator checks whether the evidence quote appears in the original transcript.

Unsupported action items and decisions are rejected before storage.

This is the anti-hallucination layer.

## 13. What If the Transcript Is Wrong?

The app can only validate against the transcript it receives.

If the transcript itself is wrong, the app may still produce evidence-backed output from bad source text.

In production, I would expose transcript review/editing and possibly regenerate summaries after transcript correction.

## 14. What If an Action Item Has No Owner?

The validator normalizes missing owner to:

```text
Unassigned
```

This keeps the action item visible instead of dropping useful work just because ownership was unclear.

## 15. What If a Due Date Is Missing?

The validator normalizes missing due date to:

```text
Not specified
```

That is clearer than guessing a date.

## 16. Why Not Real Zoom OAuth in the MVP?

Real Zoom integration adds OAuth, webhook verification, public URLs, permissions, and platform-specific setup.

That would distract from the core value: transcript-to-evidence-backed-notes.

The simulated webhook shows the event-driven shape without the full integration burden.

## 17. Why Audio Upload Is Only a Skeleton?

File upload is riskier than pasted text.

The app validates allowed extensions, stores files with generated names, and uses a transcription abstraction.

Real transcription can be added later behind that abstraction.

## 18. Why Store Decisions and Risks as JSON Text?

For the MVP, JSON text fields keep the database smaller and easier to explain.

Action items have their own table because users update their status.

In production, decisions and risks could become separate tables if they need filtering, editing, or detailed tracking.

## 19. What Are the Main Failure Modes?

- Missing Gemini key: mock fallback.
- Gemini bad response: mock fallback.
- Unsupported evidence: reject item.
- Missing meeting ID: 404.
- Invalid action status: validation error.
- Bad audio extension: reject upload.
- Transcription failure: save meeting with failure status.

## 20. What Would Change in Production?

I would add:

- authentication
- authorization
- PostgreSQL
- database migrations
- real transcription provider
- webhook signature verification
- background jobs for audio processing
- structured logging without sensitive content
- monitoring and retry policies
- deployment documentation

## 21. How Would You Add Owner Filtering Live?

I would add a small endpoint:

```text
GET /meetings/{meeting_id}/action-items?owner=Abhishek
```

Then query action items for that meeting and apply an owner filter if provided.

This is a good live feature because it is small, useful, and uses the existing data model.

## 22. What Would You Cut If Time Was Reduced?

I would cut audio upload and simulated webhook first.

The core MVP is:

```text
paste transcript -> summarize -> validate evidence -> store -> view -> mark done -> export
```

That is the main value path.

## 23. How Did You Use AI Responsibly?

The project treats AI output as untrusted.

It uses:

- mock fallback
- strict prompt instructions
- JSON parsing
- normalization
- evidence validation
- safe environment variables
- no hardcoded secrets

The app does not present unsupported AI output as reliable meeting truth.

## 24. One-Minute Project Explanation

This is an AI meeting summarizer that converts transcripts into structured notes and action items. The important design choice is that action items and decisions must include evidence quotes from the original transcript. The backend uses FastAPI, SQLite, SQLAlchemy, Pydantic schemas, a Gemini-or-mock summarizer, and a validator that rejects unsupported claims. The app can create meetings, retrieve them, update action item status, export Markdown, and demonstrate optional audio and webhook flows.
