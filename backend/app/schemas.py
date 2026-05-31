from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MeetingCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    participants: str | None = None
    transcript_text: str = Field(min_length=1)


class RecordingCompletedWebhookRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    source_platform: str = Field(default="simulated", max_length=50)
    recording_url: str | None = None
    transcript_text: str | None = None


class ActionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner: str
    task: str
    due_date: str
    priority: str
    status: str
    evidence_quote: str
    confidence: float
    created_at: datetime


class ActionItemUpdateRequest(BaseModel):
    owner: str | None = None
    due_date: str | None = None
    priority: str | None = None
    status: str | None = None


class SummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    executive_summary: str
    key_decisions: list[dict[str, str]]
    risks: list[dict[str, str]]
    follow_up_questions: list[str]
    created_at: datetime


class MeetingListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    participants: str | None
    source_type: str
    status: str
    created_at: datetime
    processed_at: datetime | None


class MeetingDetailResponse(MeetingListItem):
    error_message: str | None
    summary: SummaryResponse | None
    action_items: list[ActionItemResponse]


class ExportResponse(BaseModel):
    meeting_id: int
    markdown: str
