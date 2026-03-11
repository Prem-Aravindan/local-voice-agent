"""REST API router: audio file download."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.services.tts_service import TTSService

router = APIRouter(prefix="/audio", tags=["audio"])


@router.get("/{audio_id}")
def download_audio(audio_id: str, db: Session = Depends(get_db)) -> FileResponse:
    """Download the WAV file for a previously generated audio clip."""
    audio = TTSService.get_audio(db, audio_id)
    if audio is None:
        raise HTTPException(status_code=404, detail="Audio not found.")

    from pathlib import Path

    path = Path(audio.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file missing from disk.")

    return FileResponse(
        path=str(path),
        media_type="audio/wav",
        filename=f"{audio_id}.wav",
    )
