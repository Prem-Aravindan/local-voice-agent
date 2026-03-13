# 🏗️ Architecture Guide

This document explains **how every piece of the application fits together** — the layers, the data flows, and the design decisions behind them.

---

## Table of Contents

- [High-Level Overview](#high-level-overview)
- [Layer Breakdown](#layer-breakdown)
- [End-to-End Data Flows](#end-to-end-data-flows)
  - [1. Record a Voice](#1-record-a-voice)
  - [2. Train an Embedding](#2-train-an-embedding)
  - [3. Generate Speech](#3-generate-speech)
- [Component Interaction Map](#component-interaction-map)
- [Directory Structure](#directory-structure)
- [Key Design Decisions](#key-design-decisions)

---

## High-Level Overview

The application is split into two top-level services:

```
┌────────────────────────────────────────────────────────────────┐
│  FRONTEND  (Next.js · TypeScript)                              │
│                                                                │
│   /               /voices          /record        /generate   │
│   Dashboard        CRUD panel       Recording      TTS panel  │
│                                     wizard                    │
└────────────────────────┬───────────────────────────────────────┘
                         │
                  HTTP REST (JSON)
                  Audio upload/download (WAV)
                         │
┌────────────────────────▼───────────────────────────────────────┐
│  BACKEND  (FastAPI · Python)                                   │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  API Layer   /api/v1/voice/*  /api/v1/tts  /api/v1/audio│  │
│  └────────────────────┬────────────────────────────────────┘  │
│                       │ calls                                  │
│  ┌────────────────────▼────────────────────────────────────┐  │
│  │  Service Layer   VoiceService · TTSService               │  │
│  └────────────────────┬────────────────────────────────────┘  │
│                       │ uses                                   │
│  ┌────────────────────▼────────────────────────────────────┐  │
│  │  Voice Engine    Recorder · DatasetBuilder               │  │
│  │                  EmbeddingEngine · TTSEngine             │  │
│  └────────────────────┬────────────────────────────────────┘  │
│                       │ reads/writes                           │
│  ┌────────────────────▼────────────────────────────────────┐  │
│  │  Storage          SQLite DB  ·  data/ filesystem         │  │
│  └─────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

---

## Layer Breakdown

### 1. Frontend (Presentation Layer)

**Purpose:** Provide a guided, user-friendly interface.  
**Technology:** Next.js (React) with TypeScript and Tailwind CSS.  
**Communicates with:** Backend exclusively via `app/lib/api.ts`.

> 💡 The frontend holds **no business logic** — it only calls the backend API and renders the response.

### 2. API Layer (Interface Layer)

**Purpose:** Accept HTTP requests, validate inputs, and delegate to the service layer.  
**Files:** `backend/app/api/voices.py`, `tts.py`, `audio.py`  
**Why FastAPI?** Automatic OpenAPI/Swagger docs, async-native, Pydantic validation built in.

### 3. Service Layer (Business Logic Layer)

**Purpose:** Orchestrate database operations and voice-engine calls.  
**Files:** `backend/app/services/voice_service.py`, `tts_service.py`  
**Key principle:** All database interaction goes through services; API routers do **not** query the DB directly.

### 4. Voice Engine (ML/Audio Processing Layer)

**Purpose:** The heavy-lifting — audio capture, preprocessing, ML inference.  
**Files:** `backend/voice_engine/` package  
**Key principle:** Engine modules are pure functions / thin classes; they don't know about the database.

### 5. Storage (Persistence Layer)

Two complementary storage mechanisms:

| Store | What | Where | Format |
|-------|------|-------|--------|
| SQLite | Metadata, relationships, status | `database/app.db` | Rows |
| Filesystem | Audio files, ML tensors | `data/` | WAV, `.pt` |

> 🔑 The SQLite DB stores *metadata* (paths, statuses, timestamps). The actual binary data (audio, embeddings) lives in the filesystem. The DB row points to the file path.

---

## End-to-End Data Flows

### 1. Record a Voice

```
Browser (microphone) ──► MediaRecorder API (WAV blob)
        │
        ▼
POST /api/v1/voice/sample  (multipart/form-data)
        │
        ▼  voices.py router
upload_sample()
  • Validate voice_id exists in DB
  • Save WAV to  data/recordings/{voice_id}/{section}/sample_NNN.wav
  • Call VoiceService.add_recording()
        │
        ▼  voice_service.py
INSERT INTO recordings (voice_id, file_path, duration, section)
        │
        ▼
201 Created  ←── frontend shows "Recorded!"
```

### 2. Train an Embedding

```
POST /api/v1/voice/{voice_id}/train
        │
        ▼  voices.py router
train_voice()
  • Validate voice exists
  • VoiceService.create_training_job()  →  INSERT INTO training_jobs (status="queued")
  • FastAPI BackgroundTasks.add_task(build_voice_embedding, voice_id, job_id)
        │
        ▼  202 / 200 returned immediately to browser

═══════════════════════ Background Worker (tasks.py) ═══════════════════════

UPDATE training_jobs SET status="running"
        │
        ▼  DatasetBuilder.build(recordings_dir)
  FOR EACH recording:
    1. Load WAV (librosa)
    2. Resample → 24 kHz, convert → mono
    3. Trim silence (top_db=30 dB)
    4. Normalize to -3 dBFS
    5. Skip if < 1 second
    6. Save cleaned WAV to  data/recordings/{voice_id}/dataset/
        │
        ▼  EmbeddingEngine.create_embedding(cleaned_paths, voice_id)
  1. Load Coqui XTTS v2 model  (first run: downloads ~1.8 GB)
  2. model.get_conditioning_latents(audio_paths=[...])
     ↳ gpt_cond_latent   — GPT conditioning tensor
     ↳ speaker_embedding — voice identity vector
  3. torch.save({...}, "data/embeddings/{voice_id}/embedding.pt")
        │
        ▼
VoiceService.set_embedding_path()
  UPDATE voices SET status="ready", embedding_path="..."
  Write metadata.json alongside the voice directory
        │
UPDATE training_jobs SET status="done", completed_at=NOW()
```

### 3. Generate Speech

```
POST /api/v1/tts  { voice_id, text, language, speed, temperature }
        │
        ▼  tts.py router
  • Validate voice exists  and  status == "ready"
  • TTSService.generate(voice_id, text, ...)
        │
        ▼  tts_service.py
  1. Load TTSEngine  (singleton, cached)
  2. TTSEngine.synthesise(text, embedding_path, ...)
        │
        ▼  tts_engine.py
  1. Load XTTS v2 model  (cached with @lru_cache)
  2. Load embedding dict from .pt file
  3. model.inference(text, language,
                     gpt_cond_latent, speaker_embedding,
                     temperature, speed)
  4. soundfile.write("data/generated/{voice_id}/{audio_id}.wav", samples, 24000)
        │
        ▼  back in tts_service.py
  INSERT INTO generated_audio (audio_id, voice_id, text, file_path, speed, temperature)
        │
        ▼  201 Created  { audio_id }
        │
Browser: GET /api/v1/audio/{audio_id}
        │
        ▼  audio.py router
FileResponse("data/generated/{voice_id}/{audio_id}.wav")
        │
        ▼
Browser plays / downloads the WAV
```

---

## Component Interaction Map

```
┌──────────────────────────────────────────────────────────────────┐
│ voices.py (router)                                               │
│   ├─ VoiceService.create_voice()                                 │
│   ├─ VoiceService.list_voices()                                  │
│   ├─ VoiceService.delete_voice()                                 │
│   ├─ VoiceRecorder.start() / .stop()   ─── Recorder (thread)    │
│   ├─ VoiceService.add_recording()                                │
│   └─ BackgroundTasks → build_voice_embedding()                   │
│                              │                                   │
│                              ├─ DatasetBuilder.build()           │
│                              ├─ EmbeddingEngine.create_embedding()│
│                              └─ VoiceService.set_embedding_path()│
├──────────────────────────────────────────────────────────────────┤
│ tts.py (router)                                                  │
│   └─ TTSService.generate()                                       │
│              │                                                   │
│              └─ TTSEngine.synthesise()   ─── XTTS v2 model       │
├──────────────────────────────────────────────────────────────────┤
│ audio.py (router)                                                │
│   └─ FileResponse  (serves WAV directly from filesystem)         │
└──────────────────────────────────────────────────────────────────┘
                  │  All routers share
                  ▼
           SQLAlchemy Session  (get_db() dependency)
                  │
                  ▼
            SQLite  database/app.db
```

---

## Directory Structure

```
local-voice-agent/
│
├── backend/                        # Python package — the server
│   ├── app/
│   │   ├── api/                    # HTTP route handlers (thin, no business logic)
│   │   │   ├── audio.py            # GET /audio/{id}
│   │   │   ├── tts.py              # POST /tts
│   │   │   └── voices.py           # All /voice/* endpoints
│   │   ├── database/
│   │   │   └── db.py               # SQLAlchemy engine, session factory, Base, get_db()
│   │   ├── models/
│   │   │   └── db_models.py        # ORM table definitions (Voice, Recording, …)
│   │   ├── services/               # Business logic — all DB writes go here
│   │   │   ├── voice_service.py    # Voice + Recording + TrainingJob CRUD
│   │   │   └── tts_service.py      # TTS orchestration + GeneratedAudio persistence
│   │   ├── workers/
│   │   │   └── tasks.py            # Background embedding-training task
│   │   ├── config.py               # Paths, env vars, recording protocol prompts
│   │   └── main.py                 # FastAPI app, middleware, router inclusion
│   │
│   ├── voice_engine/               # Pure ML/audio modules (no FastAPI, no DB)
│   │   ├── recorder.py             # Microphone capture → WAV (sounddevice)
│   │   ├── dataset_builder.py      # Audio cleaning pipeline (librosa)
│   │   ├── embedding.py            # Speaker embedding extraction (XTTS v2)
│   │   └── tts_engine.py           # Speech synthesis (XTTS v2)
│   │
│   ├── alembic/                    # Database schema migrations
│   │   ├── versions/
│   │   │   └── 0001_initial.py     # First migration — creates all four tables
│   │   ├── env.py                  # Alembic runtime config
│   │   └── script.py.mako          # Template for new migration files
│   ├── alembic.ini                 # Points Alembic to the migration directory
│   └── requirements.txt            # Pinned Python dependencies
│
├── frontend/                       # Next.js app — the browser UI
│   └── app/
│       ├── page.tsx                # Home / dashboard
│       ├── layout.tsx              # Navigation shell
│       ├── voices/page.tsx         # Voice profile management
│       ├── record/page.tsx         # Guided recording wizard
│       ├── generate/page.tsx       # TTS generation panel
│       ├── lib/api.ts              # Typed API client (all fetch() calls live here)
│       └── globals.css             # Tailwind base styles
│
├── docker/
│   ├── Dockerfile.backend          # Python image for the API server
│   └── Dockerfile.frontend         # Node image for the Next.js server
│
├── tests/
│   ├── conftest.py                 # sys.path setup for pytest
│   └── test_voice_agent.py         # 25+ unit/integration tests
│
├── docker-compose.yml              # Wires backend + frontend together
├── README.md                       # Project-level quick-start
└── pytest.ini                      # Pytest configuration

Runtime directories (git-ignored, created on first run):
├── data/
│   ├── voices/                     # Voice metadata + sub-dirs
│   ├── recordings/{voice_id}/      # Raw + cleaned WAV files
│   ├── embeddings/{voice_id}/      # embedding.pt + metadata.json
│   ├── models/                     # Downloaded XTTS v2 model weights
│   └── generated/{voice_id}/       # Synthesised speech WAVs
├── database/
│   └── app.db                      # SQLite database file
└── logs/                           # Application log files
```

---

## Key Design Decisions

### Why local-first?
Voice data is uniquely personal. Running entirely on your hardware means your raw recordings and speaker embeddings never leave your machine.

### Why SQLite?
Zero configuration, single-file, perfectly adequate for a single-user local application. Alembic handles schema upgrades so you can migrate to PostgreSQL later with minimal code changes.

### Why separate filesystem + DB?
Large binary files (audio, model tensors) are stored on disk; the database stores only lightweight metadata and file paths. This keeps the DB small and fast and avoids binary blobs in SQL.

### Why BackgroundTasks for embedding training?
Embedding extraction takes 2–5 minutes (CPU). Running it in a background task lets the HTTP request return immediately and the frontend can poll the job status endpoint rather than waiting for a timeout.

### Why a module-level `VoiceRecorder` singleton?
Microphone hardware only exists once per process. A singleton prevents two requests from trying to open the same audio device simultaneously. Concurrent recording attempts are rejected with an appropriate HTTP error.

### Why `@lru_cache` on the TTS model loader?
Loading the 1.8 GB XTTS v2 model into memory takes 10–20 seconds. Caching the loaded model in memory means the second synthesis request is answered in seconds, not tens of seconds.
