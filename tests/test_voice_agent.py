"""Unit tests for the Voice Clone Agent backend.

These tests are self-contained and do not require PyTorch, TTS, or
sounddevice to be installed – all heavy dependencies are patched out.

Run:
    cd voice-agent/backend
    python -m pytest tests/ -v
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub out heavy optional dependencies so tests work without them installed
# ---------------------------------------------------------------------------

def _make_stub_module(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


for _mod in ("torch", "TTS", "TTS.api", "sounddevice", "librosa", "soundfile", "pydub"):
    if _mod not in sys.modules:
        _make_stub_module(_mod)

# Give torch.save / torch.load no-op stubs
_torch = sys.modules["torch"]
_torch.save = lambda obj, path, **kw: None  # type: ignore[attr-defined]
_torch.load = lambda path, **kw: {"stub": True}  # type: ignore[attr-defined]
_torch.zeros = lambda *a, **kw: []  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Add backend/ to sys.path so 'app' and 'voice_engine' are importable
# (conftest.py does this too; kept here for standalone execution)
# ---------------------------------------------------------------------------
_BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect all data directories to a temp path for isolation."""
    import app.config as cfg

    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(cfg, "VOICES_DIR", tmp_path / "data" / "voices")
    monkeypatch.setattr(cfg, "RECORDINGS_DIR", tmp_path / "data" / "recordings")
    monkeypatch.setattr(cfg, "EMBEDDINGS_DIR", tmp_path / "data" / "embeddings")
    monkeypatch.setattr(cfg, "GENERATED_DIR", tmp_path / "data" / "generated")

    for d in (cfg.VOICES_DIR, cfg.RECORDINGS_DIR, cfg.EMBEDDINGS_DIR, cfg.GENERATED_DIR):
        d.mkdir(parents=True, exist_ok=True)

    return tmp_path


@pytest.fixture()
def db_session(tmp_path: Path):
    """In-memory SQLite session for testing."""
    import os

    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # Import after setting DATABASE_URL so the engine picks up the override
    from app.database.db import Base
    from app.models import db_models  # noqa: F401 – registers models

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


# ===========================================================================
# Tests: DatasetBuilder
# ===========================================================================


class TestDatasetBuilder:
    def test_returns_error_when_no_wav_files(self, tmp_path: Path) -> None:
        from voice_engine.dataset_builder import DatasetBuilder

        builder = DatasetBuilder()
        result = builder.build(
            voice_id="test_voice",
            recordings_dir=tmp_path / "empty",
            dataset_dir=tmp_path / "dataset",
        )
        assert result.error is not None

    def test_returns_error_when_libs_unavailable(self, tmp_path: Path, monkeypatch) -> None:
        import voice_engine.dataset_builder as db_mod

        monkeypatch.setattr(db_mod, "_AUDIO_LIBS_AVAILABLE", False)

        from voice_engine.dataset_builder import DatasetBuilder

        builder = DatasetBuilder()
        result = builder.build(
            voice_id="v",
            recordings_dir=tmp_path,
            dataset_dir=tmp_path / "out",
        )
        assert result.error is not None
        assert "librosa" in result.error or "installed" in result.error


# ===========================================================================
# Tests: VoiceService
# ===========================================================================


class TestVoiceService:
    def test_create_and_list_voice(self, db_session, tmp_data: Path) -> None:
        from app.services.voice_service import VoiceService

        voice = VoiceService.create_voice(db_session, name="test_voice")
        assert voice.voice_id is not None
        assert voice.name == "test_voice"
        assert voice.status == "pending"

        voices = VoiceService.list_voices(db_session)
        assert len(voices) == 1
        assert voices[0].voice_id == voice.voice_id

    def test_get_voice_by_name(self, db_session, tmp_data: Path) -> None:
        from app.services.voice_service import VoiceService

        VoiceService.create_voice(db_session, name="my_voice")
        found = VoiceService.get_voice_by_name(db_session, "my_voice")
        assert found is not None
        missing = VoiceService.get_voice_by_name(db_session, "ghost")
        assert missing is None

    def test_delete_voice(self, db_session, tmp_data: Path) -> None:
        from app.services.voice_service import VoiceService

        voice = VoiceService.create_voice(db_session, name="delete_me")
        deleted = VoiceService.delete_voice(db_session, voice.voice_id)
        assert deleted is True
        assert VoiceService.get_voice(db_session, voice.voice_id) is None

    def test_add_recording(self, db_session, tmp_data: Path) -> None:
        from app.services.voice_service import VoiceService

        voice = VoiceService.create_voice(db_session, name="rec_voice")
        recording = VoiceService.add_recording(
            db_session,
            voice_id=voice.voice_id,
            file_path="/tmp/sample.wav",
            duration_seconds=5.0,
            section="warmup",
        )
        assert recording.recording_id is not None
        assert recording.section == "warmup"

        recs = VoiceService.list_recordings(db_session, voice.voice_id)
        assert len(recs) == 1

    def test_training_job_lifecycle(self, db_session, tmp_data: Path) -> None:
        from app.services.voice_service import VoiceService

        voice = VoiceService.create_voice(db_session, name="job_voice")
        job = VoiceService.create_training_job(db_session, voice_id=voice.voice_id)
        assert job.status == "queued"

        VoiceService.update_job_status(db_session, job.job_id, "running")
        db_session.expire_all()
        from app.models.db_models import TrainingJob

        refreshed = db_session.get(TrainingJob, job.job_id)
        assert refreshed.status == "running"

        VoiceService.update_job_status(db_session, job.job_id, "done")
        db_session.expire_all()
        done_job = db_session.get(TrainingJob, job.job_id)
        assert done_job.status == "done"
        assert done_job.completed_at is not None

    def test_set_embedding_path(self, db_session, tmp_data: Path) -> None:
        from app.services.voice_service import VoiceService

        voice = VoiceService.create_voice(db_session, name="emb_voice")
        updated = VoiceService.set_embedding_path(
            db_session, voice.voice_id, "/data/embeddings/emb_voice/embedding.pt"
        )
        assert updated is not None
        assert updated.status == "ready"
        assert updated.embedding_path.endswith("embedding.pt")


