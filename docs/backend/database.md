# 🗄️ Database Guide

This document covers the database schema, ORM models, how relationships work, and how to manage migrations.

---

## Table of Contents

- [Technology Choice](#technology-choice)
- [Schema Diagram](#schema-diagram)
- [Tables](#tables)
  - [Voice](#voice)
  - [Recording](#recording)
  - [TrainingJob](#trainingjob)
  - [GeneratedAudio](#generatedaudio)
- [Relationships](#relationships)
- [Database Module (db.py)](#database-module-dbpy)
- [Migrations with Alembic](#migrations-with-alembic)
- [SQLite vs PostgreSQL](#sqlite-vs-postgresql)

---

## Technology Choice

| Component | Choice | Why |
|-----------|--------|-----|
| Database engine | **SQLite** | Zero-config, single-file, perfect for local-first apps |
| ORM | **SQLAlchemy** | Industry-standard Python ORM with excellent async support |
| Migrations | **Alembic** | Version-controlled, incremental schema changes |

> 🔑 The database stores only **metadata** (names, paths, statuses, timestamps). Large binary files (WAV audio, `.pt` embeddings) are stored on the filesystem and referenced by path.

---

## Schema Diagram

```
┌───────────────────────────────┐
│           voices              │
├───────────────────────────────┤
│ voice_id        PK  UUID      │◄──┐
│ name            UNIQUE TEXT   │   │
│ description     TEXT nullable │   │
│ status          ENUM          │   │  one-to-many
│ embedding_path  TEXT nullable │   │
│ samples_path    TEXT nullable │   │
│ created_at      DATETIME      │   │
└───────────────────────────────┘   │
                                    │
┌───────────────────────────────┐   │
│          recordings           │   │
├───────────────────────────────┤   │
│ recording_id    PK  UUID      │   │
│ voice_id        FK ───────────┼───┤
│ file_path       TEXT          │   │
│ duration_seconds FLOAT        │   │
│ section         ENUM          │   │
│ created_at      DATETIME      │   │
└───────────────────────────────┘   │
                                    │
┌───────────────────────────────┐   │
│         training_jobs         │   │
├───────────────────────────────┤   │
│ job_id          PK  UUID      │   │
│ voice_id        FK ───────────┼───┤
│ status          ENUM          │   │
│ error_message   TEXT nullable │   │
│ created_at      DATETIME      │   │
│ completed_at    DATETIME nul. │   │
└───────────────────────────────┘   │
                                    │
┌───────────────────────────────┐   │
│        generated_audio        │   │
├───────────────────────────────┤   │
│ audio_id        PK  UUID      │   │
│ voice_id        FK ───────────┼───┘
│ text            TEXT          │
│ file_path       TEXT          │
│ speed           FLOAT         │
│ temperature     FLOAT         │
│ created_at      DATETIME      │
└───────────────────────────────┘
```

---

## Tables

> 📂 Source: `backend/app/models/db_models.py`

---

### Voice

Stores a **voice profile** — the top-level entity that groups recordings, training jobs, and generated audio together.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `voice_id` | UUID | PK, not null | Unique identifier generated at creation time |
| `name` | String | Unique, not null | Human-readable name (e.g. "Alice") |
| `description` | Text | Nullable | Optional free-text notes |
| `status` | Enum | Not null, default `pending` | `pending` → `ready` → (or `failed`) |
| `embedding_path` | String | Nullable | Absolute path to `embedding.pt` once training completes |
| `samples_path` | String | Nullable | Absolute path to the voice's recordings directory |
| `created_at` | DateTime | Not null | Row creation timestamp (UTC) |

**Status lifecycle:**

```
[create]        [train + succeed]    [train + fail]
  pending  ──────────► ready         pending ──► failed
```

---

### Recording

Stores metadata for **one audio sample** recorded or uploaded for a voice.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `recording_id` | UUID | PK, not null | Unique identifier |
| `voice_id` | UUID | FK → voices, not null | Owning voice |
| `file_path` | String | Not null | Absolute path to the WAV file |
| `duration_seconds` | Float | Not null | Length of the audio in seconds |
| `section` | Enum | Not null | Which protocol section this sample belongs to |
| `created_at` | DateTime | Not null | Row creation timestamp |

**Section values:**

| Value | Protocol stage |
|-------|---------------|
| `warmup` | Warm-up sentences |
| `storybook` | Extended narrative |
| `numbers` | Numbers, dates, measurements |
| `assistant` | Conversational assistant phrases |
| `expressive` | Emotional/expressive speech |

---

### TrainingJob

Tracks the **background embedding-training task** associated with a voice.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `job_id` | UUID | PK, not null | Unique identifier |
| `voice_id` | UUID | FK → voices, not null | Voice being trained |
| `status` | Enum | Not null, default `queued` | Current job state |
| `error_message` | Text | Nullable | Populated on failure |
| `created_at` | DateTime | Not null | When the job was enqueued |
| `completed_at` | DateTime | Nullable | When the job finished (success or failure) |

**Status lifecycle:**

```
POST /voice/{id}/train
       │
       ▼
    queued ──► running ──► done
                    └──────► failed  (error_message populated)
```

---

### GeneratedAudio

Records metadata for **each synthesis output** so it can be downloaded later.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `audio_id` | UUID | PK, not null | Unique identifier; used in the download URL |
| `voice_id` | UUID | FK → voices, not null | Voice used for synthesis |
| `text` | Text | Not null | The input text that was synthesised |
| `file_path` | String | Not null | Absolute path to the output WAV |
| `speed` | Float | Not null | Playback speed used (0.1 – 3.0) |
| `temperature` | Float | Not null | Temperature used (0.0 – 1.0) |
| `created_at` | DateTime | Not null | Row creation timestamp |

---

## Relationships

SQLAlchemy `relationship()` declarations allow navigating from a `Voice` object to all its related rows:

```python
voice = db.query(Voice).first()

voice.recordings      # List[Recording]  — all audio samples
voice.training_jobs   # List[TrainingJob] — all training attempts
voice.generated_audio # List[GeneratedAudio] — all TTS outputs
```

Cascading deletes: when a `Voice` is deleted, **all** related rows are automatically removed from the database and the associated files are deleted from the filesystem by `VoiceService.delete_voice()`.

---

## Database Module (`db.py`)

> 📂 Source: `backend/app/database/db.py`

This module is the single source of truth for the database connection.

```python
# What this module provides:

engine       # SQLAlchemy Engine — the raw connection pool
SessionLocal # Session factory — call SessionLocal() to open a DB session
Base         # Declarative base class — all ORM models inherit from this
get_db()     # FastAPI dependency — yields a session, closes it on exit
init_db()    # Creates all tables (called once on server startup)
```

**Why a factory instead of a global session?**

Each HTTP request gets its own isolated session via `get_db()`. This prevents one request's uncommitted transaction from leaking into another.

---

## Migrations with Alembic

Alembic tracks database schema changes as versioned migration scripts.

> 📂 Source: `backend/alembic/`

### Run all pending migrations

```bash
cd backend
alembic upgrade head
```

### Check current migration state

```bash
alembic current
```

### Create a new migration

After changing `db_models.py`:

```bash
alembic revision --autogenerate -m "add_language_column_to_generated_audio"
```

This creates a new file in `alembic/versions/` with `upgrade()` and `downgrade()` functions.

### Roll back the last migration

```bash
alembic downgrade -1
```

### Migration file structure

```
alembic/
├── env.py                         # Alembic environment — imports your models so
│                                  # autogenerate can diff them against the DB
├── script.py.mako                 # Template for new revision files
└── versions/
    └── 0001_initial.py            # Creates voices, recordings,
                                   # training_jobs, generated_audio tables
```

> 💡 On a fresh install, `init_db()` (called on server startup) creates the tables directly via `Base.metadata.create_all()`. Alembic is used for *upgrading* an existing installation.

---

## SQLite vs PostgreSQL

The application defaults to SQLite for simplicity. To switch to PostgreSQL:

1. Update the `DATABASE_URL` environment variable:

   ```bash
   DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/voiceagent
   ```

2. Install the driver:

   ```bash
   pip install psycopg2-binary
   ```

3. Remove the `connect_args={"check_same_thread": False}` guard in `db.py` (it is SQLite-specific).

4. Run migrations:

   ```bash
   alembic upgrade head
   ```

All ORM code is database-agnostic and will work without further changes.
