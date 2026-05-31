from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    participants: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), default="paste", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="created", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    transcript_segments: Mapped[list["TranscriptSegment"]] = relationship(
        back_populates="meeting",
        cascade="all, delete-orphan",
    )
    summary: Mapped["MeetingSummary | None"] = relationship(
        back_populates="meeting",
        cascade="all, delete-orphan",
        uselist=False,
    )
    action_items: Mapped[list["ActionItem"]] = relationship(
        back_populates="meeting",
        cascade="all, delete-orphan",
    )


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    speaker: Mapped[str | None] = mapped_column(String(100), nullable=True)
    start_time: Mapped[str | None] = mapped_column(String(50), nullable=True)
    end_time: Mapped[str | None] = mapped_column(String(50), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    meeting: Mapped[Meeting] = relationship(back_populates="transcript_segments")


class MeetingSummary(Base):
    __tablename__ = "meeting_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"), nullable=False, unique=True)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_decisions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    risks_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    follow_up_questions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    meeting: Mapped[Meeting] = relationship(back_populates="summary")


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    owner: Mapped[str] = mapped_column(String(100), default="Unassigned", nullable=False)
    task: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[str] = mapped_column(String(100), default="Not specified", nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    evidence_quote: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    meeting: Mapped[Meeting] = relationship(back_populates="action_items")
