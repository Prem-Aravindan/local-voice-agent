# ⚙️ Configuration Reference

All application behaviour can be controlled through environment variables. This document explains each setting and the `config.py` module that reads them.

---

## Table of Contents

- [How Configuration Works](#how-configuration-works)
- [Directory Paths](#directory-paths)
- [Database Settings](#database-settings)
- [Audio Settings](#audio-settings)
- [TTS / ML Settings](#tts--ml-settings)
- [Recording Protocol](#recording-protocol)
- [Setting Environment Variables](#setting-environment-variables)
- [config.py at a Glance](#configpy-at-a-glance)

---

## How Configuration Works

> 📂 Source: `backend/app/config.py`

The `config.py` module reads values from environment variables with sensible defaults. There is no complex framework — it is plain Python with `os.getenv()`.

```python
# Pattern used throughout config.py:
SOME_SETTING = os.getenv("SOME_SETTING", "default_value")
```

All other modules import from `config.py`:

```python
from app.config import settings
# or
from app.config import SAMPLE_RATE, TTS_MODEL_NAME, …
```

---

## Directory Paths

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `{repo_root}/data` | Root directory for all audio files and embeddings |
| `LOGS_DIR` | `{repo_root}/logs` | Application log output directory |

The following subdirectories are derived from `DATA_DIR` and **cannot** be individually overridden (they are always relative to `DATA_DIR`):

| Path | Purpose |
|------|---------|
| `DATA_DIR/voices/` | Per-voice metadata subdirectories |
| `DATA_DIR/recordings/` | Raw and cleaned WAV recordings |
| `DATA_DIR/embeddings/` | Speaker embedding `.pt` files |
| `DATA_DIR/models/` | Downloaded TTS model weights |
| `DATA_DIR/generated/` | Synthesised speech WAV output |

All directories are created automatically on server startup (`ensure_dirs()` in `main.py`).

---

## Database Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./database/app.db` | SQLAlchemy database connection string |

**Examples:**

```bash
# SQLite (default, zero configuration)
DATABASE_URL=sqlite:///./database/app.db

# SQLite with absolute path
DATABASE_URL=sqlite:////home/user/voice-agent/database/app.db

# PostgreSQL
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/voiceagent
```

> ⚠️ The `database/` directory must exist and be writable. Create it with `mkdir -p database` if needed.

---

## Audio Settings

These settings control the recording and synthesis format. They are fixed constants in `config.py` — they are **not** configurable via environment variables because changing them would break compatibility with existing recordings and the XTTS v2 model.

| Constant | Value | Description |
|----------|-------|-------------|
| `SAMPLE_RATE` | `24_000` Hz | Matches XTTS v2's native sample rate |
| `AUDIO_CHANNELS` | `1` | Mono audio (XTTS v2 requirement) |
| `AUDIO_BIT_DEPTH` | `16` | PCM 16-bit encoding |

> 🔑 XTTS v2 was trained on 24 kHz mono audio. Using any other sample rate will degrade voice quality. The `DatasetBuilder` resamples uploaded recordings to 24 kHz automatically.

---

## TTS / ML Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `TTS_MODEL_NAME` | `tts_models/multilingual/multi-dataset/xtts_v2` | Coqui TTS model identifier |
| `TTS_DEVICE` | `cpu` | PyTorch compute device: `cpu` or `cuda` |

**`TTS_DEVICE` options:**

| Value | When to use | Synthesis latency |
|-------|------------|------------------|
| `cpu` | Default; works everywhere | ~5–10 sec per 10 sec of speech |
| `cuda` | NVIDIA GPU with ≥ 4 GB VRAM | ~1–2 sec per 10 sec of speech |

**Model download:**  
On the first TTS request, the Coqui library downloads the model weights (~1.8 GB) from Hugging Face into `DATA_DIR/models/`. Subsequent requests use the cached weights.

To pre-download the model:
```bash
tts --model_name tts_models/multilingual/multi-dataset/xtts_v2 \
    --list_models
```

---

## Recording Protocol

The `RECORDING_PROTOCOL` dictionary in `config.py` defines the exact prompts shown to users on the recording page. It is exposed via `GET /api/v1/voice/protocol`.

```python
RECORDING_PROTOCOL = {
    "warmup": [
        # Simple sentences; get the speaker comfortable with the recording setup
        "The quick brown fox jumps over the lazy dog.",
        "…",
    ],
    "storybook": [
        # Extended narrative; captures natural rhythm and pacing
        "Once upon a time in a small coastal village…",
        "…",
    ],
    "numbers": [
        # Numbers, dates, measurements; critical for TTS accuracy on numeric data
        "The meeting is scheduled for March 15th at 2:30 PM.",
        "…",
    ],
    "assistant": [
        # Conversational phrases typical of a voice assistant
        "Sure! I can help you with that right away.",
        "…",
    ],
    "expressive": [
        # Emotional range; improves naturalness across different contexts
        "I can't believe we actually did it! This is amazing!",
        "…",
    ],
}
```

**Protocol design rationale:**

| Section | Duration target | Why it matters |
|---------|----------------|----------------|
| Warmup | ~2 min | Covers all phonemes; warms up the speaker |
| Storybook | ~10 min | Bulk of the training data; natural speaking pace |
| Numbers | ~2 min | Numeric pronunciation is often different from prose |
| Assistant | ~3 min | Conversational tone used in most TTS applications |
| Expressive | ~3 min | Emotional range; prevents flat/robotic output |

To customise the prompts, edit `RECORDING_PROTOCOL` in `config.py` and restart the server. The frontend fetches prompts from the API and will reflect your changes immediately.

---

## Setting Environment Variables

### Option 1 — Shell export

```bash
export TTS_DEVICE=cuda
export DATA_DIR=/mnt/external-drive/voice-data
uvicorn app.main:app
```

### Option 2 — `.env` file with python-dotenv

If `python-dotenv` is installed, create a `.env` file in the `backend/` directory:

```bash
# backend/.env
DATABASE_URL=sqlite:///./database/app.db
DATA_DIR=./data
TTS_DEVICE=cpu
TTS_MODEL_NAME=tts_models/multilingual/multi-dataset/xtts_v2
```

### Option 3 — Docker Compose

```yaml
# docker-compose.yml
services:
  backend:
    environment:
      DATABASE_URL: sqlite:///./database/app.db
      DATA_DIR: /app/data
      TTS_DEVICE: cpu
```

---

## config.py at a Glance

```python
# backend/app/config.py  — annotated summary

import os
from pathlib import Path

# ── Root paths ───────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[3]   # repo root
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
LOGS_DIR = Path(os.getenv("LOGS_DIR", BASE_DIR / "logs"))

# ── Data subdirectories ──────────────────────────────────────
VOICES_DIR     = DATA_DIR / "voices"
RECORDINGS_DIR = DATA_DIR / "recordings"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
MODELS_DIR     = DATA_DIR / "models"
GENERATED_DIR  = DATA_DIR / "generated"

# ── Database ─────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'database' / 'app.db'}"
)

# ── Audio constants (do not change without retraining) ───────
SAMPLE_RATE    = 24_000   # Hz  — XTTS v2 native rate
AUDIO_CHANNELS = 1        # Mono
AUDIO_BIT_DEPTH = 16      # PCM-16

# ── TTS / ML ──────────────────────────────────────────────────
TTS_MODEL_NAME = os.getenv(
    "TTS_MODEL_NAME",
    "tts_models/multilingual/multi-dataset/xtts_v2"
)
TTS_DEVICE = os.getenv("TTS_DEVICE", "cpu")

# ── Recording protocol prompts ───────────────────────────────
RECORDING_PROTOCOL = { … }   # see full source for all prompts
```
