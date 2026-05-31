import json
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import Depends
from fastapi import File
from fastapi import FastAPI
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import models
from .database import Base, engine, get_db
from .schemas import (
    ActionItemResponse,
    ActionItemUpdateRequest,
    ExportResponse,
    MeetingCreateRequest,
    MeetingDetailResponse,
    MeetingListItem,
    RecordingCompletedWebhookRequest,
    SummaryResponse,
)
from .services.exporter import export_meeting_markdown
from .services.summarizer import summarize_transcript
from .services.transcription import TranscriptionService
from .services.validator import validate_action_items, validate_decisions


# Defines which audio file types the upload endpoint will accept.
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a"}
# Points to the backend/uploads folder where uploaded audio files are stored.
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"

# Creates the FastAPI application object that Uvicorn runs and routes attach to.
app = FastAPI(title="AI Meeting Summarizer API")

# Adds request/response middleware to let the local frontend call this backend.
app.add_middleware(
    # Uses FastAPI's CORS middleware to control which browser origins can call the API.
    CORSMiddleware,
    # Lists the frontend origins that browsers may use to call this API.
    allow_origins=[
        # Allows the Vite frontend when it runs on localhost port 5173.
        "http://localhost:5173",
        # Allows the same local frontend when it is opened through 127.0.0.1.
        "http://127.0.0.1:5173",
    ],
    # Allows approved browser requests to include credentials such as cookies or auth headers.
    allow_credentials=True,
    # Allows the approved frontend to use any HTTP method, such as GET, POST, or PATCH.
    allow_methods=["*"],
    # Allows the approved frontend to send headers such as Content-Type.
    allow_headers=["*"],
)  # Finishes the CORS middleware configuration.


# Runs the function below automatically when the FastAPI app starts.
@app.on_event("startup")
# Defines the startup task that prepares database tables before requests are handled.
def create_database_tables() -> None:
    # Creates any missing tables from the SQLAlchemy model definitions.
    Base.metadata.create_all(bind=engine)


# Registers a simple GET endpoint used to confirm the backend is running.
@app.get("/health")
# Handles the health-check request and returns a small status dictionary.
def health_check() -> dict[str, str]:
    # Returns a minimal JSON-ready response proving the API process is reachable.
    return {"status": "ok"}


# Registers a GET endpoint that returns a list of saved meetings.
@app.get("/meetings", response_model=list[MeetingListItem])
# Handles the meeting-list request and receives a database session from FastAPI.
def get_meetings(db: Session = Depends(get_db)) -> list[models.Meeting]:
    # Fetches every meeting from the database with the newest meetings first.
    return db.query(models.Meeting).order_by(models.Meeting.created_at.desc()).all()


# Registers a GET endpoint that returns full details for one meeting by ID.
@app.get("/meetings/{meeting_id}", response_model=MeetingDetailResponse)
# Handles the meeting-detail request; parameters are split across lines for readability.
def get_meeting(
    # Gets the numeric meeting ID from the URL path, such as /meetings/7.
    meeting_id: int,
    # Receives a database session from FastAPI's get_db dependency.
    db: Session = Depends(get_db),
# Declares that this endpoint returns the full meeting-detail response shape.
) -> MeetingDetailResponse:
    # Looks up the requested meeting by its primary key ID.
    meeting = db.get(models.Meeting, meeting_id)
    # If no matching meeting exists, return a clear 404 error instead of crashing.
    if meeting is None:
        # Sends a standard HTTP 404 response when the requested meeting ID is missing.
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Converts the found meeting model into the full API detail response.
    return _build_meeting_detail(meeting)


