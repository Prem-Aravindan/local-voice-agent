# Voice Clone Agent

A **modern, local-first voice cloning application** built with FastAPI + Next.js.

## Features

- **Guided voice recording** — 5-section protocol covering warmup, storybook, numbers, assistant-style, and expressive speech
- **Speaker embedding** — Powered by [Coqui XTTS v2](https://github.com/coqui-ai/TTS)
- **Text-to-speech** — Synthesise speech using your cloned voice
- **Voice profiles** — Create, manage, and delete named voice profiles
- **Local-first** — SQLite database, all audio stored on your filesystem
- **Docker ready** — One command to start everything

---

## Quick Start

### Option 1 – Docker Compose (recommended)

```bash
docker compose up
```

- **Backend API**: http://localhost:8000
- **Web UI**: http://localhost:3000
- **API docs**: http://localhost:8000/docs

### Option 2 – Manual

#### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Workflow

1. **Create a voice profile** — `POST /api/v1/voice/create` or use the Voices page
2. **Record samples** — Follow the guided protocol on the Record page (aim for 10–20 min total)
3. **Train the embedding** — Click *Train* or `POST /api/v1/voice/{voice_id}/train`
4. **Generate speech** — Visit the Generate page or `POST /api/v1/tts`
5. **Download audio** — `GET /api/v1/audio/{audio_id}`

---

## Directory Layout

```
.
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routers
│   │   ├── database/      # SQLAlchemy engine & session
│   │   ├── models/        # ORM models
│   │   ├── services/      # Business logic
│   │   ├── workers/       # Background tasks
│   │   ├── config.py      # App-wide settings
│   │   └── main.py        # FastAPI app
│   ├── voice_engine/
│   │   ├── recorder.py    # Microphone recording
│   │   ├── dataset_builder.py  # Audio pre-processing
│   │   ├── embedding.py   # XTTS speaker embedding
│   │   └── tts_engine.py  # Text-to-speech synthesis
│   ├── alembic/           # Database migrations
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── voices/        # Voice management page
│   │   ├── record/        # Guided recording page
│   │   ├── generate/      # TTS generation page
│   │   └── lib/api.ts     # API client
│   └── package.json
├── data/                  # Audio files (gitignored)
├── database/              # SQLite DB (gitignored)
├── logs/                  # Log files (gitignored)
├── docker/
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── docker-compose.yml
└── tests/
    └── test_voice_agent.py
```

---

## REST API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/voices` | List all voice profiles |
| `POST` | `/api/v1/voice/create` | Create a new voice profile |
| `GET` | `/api/v1/voice/{id}` | Get a single voice |
| `DELETE` | `/api/v1/voice/{id}` | Delete a voice |
| `POST` | `/api/v1/voice/{id}/train` | Enqueue embedding job |
| `GET` | `/api/v1/voice/protocol` | Get recording protocol |
| `POST` | `/api/v1/voice/record/start` | Start microphone recording |
| `POST` | `/api/v1/voice/record/stop` | Stop microphone recording |
| `POST` | `/api/v1/voice/sample` | Upload a WAV sample |
| `POST` | `/api/v1/tts` | Generate speech |
| `GET` | `/api/v1/audio/{id}` | Download generated audio |
| `GET` | `/healthz` | Health check |

Full interactive docs: http://localhost:8000/docs

---

## Recording Protocol

The guided protocol captures diverse phonemes and speaking styles:

| Section | Target Duration | Content |
|---------|----------------|---------|
| Warmup | 2 min | Simple sentences, tongue twisters |
| Storybook | 10 min | Short adventure story |
| Numbers & Data | 2 min | Dates, currencies, measurements |
| Assistant Style | 3 min | Natural assistant phrases |
| Expressive Speech | 3 min | Excited, curious, serious, narration |

**Total: ~20 minutes** of recordings for best quality.  
Minimum: **10 minutes**.

---

## Recording Quality Requirements

| Setting | Value |
|---------|-------|
| Sample rate | 24 000 Hz |
| Format | WAV (PCM-16) |
| Channels | Mono |

---

## Running Tests

```bash
python -m pytest tests/ -v
```

Tests are self-contained — no PyTorch, TTS, or audio hardware required.

---

## TTS Model

Default: **Coqui XTTS v2** (`tts_models/multilingual/multi-dataset/xtts_v2`)

Override via environment variable:

```bash
TTS_MODEL_NAME=tts_models/multilingual/multi-dataset/xtts_v2
TTS_DEVICE=cuda   # or cpu
```

The model is downloaded automatically on first use (~1.8 GB).

---

## GPU Support

Set `TTS_DEVICE=cuda` in your environment or `docker-compose.yml` and ensure PyTorch is installed with CUDA support:

```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

---

## Performance Goals

| Metric | Target |
|--------|--------|
| Speech latency | < 2 seconds (GPU) |
| Voice similarity | > 85% |
| MOS quality | > 4.0 |

---

## Security Notes

- The API is intended for **local use only**. Do not expose it to the public internet without adding authentication.
- Consider adding a **voice ownership confirmation** step before creating embeddings.
