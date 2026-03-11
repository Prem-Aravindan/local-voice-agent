"""Service layer: text-to-speech synthesis."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import GENERATED_DIR, TTS_DEVICE, TTS_MODEL_NAME
from app.models.db_models import GeneratedAudio
from voice_engine.tts_engine import TTSEngine

logger = logging.getLogger(__name__)

_engine = TTSEngine(model_name=TTS_MODEL_NAME, device=TTS_DEVICE)


class TTSService:
    """Orchestrates TTS generation and persists metadata."""

    @staticmethod
    def generate(
        db: Session,
        voice_id: str,
        embedding_path: str,
        text: str,
        speed: float = 1.0,
        temperature: float = 0.7,
        language: str = "en",
    ) -> GeneratedAudio:
        """Generate speech and return the persisted :class:`GeneratedAudio` record."""
        audio_id = str(uuid.uuid4())
        out_dir = GENERATED_DIR / voice_id
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"{audio_id}.wav"

        _engine.generate(
            text=text,
            embedding_path=Path(embedding_path),
            output_path=output_path,
            language=language,
            speed=speed,
            temperature=temperature,
        )

        record = GeneratedAudio(
            audio_id=audio_id,
            voice_id=voice_id,
            text=text,
            file_path=str(output_path),
            speed=speed,
            temperature=temperature,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        logger.info("Audio %s generated at %s", audio_id, output_path)
        return record

    @staticmethod
    def get_audio(db: Session, audio_id: str) -> GeneratedAudio | None:
        return db.get(GeneratedAudio, audio_id)
