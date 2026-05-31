# Critical Functions Walkthrough

This document explains the most important functions in the project block by block.

It is written for interview preparation, not as a replacement for reading the code.

## `create_meeting`

File: `backend/app/main.py`

### What It Does

Creates a meeting from pasted transcript text.

### Block-by-Block Explanation

It receives a `MeetingCreateRequest`, so FastAPI and Pydantic validate that the title and transcript text are present.

It calls `_create_meeting_shell` with `source_type="paste"` and `status="processing"` to create the parent meeting row.

It calls `_store_transcript_segment` to save the transcript text connected to the meeting ID.

It calls `_summarize_and_store_meeting`, which runs summarization, validation, summary storage, action item storage, and response building.

### Why It Exists

This is the main transcript-to-meeting workflow.

### What Breaks If Removed

The core pasted transcript flow disappears, and the frontend cannot create normal meetings.

### Possible Alternative

The route could contain all logic inline, but helper functions keep shared workflows reusable for audio upload and webhooks.

### Interview Explanation

`create_meeting` accepts pasted transcript input, creates a meeting row, stores the transcript, and reuses the shared summarization workflow to return a complete meeting detail response.

## `_summarize_and_store_meeting`

File: `backend/app/main.py`

### What It Does

Runs the transcript through summarization and validation, then stores the summary and action items.

### Block-by-Block Explanation

It calls `summarize_transcript` with transcript text.

It validates decisions with `validate_decisions`.

It validates action items with `validate_action_items`.

It creates a `MeetingSummary` row with executive summary, decisions, risks, and follow-up questions.

It loops through validated action items and creates `ActionItem` rows.

It sets the meeting status to `completed` and records `processed_at`.

If an exception happens, it stores `summary_failed` and the error message.

### Why It Exists

It keeps the shared processing workflow in one place.

Pasted transcript creation, audio upload, and webhook creation can all reuse it.

### What Breaks If Removed

Each creation route would need to duplicate summarization, validation, and storage logic.

### Possible Alternative

Move this function to a dedicated service module later if `main.py` grows too large.

### Interview Explanation

`_summarize_and_store_meeting` is the core backend processing pipeline: summarize, validate evidence, store structured results, and mark the meeting completed or failed.

## `get_meetings`

File: `backend/app/main.py`

### What It Does

Returns saved meetings ordered by newest first.

### Block-by-Block Explanation

It receives a database session through FastAPI dependency injection.

It queries the `Meeting` table.

It orders by `created_at.desc()`.

It returns the list using the `MeetingListItem` response schema.

### Why It Exists

The frontend needs a lightweight meeting list for browsing.

### What Breaks If Removed

The dashboard cannot show previously created meetings.

### Possible Alternative

Add pagination later if the list becomes large.

### Interview Explanation

`get_meetings` provides a lightweight newest-first meeting list without returning every summary and action item.

## `get_meeting`

File: `backend/app/main.py`

### What It Does

Returns one full meeting detail by ID.

### Block-by-Block Explanation

It looks up the meeting using `db.get`.

If no meeting exists, it raises a 404 error.

If the meeting exists, it returns `_build_meeting_detail`.

### Why It Exists

The frontend needs full meeting details when a user selects one meeting.

### What Breaks If Removed

Users could create and list meetings but not open the full summary and action items.

### Possible Alternative

Use eager loading for related records if performance becomes an issue.

### Interview Explanation

`get_meeting` retrieves one meeting safely, handles the not-found case with 404, and returns the full detail response.

## `update_action_item`

File: `backend/app/main.py`

### What It Does

Updates editable fields on one action item.

### Block-by-Block Explanation

It looks up the action item by ID.

If it does not exist, it returns 404.

If status is provided, it allows only `open` or `done`.

It updates only fields present in the request.

It normalizes empty owner, due date, and priority values.

It commits and returns the updated action item.

### Why It Exists

Action items represent work, so users need to mark them done or adjust small details.

### What Breaks If Removed

The app becomes a static summarizer instead of a workflow tool.

### Possible Alternative

Use stricter enum schemas for status and priority.

### Interview Explanation

`update_action_item` lets the user update part of an action item while preventing invalid status values and preserving clear defaults.

## `export_meeting`

File: `backend/app/main.py`

### What It Does

Returns Markdown export for one meeting.

### Block-by-Block Explanation

It looks up the meeting by ID.

It returns 404 if the meeting does not exist.

It calls `export_meeting_markdown` with the meeting, summary, and action items.

It returns `ExportResponse`.

### Why It Exists

Users need to reuse meeting notes outside the app.

### What Breaks If Removed

The Markdown export feature disappears.

### Possible Alternative

Return `text/markdown` directly instead of wrapping Markdown in JSON.

### Interview Explanation

`export_meeting` keeps route logic small by fetching the meeting and delegating formatting to the exporter service.

## `summarize_transcript`

File: `backend/app/services/summarizer.py`

### What It Does

Returns structured meeting notes from transcript text.

### Block-by-Block Explanation

It loads local environment variables.

It checks for `GEMINI_API_KEY`.

