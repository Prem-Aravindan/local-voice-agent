# 🐍 Backend Overview

The backend is a **FastAPI** application written in Python. It serves a REST API consumed by the Next.js frontend and orchestrates all ML/audio processing.

---

## Table of Contents

- [Package Structure](#package-structure)
- [Startup Sequence](#startup-sequence)
- [Dependency Injection](#dependency-injection)
- [Error Handling Conventions](#error-handling-conventions)
- [Logging](#logging)
- [Testing](#testing)

---

## Package Structure

```
backend/
├── app/                            # Core application package
│   ├── __init__.py
│   ├── main.py                     # FastAPI instance, middleware, routers, lifespan
│   ├── config.py                   # All settings (paths, audio params, recording protocol)
│   │
│   ├── api/                        # HTTP interface — thin "controller" layer
│   │   ├── audio.py                # Serve generated WAV files
│   │   ├── tts.py                  # Trigger speech synthesis
│   │   └── voices.py               # Voice + recording + training management
│   │
│   ├── database/
│   │   └── db.py                   # SQLAlchemy engine, SessionLocal, get_db()
│   │
│   ├── models/
│   │   └── db_models.py            # ORM class definitions (Voice, Recording, …)
│   │
│   ├── services/                   # Business logic — orchestrates DB + engine calls
│   │   ├── voice_service.py        # Voice/Recording/TrainingJob lifecycle
│   │   └── tts_service.py          # TTS generation + GeneratedAudio persistence
│   │
│   └── workers/
│       └── tasks.py                # Background task: build_voice_embedding()
│
└── voice_engine/                   # Pure ML/audio modules — no FastAPI, no DB
    ├── __init__.py
    ├── recorder.py                 # Live microphone capture (sounddevice)
    ├── dataset_builder.py          # Audio preprocessing pipeline (librosa)
    ├── embedding.py                # Speaker embedding extraction (XTTS v2)
    └── tts_engine.py               # Speech synthesis (XTTS v2)
```

### 🔑 Separation of concerns

| Layer | Knows about | Does NOT know about |
|-------|-------------|---------------------|
| `api/` | HTTP, request/response shapes | Database internals, ML details |
| `services/` | Database session, voice engine API | HTTP methods, request bodies |
| `voice_engine/` | Audio files, ML models | Database, HTTP, services |

This separation makes each layer independently testable and replaceable.

---

## Startup Sequence

`main.py` uses FastAPI's `lifespan` context manager to run initialisation code before the server accepts requests:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Runs BEFORE the first request ──────────────────────────
    init_db()          # Create tables if they don't exist (no-op if schema is current)
    ensure_dirs()      # Create data/, logs/ subdirectories
    # ────────────────────────────────────────────────────────────
    yield
    # ── Runs AFTER the last request (graceful shutdown) ─────────
    # (nothing needed right now)
```

Routers are registered with a common prefix:

```python
app.include_router(voices_router, prefix="/api/v1")
app.include_router(tts_router,    prefix="/api/v1")
app.include_router(audio_router,  prefix="/api/v1")
```

A CORS middleware allows the frontend development server to call the API:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Dependency Injection

FastAPI's `Depends()` mechanism is used to inject a database session into every endpoint that needs one:

```python
# db.py — factory function
def get_db():
    db = SessionLocal()   # open connection
    try:
        yield db          # hand it to the caller
    finally:
        db.close()        # always close, even on exception

# voices.py — usage in an endpoint
@router.get("/voices")
def list_voices(db: Session = Depends(get_db)):
    return VoiceService.list_voices(db)
```

> 💡 Each HTTP request gets its **own** database session. Sessions are never shared between requests.

---

## Error Handling Conventions

| Situation | HTTP status | How |
|-----------|------------|-----|
| Resource not found | `404 Not Found` | `raise HTTPException(status_code=404)` |
| Invalid input | `422 Unprocessable Entity` | Pydantic validation (automatic) |
| Business rule violation | `400 Bad Request` | `raise HTTPException(status_code=400, detail="…")` |
| Unexpected server error | `500 Internal Server Error` | Unhandled exception (FastAPI default) |

Background tasks catch all exceptions internally and write the error message to the `TrainingJob.error_message` column rather than crashing the worker.

---

## Logging

The application uses Python's built-in `logging` module. Log files are written to the `logs/` directory (configurable via `LOGS_DIR`).

Typical log entries:
- Request received / responded
- Background job status transitions (`queued → running → done/failed`)
- ML model load events
- File I/O errors

---

## Testing

```bash
# From the repo root
python -m pytest tests/ -v
```

Tests are intentionally **self-contained** — they do not require:
- XTTS v2 / PyTorch (the engine modules fall back to stubs)
- A real microphone (sounddevice is mocked)
- A pre-existing database (tests create an in-memory SQLite instance)

See `tests/test_voice_agent.py` and `tests/conftest.py` for details, and the [Contributing guide](../contributing.md) for how to write new tests.
