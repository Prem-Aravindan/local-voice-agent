"""REST API router: text-to-speech generation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.services.tts_service import TTSService
from app.services.voice_service import VoiceService

router = APIRouter(prefix="/tts", tags=["tts"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class TTSRequest(BaseModel):
    voice_id: str
    text: str = Field(..., min_length=1, max_length=5000)
    language: str = "en"
    speed: float = Field(default=1.0, ge=0.1, le=3.0)
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)


class TTSResponse(BaseModel):
    audio_id: str
    voice_id: str
    text: str
    file_path: str
    speed: float
    temperature: float
    created_at: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=TTSResponse, status_code=201)
def generate_speech(body: TTSRequest, db: Session = Depends(get_db)) -> TTSResponse:
    """Synthesise speech for *text* using the cloned voice identified by *voice_id*."""
    voice = VoiceService.get_voice(db, body.voice_id)
    if voice is None:
        raise HTTPException(status_code=404, detail="Voice not found.")
    if voice.status != "ready":
        raise HTTPException(
            status_code=422,
            detail=(
                f"Voice '{voice.name}' is not ready (status={voice.status}). "
                "Run POST /voice/{voice_id}/train first."
            ),
        )
    if not voice.embedding_path:
        raise HTTPException(status_code=422, detail="Voice has no embedding yet.")

    audio = TTSService.generate(
        db=db,
        voice_id=body.voice_id,
        embedding_path=voice.embedding_path,
        text=body.text,
        speed=body.speed,
        temperature=body.temperature,
        language=body.language,
    )
    return TTSResponse(
        audio_id=audio.audio_id,
        voice_id=audio.voice_id,
        text=audio.text,
        file_path=audio.file_path,
        speed=audio.speed,
        temperature=audio.temperature,
        created_at=audio.created_at.isoformat(),
    )
