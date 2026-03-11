"""REST API router: voice management and recording."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import RECORDINGS_DIR, RECORDING_PROTOCOL
from app.database.db import get_db
from app.services.voice_service import VoiceService
from app.workers.tasks import build_voice_embedding
from voice_engine.recorder import VoiceRecorder

router = APIRouter(prefix="/voice", tags=["voice"])

# Module-level recorder (one per process; concurrent recording not supported)
_recorder = VoiceRecorder()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class CreateVoiceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None


class VoiceResponse(BaseModel):
    voice_id: str
    name: str
    description: str | None
    status: str
    embedding_path: str | None
    samples_path: str | None
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_voice(cls, v: object) -> "VoiceResponse":
        return cls(
            voice_id=v.voice_id,
            name=v.name,
            description=v.description,
            status=v.status,
            embedding_path=v.embedding_path,
            samples_path=v.samples_path,
            created_at=v.created_at.isoformat(),
        )


class RecordStartRequest(BaseModel):
    voice_id: str
    section: str = "warmup"


class RecordStartResponse(BaseModel):
    voice_id: str
    section: str
    file_path: str
    is_recording: bool
    error: str | None = None


class RecordStopResponse(BaseModel):
    voice_id: str
    section: str
    file_path: str
    duration: float
    error: str | None = None


class TrainingJobResponse(BaseModel):
    job_id: str
    voice_id: str
    status: str


class ProtocolResponse(BaseModel):
    protocol: dict[str, list[str]]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/protocol", response_model=ProtocolResponse)
def get_recording_protocol() -> ProtocolResponse:
    """Return the guided recording protocol texts."""
    return ProtocolResponse(protocol=RECORDING_PROTOCOL)


@router.post("/record/start", response_model=RecordStartResponse)
def record_start(body: RecordStartRequest, db: Session = Depends(get_db)) -> RecordStartResponse:
    """Begin a microphone recording session for the given voice / section."""
    voice = VoiceService.get_voice(db, body.voice_id)
    if voice is None:
        raise HTTPException(status_code=404, detail="Voice not found.")
    if _recorder.is_active():
        raise HTTPException(status_code=409, detail="A recording is already in progress.")

    session = _recorder.start(voice_id=body.voice_id, section=body.section)
    return RecordStartResponse(
        voice_id=session.voice_id,
        section=session.section,
        file_path=str(session.file_path),
        is_recording=session.is_recording,
        error=session.error,
    )


@router.post("/record/stop", response_model=RecordStopResponse)
def record_stop(db: Session = Depends(get_db)) -> RecordStopResponse:
    """Stop the active recording and persist the file."""
    session = _recorder.stop()
    if session is None:
        raise HTTPException(status_code=409, detail="No active recording to stop.")

    if session.error is None and session.file_path.exists():
        VoiceService.add_recording(
            db,
            voice_id=session.voice_id,
            file_path=str(session.file_path),
            duration_seconds=session.duration,
            section=session.section,
        )

    return RecordStopResponse(
        voice_id=session.voice_id,
        section=session.section,
        file_path=str(session.file_path),
        duration=session.duration,
        error=session.error,
    )


@router.post("/sample", status_code=status.HTTP_201_CREATED)
async def upload_sample(
    voice_id: Annotated[str, Form()],
    section: Annotated[str, Form()] = "warmup",
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    """Upload a pre-recorded WAV sample for a voice."""
    voice = VoiceService.get_voice(db, voice_id)
    if voice is None:
        raise HTTPException(status_code=404, detail="Voice not found.")

    dest_dir = RECORDINGS_DIR / voice_id / section
    dest_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(dest_dir.glob("sample_*.wav"))
    idx = len(existing) + 1
    dest_path = dest_dir / f"sample_{idx:03d}.wav"

    with dest_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    recording = VoiceService.add_recording(
        db, voice_id=voice_id, file_path=str(dest_path), section=section
    )
    return {"recording_id": recording.recording_id, "file_path": str(dest_path)}


@router.post("/create", response_model=VoiceResponse, status_code=status.HTTP_201_CREATED)
def create_voice(body: CreateVoiceRequest, db: Session = Depends(get_db)) -> VoiceResponse:
    """Create a new voice profile (metadata only; recordings uploaded separately)."""
    if VoiceService.get_voice_by_name(db, body.name) is not None:
        raise HTTPException(
            status_code=409, detail=f"A voice named '{body.name}' already exists."
        )
    voice = VoiceService.create_voice(db, name=body.name, description=body.description)
    return VoiceResponse.from_orm_voice(voice)


@router.post("/{voice_id}/train", response_model=TrainingJobResponse)
def train_voice(
    voice_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> TrainingJobResponse:
    """Enqueue a background job to build the speaker embedding for *voice_id*."""
    voice = VoiceService.get_voice(db, voice_id)
    if voice is None:
        raise HTTPException(status_code=404, detail="Voice not found.")

    recordings = VoiceService.list_recordings(db, voice_id)
    if not recordings:
        raise HTTPException(status_code=422, detail="No recordings found for this voice.")

    job = VoiceService.create_training_job(db, voice_id=voice_id)
    background_tasks.add_task(build_voice_embedding, voice_id=voice_id, job_id=job.job_id)
    return TrainingJobResponse(job_id=job.job_id, voice_id=voice_id, status=job.status)


@router.get("s", response_model=list[VoiceResponse])
def list_voices(db: Session = Depends(get_db)) -> list[VoiceResponse]:
    """List all voice profiles."""
    voices = VoiceService.list_voices(db)
    return [VoiceResponse.from_orm_voice(v) for v in voices]


@router.get("/{voice_id}", response_model=VoiceResponse)
def get_voice(voice_id: str, db: Session = Depends(get_db)) -> VoiceResponse:
    """Retrieve a single voice profile by ID."""
    voice = VoiceService.get_voice(db, voice_id)
    if voice is None:
        raise HTTPException(status_code=404, detail="Voice not found.")
    return VoiceResponse.from_orm_voice(voice)


@router.delete("/{voice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_voice(voice_id: str, db: Session = Depends(get_db)) -> None:
    """Delete a voice profile and all its associated data."""
    deleted = VoiceService.delete_voice(db, voice_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Voice not found.")
