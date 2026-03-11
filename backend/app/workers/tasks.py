"""Background worker tasks executed via FastAPI BackgroundTasks."""

from __future__ import annotations

import logging
from pathlib import Path

from app.config import (
    EMBEDDINGS_DIR,
    RECORDINGS_DIR,
    TTS_DEVICE,
    TTS_MODEL_NAME,
)
from app.database.db import SessionLocal
from app.services.voice_service import VoiceService
from voice_engine.dataset_builder import DatasetBuilder
from voice_engine.embedding import EmbeddingEngine

logger = logging.getLogger(__name__)

_dataset_builder = DatasetBuilder()
_embedding_engine = EmbeddingEngine(model_name=TTS_MODEL_NAME, device=TTS_DEVICE)


def build_voice_embedding(voice_id: str, job_id: str) -> None:
    """Build a speaker embedding from existing recordings for *voice_id*.

    This function is meant to run in a FastAPI ``BackgroundTasks`` worker.
    It uses its own DB session so that it is independent of the request
    session that created the job.
    """
    db = SessionLocal()
    try:
        VoiceService.update_job_status(db, job_id, "running")

        recordings_dir = RECORDINGS_DIR / voice_id
        dataset_dir = EMBEDDINGS_DIR / voice_id / "dataset"

        # Step 1 – Build clean dataset
        build_result = _dataset_builder.build(
            voice_id=voice_id,
            recordings_dir=recordings_dir,
            dataset_dir=dataset_dir,
        )
        if build_result.error:
            raise RuntimeError(build_result.error)
        if not build_result.sample_paths:
            raise RuntimeError("No usable audio samples found after dataset build.")

        # Step 2 – Create speaker embedding
        embedding_path = EMBEDDINGS_DIR / voice_id / "embedding.pt"
        _embedding_engine.create_embedding(
            audio_paths=build_result.sample_paths,
            output_path=embedding_path,
        )

        # Step 3 – Persist embedding path on the Voice record
        VoiceService.set_embedding_path(db, voice_id, str(embedding_path))
        VoiceService.update_job_status(db, job_id, "done")
        logger.info("Embedding for voice %s completed successfully.", voice_id)

    except Exception as exc:
        logger.exception("Embedding job %s failed: %s", job_id, exc)
        VoiceService.update_job_status(db, job_id, "failed", error_message=str(exc))
    finally:
        db.close()