If the key is missing, it returns mock output.

If the key exists, it tries `_summarize_with_gemini`.

If Gemini fails or returns invalid JSON, it falls back to mock output.

### Why It Exists

The rest of the app needs one stable summarization function.

### What Breaks If Removed

Meeting creation cannot generate summaries or action items.

### Possible Alternative

Define a formal provider interface if the app supports many AI vendors later.

### Interview Explanation

`summarize_transcript` hides provider details behind one function. It tries Gemini when configured and falls back to deterministic mock output when Gemini is unavailable.

## `_summarize_with_gemini`

File: `backend/app/services/summarizer.py`

### What It Does

Calls Gemini's REST API and parses JSON output.

### Block-by-Block Explanation

It reads `GEMINI_MODEL`, defaulting to a Gemini Flash model.

It builds a `generateContent` URL.

It creates a prompt with strict JSON instructions.

It sends a POST request with `responseMimeType` set to `application/json`.

It parses Gemini's returned text as JSON.

It normalizes the summary shape before returning.

### Why It Exists

This is the optional real AI path.

### What Breaks If Removed

The app can still use mock output, but real Gemini summarization is gone.

### Possible Alternative

Use the official Gemini Python SDK instead of REST.

### Interview Explanation

`_summarize_with_gemini` is the provider-specific call. It keeps Gemini details inside the summarizer service while the rest of the app depends only on `summarize_transcript`.

## `validate_action_items`

File: `backend/app/services/validator.py`

### What It Does

Filters and normalizes extracted action items.

### Block-by-Block Explanation

It loops through action items from the summarizer.

It normalizes missing fields using `normalize_action_item`.

It rejects items with no task.

It rejects items whose evidence quote is missing or not found in the transcript.

It returns only valid items.

### Why It Exists

This is the anti-hallucination layer for action items.

### What Breaks If Removed

Unsupported AI-generated tasks could be stored and shown as reliable output.

### Possible Alternative

Use fuzzy evidence matching or transcript segment IDs for stronger production validation.

### Interview Explanation

`validate_action_items` protects the app by accepting only action items with a task and transcript-supported evidence.

## `validate_decisions`

File: `backend/app/services/validator.py`

### What It Does

Filters extracted decisions based on evidence support.

### Block-by-Block Explanation

It reads decision text and evidence quote.

It skips empty decisions.

It checks whether the evidence quote appears in the transcript.

It returns only supported decisions.

### Why It Exists

Decisions can affect real business work, so they need source support.

### What Breaks If Removed

The app could store unsupported decisions from AI output.

### Possible Alternative

Store rejected decisions separately for review instead of dropping them.

### Interview Explanation

`validate_decisions` applies the same evidence-backed trust rule to decisions that `validate_action_items` applies to tasks.

## `export_meeting_markdown`

File: `backend/app/services/exporter.py`

### What It Does

Formats one meeting's stored data as Markdown.

### Block-by-Block Explanation

It creates headings for title, summary, decisions, risks, questions, and action items.

It parses JSON text fields for decisions, risks, and questions.

It builds a Markdown action item table.

It includes evidence quotes below action items.

It returns one Markdown string.

### Why It Exists

Export makes meeting notes useful outside the app.

### What Breaks If Removed

Users cannot easily reuse the generated notes in email, docs, or collaboration tools.

### Possible Alternative

Use a template file if formatting becomes more complex.

### Interview Explanation

`export_meeting_markdown` keeps Markdown formatting separate from API routes and preserves evidence quotes in the exported notes.

## `create_meeting_from_audio`

File: `backend/app/main.py`

### What It Does

Creates a meeting from an uploaded audio file.

### Block-by-Block Explanation

It accepts title, participants, and uploaded file.

It validates the file extension.

It saves the file with a generated filename.

It creates a meeting with source type `audio_upload`.

It calls `TranscriptionService`.

It stores transcript text and reuses the shared summarization workflow.

### Why It Exists

It demonstrates how audio upload could enter the same meeting workflow.

### What Breaks If Removed

The app still works for pasted transcripts, but optional audio upload disappears.

### Possible Alternative

Move file storage and transcription orchestration into a dedicated service.

### Interview Explanation

`create_meeting_from_audio` safely accepts limited audio types, stores the file without trusting the original filename, transcribes through a service abstraction, and reuses the transcript workflow.

## `recording_completed_webhook`

File: `backend/app/main.py`

### What It Does

Creates a meeting from a simulated recording-completed webhook payload.

### Block-by-Block Explanation

It accepts a small webhook request schema.

It creates a meeting with source type `webhook:<platform>`.

It uses transcript text from the request or a sample fallback.

It stores the transcript segment.

It reuses the shared summarization workflow.

### Why It Exists

It demonstrates event-driven meeting creation without real Zoom or Teams integration.

### What Breaks If Removed

The optional webhook demo path disappears.

### Possible Alternative

Implement real webhook signature verification and provider-specific payload parsing.

### Interview Explanation

`recording_completed_webhook` shows how a platform event could trigger meeting processing while keeping the MVP free of real OAuth and webhook infrastructure.
