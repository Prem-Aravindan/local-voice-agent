# 🤝 Contributing Guide

Welcome! This document explains how to set up a development environment, run tests, and submit quality contributions.

---

## Table of Contents

- [Development Setup](#development-setup)
- [Project Conventions](#project-conventions)
  - [Python Style](#python-style)
  - [TypeScript Style](#typescript-style)
  - [Git Conventions](#git-conventions)
- [Running Tests](#running-tests)
  - [Backend Tests](#backend-tests)
  - [What the Tests Cover](#what-the-tests-cover)
  - [Writing New Tests](#writing-new-tests)
- [Adding a New API Endpoint](#adding-a-new-api-endpoint)
- [Adding a New Frontend Page](#adding-a-new-frontend-page)
- [Database Migrations](#database-migrations)
- [Common Development Tasks](#common-development-tasks)

---

## Development Setup

### Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate       # macOS / Linux
# .venv\Scripts\activate        # Windows

# Install all dependencies including dev tools
pip install -r requirements.txt

# Start the API server with auto-reload
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

npm install
npm run dev    # → http://localhost:3000 with hot-reload
```

---

## Project Conventions

### Python Style

| Convention | Rule |
|------------|------|
| Formatter | `black` (default 88-char line length) |
| Imports | `isort` ordering: stdlib → third-party → local |
| Type hints | All public function signatures must have type annotations |
| Docstrings | Not required for trivial functions; use for complex logic |
| F-strings | Preferred over `.format()` or `%` interpolation |

```python
# ✅ Good
def create_voice(db: Session, name: str, description: str | None = None) -> Voice:
    voice_id = str(uuid.uuid4())
    voice = Voice(voice_id=voice_id, name=name, description=description)
    db.add(voice)
    db.commit()
    return voice

# ❌ Avoid
def create_voice(db, name, description=None):
    ...
```

### TypeScript Style

| Convention | Rule |
|------------|------|
| Quotes | Double quotes `"` |
| Semicolons | Always |
| Types | Prefer `interface` over `type` for object shapes |
| `any` | Avoid; use `unknown` + type guard if needed |
| React | Functional components only; no class components |

```typescript
// ✅ Good
interface Voice {
  voice_id: string;
  name: string;
}

async function fetchVoice(id: string): Promise<Voice> {
  const res = await fetch(`/api/v1/voice/${id}`);
  if (!res.ok) throw new Error("Not found");
  return res.json() as Promise<Voice>;
}

// ❌ Avoid
const fetchVoice = async (id: any) => {
  const res = await fetch(`/api/v1/voice/${id}`)
  return res.json()
}
```

### Git Conventions

| Type | When to use |
|------|------------|
| `feat:` | New feature or user-visible capability |
| `fix:` | Bug fix |
| `docs:` | Documentation changes only |
| `refactor:` | Code restructuring without behaviour change |
| `test:` | Adding or updating tests |
| `chore:` | Build scripts, dependency updates |

Examples:
```
feat: add voice export as ZIP
fix: prevent duplicate training jobs for same voice
docs: add embedding architecture diagram
```

---

## Running Tests

### Backend Tests

```bash
# From the repository root:
python -m pytest tests/ -v

# Run a single test file:
python -m pytest tests/test_voice_agent.py -v

# Run tests matching a name pattern:
python -m pytest tests/ -k "test_create_voice" -v

# Show coverage report:
python -m pytest tests/ --cov=backend/app --cov-report=term-missing
```

> ✅ Tests are self-contained — they require **no** TTS model, PyTorch, or microphone hardware.

### What the Tests Cover

> 📂 Source: `tests/test_voice_agent.py`, `tests/conftest.py`

| Test group | What it verifies |
|------------|-----------------|
| `DatasetBuilder` | Handles missing files, unsupported libraries, valid audio |
| `VoiceService` | Create, get, list, delete voices; add recordings; training job lifecycle |
| `TTSService` | Generate and retrieve audio; stub engine fallback |
| `EmbeddingEngine` | Stub embedding creation |
| `Configuration` | Recording protocol completeness; directory paths |
| FastAPI integration | Health check; voice CRUD via HTTP; TTS via HTTP; audio download |

All integration tests use an **in-memory SQLite database** and **temporary directories** — no persistent state between tests.

### Writing New Tests

Follow the patterns already in `test_voice_agent.py`:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.db import Base

# ── Fixtures ─────────────────────────────────────────────────

@pytest.fixture
def db():
    """In-memory SQLite session for isolated tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

# ── Tests ─────────────────────────────────────────────────────

def test_create_voice(db, tmp_path, monkeypatch):
    """VoiceService.create_voice() should return a Voice with status pending."""
    # Redirect filesystem writes to a temporary directory
    monkeypatch.setattr("app.services.voice_service.RECORDINGS_DIR", tmp_path)

    from app.services.voice_service import VoiceService
    voice = VoiceService.create_voice(db, name="Test Voice")

    assert voice.voice_id is not None
    assert voice.name == "Test Voice"
    assert voice.status == "pending"
```

**Key test utilities:**

| Tool | Purpose |
|------|---------|
| `pytest.fixture` | Set up shared test resources (DB session, temp dirs) |
| `tmp_path` | pytest built-in fixture providing a temporary directory |
| `monkeypatch` | Override module-level constants or functions during a test |
| `fastapi.testclient.TestClient` | Make HTTP requests to the FastAPI app without a real server |

---

## Adding a New API Endpoint

1. **Define the Pydantic schema** (request body / response) in the router file or a shared `schemas.py`
2. **Add the service method** in `app/services/`
3. **Add the route** in the appropriate `app/api/*.py` file
4. **Write a test** in `tests/test_voice_agent.py`

Example skeleton:

```python
# app/api/voices.py

class ExportVoiceResponse(BaseModel):
    zip_url: str

@router.get("/voice/{voice_id}/export", response_model=ExportVoiceResponse)
def export_voice(voice_id: str, db: Session = Depends(get_db)):
    voice = VoiceService.get_voice(db, voice_id)
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    zip_path = VoiceService.export_voice(db, voice_id)
    return ExportVoiceResponse(zip_url=f"/api/v1/audio/{zip_path}")
```

---

## Adding a New Frontend Page

1. Create `frontend/app/<page-name>/page.tsx`
2. Mark it `"use client"` (all pages use client-side data fetching)
3. Add the navigation link in `frontend/app/layout.tsx`
4. Add any new API method in `frontend/app/lib/api.ts`

Example skeleton:

```tsx
// frontend/app/history/page.tsx
"use client";

import { useState, useEffect } from "react";
import { api, AudioRecord } from "../lib/api";

export default function HistoryPage() {
  const [records, setRecords] = useState<AudioRecord[]>([]);

  useEffect(() => {
    // api.listGeneratedAudio() would need to be added to api.ts
    api.listGeneratedAudio().then(setRecords);
  }, []);

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold mb-4">Generation History</h1>
      {records.map((r) => (
        <div key={r.audio_id}>
          <p>{r.text}</p>
          <audio controls src={api.audioUrl(r.audio_id)} />
        </div>
      ))}
    </main>
  );
}
```

---

## Database Migrations

When you change `backend/app/models/db_models.py`:

```bash
cd backend

# 1. Generate a migration file
alembic revision --autogenerate -m "describe_your_change"

# 2. Review the generated file in alembic/versions/
#    Make sure upgrade() and downgrade() look correct

# 3. Apply the migration
alembic upgrade head
```

Always commit the migration file alongside your model changes.

---

## Common Development Tasks

### Reset the database

```bash
rm database/app.db
# Restart the server — init_db() will recreate all tables
```

### Wipe all data (recordings, embeddings, generated audio)

```bash
rm -rf data/
mkdir -p data/voices data/recordings data/embeddings data/models data/generated
```

### Check API response in the terminal

```bash
# List voices
curl -s http://localhost:8000/api/v1/voices | python -m json.tool

# Create a voice
curl -s -X POST http://localhost:8000/api/v1/voice/create \
  -H "Content-Type: application/json" \
  -d '{"name": "Test"}' | python -m json.tool

# Health check
curl http://localhost:8000/healthz
```

### Regenerate OpenAPI schema

```bash
# Output the full OpenAPI JSON spec
curl http://localhost:8000/openapi.json | python -m json.tool > openapi.json
```