# ===========================================================================
# Tests: TTSEngine (stub path)
# ===========================================================================


class TestTTSEngine:
    def test_generate_writes_stub_when_tts_unavailable(self, tmp_path: Path, monkeypatch) -> None:
        import voice_engine.tts_engine as tts_mod

        monkeypatch.setattr(tts_mod, "_TTS_AVAILABLE", False)

        from voice_engine.tts_engine import TTSEngine

        engine = TTSEngine(model_name="dummy", device="cpu")
        emb_path = tmp_path / "embedding.pt"
        out_path = tmp_path / "output.wav"

        result = engine.generate(
            text="Hello world",
            embedding_path=emb_path,
            output_path=out_path,
        )
        assert result == out_path
        assert out_path.exists()
        assert out_path.stat().st_size > 0


# ===========================================================================
# Tests: Recording protocol config
# ===========================================================================


class TestRecordingProtocol:
    def test_protocol_has_required_sections(self) -> None:
        from app.config import RECORDING_PROTOCOL

        for section in ("warmup", "storybook", "numbers", "assistant", "expressive"):
            assert section in RECORDING_PROTOCOL
            assert len(RECORDING_PROTOCOL[section]) > 0

    def test_all_prompts_are_non_empty_strings(self) -> None:
        from app.config import RECORDING_PROTOCOL

        for section, prompts in RECORDING_PROTOCOL.items():
            for prompt in prompts:
                assert isinstance(prompt, str)
                assert len(prompt.strip()) > 0, f"Empty prompt in section '{section}'"


# ===========================================================================
# Tests: FastAPI application (integration-style)
# ===========================================================================


@pytest.fixture()
def api_client(tmp_data: Path):
    """Provide a FastAPI TestClient backed by a fresh in-memory SQLite DB."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from fastapi.testclient import TestClient

    import app.database.db as db_mod
    from app.models import db_models  # noqa: F401 — registers ORM models

    # StaticPool ensures all connections share the same in-memory database
    mem_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db_mod.Base.metadata.create_all(bind=mem_engine)

    # Patch module-level engine and SessionLocal
    orig_engine = db_mod.engine
    orig_session_local = db_mod.SessionLocal
    db_mod.engine = mem_engine
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=mem_engine)
    db_mod.SessionLocal = TestingSession

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    from app.main import app
    app.dependency_overrides[db_mod.get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    db_mod.Base.metadata.drop_all(bind=mem_engine)
    db_mod.engine = orig_engine
    db_mod.SessionLocal = orig_session_local


class TestFastAPIApp:
    def test_health_endpoint(self, api_client) -> None:
        resp = api_client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_create_and_list_voices(self, api_client) -> None:
        resp = api_client.post(
            "/api/v1/voice/create", json={"name": "api_test_voice"}
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "api_test_voice"
        assert data["status"] == "pending"

        list_resp = api_client.get("/api/v1/voices")
        assert list_resp.status_code == 200
        voices = list_resp.json()
        assert any(v["name"] == "api_test_voice" for v in voices)

    def test_duplicate_voice_name_returns_409(self, api_client) -> None:
        api_client.post("/api/v1/voice/create", json={"name": "dup_voice"})
        resp = api_client.post("/api/v1/voice/create", json={"name": "dup_voice"})
        assert resp.status_code == 409

    def test_tts_requires_ready_voice(self, api_client) -> None:
        # Create a voice (status=pending)
        create_resp = api_client.post("/api/v1/voice/create", json={"name": "tts_pending"})
        voice_id = create_resp.json()["voice_id"]

        resp = api_client.post(
            "/api/v1/tts", json={"voice_id": voice_id, "text": "Hello"}
        )
        assert resp.status_code == 422

    def test_get_protocol(self, api_client) -> None:
        resp = api_client.get("/api/v1/voice/protocol")
        assert resp.status_code == 200
        data = resp.json()
        assert "warmup" in data["protocol"]
