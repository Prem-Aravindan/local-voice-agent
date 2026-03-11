"""Service layer: voice lifecycle management."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import EMBEDDINGS_DIR, RECORDINGS_DIR, VOICES_DIR
from app.models.db_models import Recording, TrainingJob, Voice

logger = logging.getLogger(__name__)


class VoiceService:
    """Business logic for creating and managing voice profiles."""

    # ------------------------------------------------------------------
    # CRUD helpers
    # ------------------------------------------------------------------

    @staticmethod
    def create_voice(db: Session, name: str, description: str | None = None) -> Voice:
        """Create a new Voice record and initialise its directory layout."""
        voice_id = str(uuid.uuid4())
        voice_dir = VOICES_DIR / voice_id
        samples_path = voice_dir / "samples"
        samples_path.mkdir(parents=True, exist_ok=True)

        voice = Voice(
            voice_id=voice_id,
            name=name,
            description=description,
            samples_path=str(samples_path),
        )
        db.add(voice)
        db.commit()
        db.refresh(voice)

        # Persist metadata alongside the audio files
        _write_metadata(voice)
        return voice

    @staticmethod
    def get_voice(db: Session, voice_id: str) -> Voice | None:
        return db.get(Voice, voice_id)

    @staticmethod
    def get_voice_by_name(db: Session, name: str) -> Voice | None:
        return db.query(Voice).filter(Voice.name == name).first()

    @staticmethod
    def list_voices(db: Session) -> list[Voice]:
        return db.query(Voice).order_by(Voice.created_at.desc()).all()

    @staticmethod
    def delete_voice(db: Session, voice_id: str) -> bool:
        voice = db.get(Voice, voice_id)
        if voice is None:
            return False
        db.delete(voice)
        db.commit()
        return True

    # ------------------------------------------------------------------
    # Recording helpers
    # ------------------------------------------------------------------

    @staticmethod
    def add_recording(
        db: Session,
        voice_id: str,
        file_path: str,
        duration_seconds: float | None = None,
        section: str | None = None,
    ) -> Recording:
        recording = Recording(
            voice_id=voice_id,
            file_path=file_path,
            duration_seconds=duration_seconds,
            section=section,
        )
        db.add(recording)
        db.commit()
        db.refresh(recording)
        return recording

    @staticmethod
    def list_recordings(db: Session, voice_id: str) -> list[Recording]:
        return (
            db.query(Recording)
            .filter(Recording.voice_id == voice_id)
            .order_by(Recording.created_at)
            .all()
        )

    # ------------------------------------------------------------------
    # Training job helpers
    # ------------------------------------------------------------------

    @staticmethod
    def create_training_job(db: Session, voice_id: str) -> TrainingJob:
        job = TrainingJob(voice_id=voice_id)
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def update_job_status(
        db: Session,
        job_id: str,
        status: str,
        error_message: str | None = None,
    ) -> TrainingJob | None:
        job = db.get(TrainingJob, job_id)
        if job is None:
            return None
        job.status = status
        if error_message is not None:
            job.error_message = error_message
        if status in ("done", "failed"):
            job.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def set_embedding_path(db: Session, voice_id: str, embedding_path: str) -> Voice | None:
        voice = db.get(Voice, voice_id)
        if voice is None:
            return None
        voice.embedding_path = embedding_path
        voice.status = "ready"
        db.commit()
        db.refresh(voice)
        _write_metadata(voice)
        return voice


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _write_metadata(voice: Voice) -> None:
    """Write a metadata.json file next to the voice's sample directory."""
    voice_dir = VOICES_DIR / voice.voice_id
    voice_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "voice_id": voice.voice_id,
        "name": voice.name,
        "description": voice.description,
        "created_at": voice.created_at.isoformat() if voice.created_at else None,
        "status": voice.status,
        "embedding_path": voice.embedding_path,
        "samples_path": voice.samples_path,
    }
    (voice_dir / "metadata.json").write_text(json.dumps(meta, indent=2))