# Registers a GET endpoint that exports one meeting's notes as Markdown.
@app.get("/meetings/{meeting_id}/export", response_model=ExportResponse)
# Handles the export request; parameters are split across lines for readability.
def export_meeting(
    # Gets the numeric meeting ID from the export URL path.
    meeting_id: int,
    # Receives a database session so the meeting can be loaded before export.
    db: Session = Depends(get_db),
# Declares that this endpoint returns the structured export response.
) -> ExportResponse:
    # Looks up the meeting that should be exported.
    meeting = db.get(models.Meeting, meeting_id)
    # Stops with a 404 response if the requested meeting does not exist.
    if meeting is None:
        # Sends a standard HTTP 404 response when the requested export target is missing.
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Delegates Markdown formatting to the exporter service helper.
    markdown = export_meeting_markdown(
        meeting=meeting,
        summary=meeting.summary,
        action_items=meeting.action_items,
    )
    return ExportResponse(meeting_id=meeting.id, markdown=markdown)


@app.get("/meetings/{meeting_id}/action-items", response_model=list[ActionItemResponse])
def get_meeting_action_items(
    meeting_id: int,
    owner: str | None = None,
    db: Session = Depends(get_db),
) -> list[ActionItemResponse]:
    meeting = db.get(models.Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")

    query = db.query(models.ActionItem).filter(models.ActionItem.meeting_id == meeting_id)
    if owner:
        query = query.filter(models.ActionItem.owner.ilike(owner.strip()))

    return [
        ActionItemResponse.model_validate(action_item)
        for action_item in query.order_by(models.ActionItem.created_at.asc()).all()
    ]


@app.patch("/action-items/{action_item_id}", response_model=ActionItemResponse)
def update_action_item(
    action_item_id: int,
    request: ActionItemUpdateRequest,
    db: Session = Depends(get_db),
) -> ActionItemResponse:
    action_item = db.get(models.ActionItem, action_item_id)
    if action_item is None:
        raise HTTPException(status_code=404, detail="Action item not found")

    if request.status is not None:
        status = request.status.strip().lower()
        if status not in {"open", "done"}:
            raise HTTPException(
                status_code=400,
                detail="Status must be either 'open' or 'done'",
            )
        action_item.status = status

    if request.owner is not None:
        action_item.owner = request.owner.strip() or "Unassigned"

    if request.due_date is not None:
        action_item.due_date = request.due_date.strip() or "Not specified"

    if request.priority is not None:
        action_item.priority = request.priority.strip().lower() or "medium"

    db.commit()
    db.refresh(action_item)
    return ActionItemResponse.model_validate(action_item)


@app.post("/meetings", response_model=MeetingDetailResponse)
def create_meeting(
    request: MeetingCreateRequest,
    db: Session = Depends(get_db),
) -> MeetingDetailResponse:
    meeting = _create_meeting_shell(
        db=db,
        title=request.title,
        participants=request.participants,
        source_type="paste",
        status="processing",
    )
    _store_transcript_segment(db, meeting.id, request.transcript_text)
    return _summarize_and_store_meeting(db, meeting, request.transcript_text)


@app.post("/meetings/audio", response_model=MeetingDetailResponse)
async def create_meeting_from_audio(
    title: str = Form(...),
    participants: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> MeetingDetailResponse:
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Audio file must be .mp3, .wav, or .m4a",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    saved_audio_path = UPLOAD_DIR / f"{uuid4().hex}{extension}"

    with saved_audio_path.open("wb") as output_file:
        shutil.copyfileobj(file.file, output_file)
    await file.close()

    meeting = _create_meeting_shell(
        db=db,
        title=title,
        participants=participants,
        source_type="audio_upload",
        status="uploaded",
    )

    try:
        meeting.status = "transcribing"
        db.commit()

        transcript_text = TranscriptionService().transcribe(saved_audio_path)
        _store_transcript_segment(db, meeting.id, transcript_text)

        meeting.status = "summarizing"
        db.commit()
        return _summarize_and_store_meeting(db, meeting, transcript_text)
    except Exception as exc:
        meeting.status = "summary_failed"
        meeting.error_message = str(exc)
        db.commit()
        db.refresh(meeting)
        return _build_meeting_detail(meeting)


@app.post("/webhooks/recording-completed", response_model=MeetingDetailResponse)
def recording_completed_webhook(
    request: RecordingCompletedWebhookRequest,
    db: Session = Depends(get_db),
) -> MeetingDetailResponse:
    meeting = _create_meeting_shell(
        db=db,
        title=request.title,
        participants=None,
        source_type=f"webhook:{request.source_platform}",
        status="received",
    )

    transcript_text = request.transcript_text or (
        "Neha: Abhishek, please create the first working POC by Friday. "
        "Jeevan, please validate the logging fields by Wednesday."
    )
    _store_transcript_segment(db, meeting.id, transcript_text)

    meeting.status = "summarizing"
    db.commit()
    return _summarize_and_store_meeting(db, meeting, transcript_text)


def _create_meeting_shell(
    db: Session,
    title: str,
    participants: str | None,
    source_type: str,
    status: str,
) -> models.Meeting:
    meeting = models.Meeting(
        title=title,
        participants=participants,
        source_type=source_type,
        status=status,
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting


def _store_transcript_segment(db: Session, meeting_id: int, transcript_text: str) -> None:
    transcript_segment = models.TranscriptSegment(
        meeting_id=meeting_id,
        speaker=None,
        start_time=None,
        end_time=None,
        text=transcript_text,
    )
    db.add(transcript_segment)
    db.commit()


def _summarize_and_store_meeting(
    db: Session,
    meeting: models.Meeting,
    transcript_text: str,
) -> MeetingDetailResponse:
    try:
        summarized = summarize_transcript(transcript_text)
        decisions = validate_decisions(
            summarized.get("key_decisions", []),
            transcript_text,
        )
        action_items = validate_action_items(
            summarized.get("action_items", []),
            transcript_text,
        )

        summary = models.MeetingSummary(
            meeting_id=meeting.id,
            executive_summary=summarized.get("executive_summary", ""),
            key_decisions_json=json.dumps(decisions),
            risks_json=json.dumps(summarized.get("risks", [])),
            follow_up_questions_json=json.dumps(
                summarized.get("follow_up_questions", [])
            ),
        )
        db.add(summary)

        for action_item in action_items:
            db.add(
                models.ActionItem(
                    meeting_id=meeting.id,
                    owner=action_item["owner"],
                    task=action_item["task"],
                    due_date=action_item["due_date"],
                    priority=action_item["priority"],
                    status=action_item["status"],
                    evidence_quote=action_item["evidence_quote"],
                    confidence=action_item["confidence"],
                )
            )

        meeting.status = "completed"
        meeting.processed_at = datetime.utcnow()
        db.commit()
    except Exception as exc:
        meeting.status = "summary_failed"
        meeting.error_message = str(exc)
        db.commit()

    db.refresh(meeting)
    return _build_meeting_detail(meeting)


# Converts a Meeting database model into the full response object used by detail-style endpoints.
def _build_meeting_detail(meeting: models.Meeting) -> MeetingDetailResponse:
    # Starts with no summary so failed or still-processing meetings can still return safely.
    summary = None
    # If a summary row exists for this meeting, convert it into the API summary shape.
    if meeting.summary:
        # Builds the nested summary response returned inside the meeting detail.
        summary = SummaryResponse(
            # Copies the database ID of the meeting summary into the API response.
            id=meeting.summary.id,
            executive_summary=meeting.summary.executive_summary,
            key_decisions=json.loads(meeting.summary.key_decisions_json),
            risks=json.loads(meeting.summary.risks_json),
            follow_up_questions=json.loads(meeting.summary.follow_up_questions_json),
            created_at=meeting.summary.created_at,
        )

    return MeetingDetailResponse(
        id=meeting.id,
        title=meeting.title,
        participants=meeting.participants,
        source_type=meeting.source_type,
        status=meeting.status,
        created_at=meeting.created_at,
        processed_at=meeting.processed_at,
        error_message=meeting.error_message,
        summary=summary,
        # Starts the action-items list that will be included in the meeting detail response.
        action_items=[
            # Converts each stored ActionItem model into the API response schema.
            ActionItemResponse.model_validate(action_item)
            # Repeats that conversion for every action item connected to this meeting.
            for action_item in meeting.action_items
        ],  # Finishes the action-items list.
    )
