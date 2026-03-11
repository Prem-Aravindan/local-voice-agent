"""SQLAlchemy ORM models for the voice clone agent."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Voice(Base):
    """Represents a cloned voice profile."""

    __tablename__ = "voices"

    voice_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    embedding_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    samples_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("pending", "ready", "failed", name="voice_status"),
        default="pending",
        nullable=False,
    )

    recordings: Mapped[list[Recording]] = relationship(
        "Recording", back_populates="voice", cascade="all, delete-orphan"
    )
    training_jobs: Mapped[list[TrainingJob]] = relationship(
        "TrainingJob", back_populates="voice", cascade="all, delete-orphan"
    )
    generated_audios: Mapped[list[GeneratedAudio]] = relationship(
        "GeneratedAudio", back_populates="voice", cascade="all, delete-orphan"
    )


class Recording(Base):
    """Individual audio recording sample tied to a Voice."""

    __tablename__ = "recordings"

    recording_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    voice_id: Mapped[str] = mapped_column(ForeignKey("voices.voice_id"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    section: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    voice: Mapped[Voice] = relationship("Voice", back_populates="recordings")


class TrainingJob(Base):
    """Background job that builds a voice embedding from recordings."""

    __tablename__ = "training_jobs"

    job_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    voice_id: Mapped[str] = mapped_column(ForeignKey("voices.voice_id"), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("queued", "running", "done", "failed", name="job_status"),
        default="queued",
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    voice: Mapped[Voice] = relationship("Voice", back_populates="training_jobs")


class GeneratedAudio(Base):
    """Audio file produced by the TTS engine for a given voice."""

    __tablename__ = "generated_audios"

    audio_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    voice_id: Mapped[str] = mapped_column(ForeignKey("voices.voice_id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    speed: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    voice: Mapped[Voice] = relationship("Voice", back_populates="generated_audios")
