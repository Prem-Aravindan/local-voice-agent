# 🚀 Getting Started

This guide walks you from a fresh clone to a running application.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Option A — Docker Compose (recommended)](#option-a--docker-compose-recommended)
- [Option B — Manual Local Setup](#option-b--manual-local-setup)
  - [Backend](#backend)
  - [Frontend](#frontend)
- [Verify the Installation](#verify-the-installation)
- [First-Run Walkthrough](#first-run-walkthrough)
- [Environment Variables](#environment-variables)
- [GPU Acceleration](#gpu-acceleration)
- [Common Problems](#common-problems)

---

## Prerequisites

| Requirement | Minimum version | Notes |
|-------------|----------------|-------|
| **Git** | Any | `git clone` the repo |
| **Docker + Docker Compose** | Docker 24 / Compose v2 | For Option A |
| **Python** | 3.10+ | For Option B backend |
| **Node.js** | 18+ | For Option B frontend |
| **Disk space** | ≥ 5 GB | TTS model ~1.8 GB, Docker layers ~1 GB |
| **RAM** | ≥ 8 GB | XTTS v2 runs in-process |
| **Microphone** | Any | Required for live recording |

---

## Option A — Docker Compose (recommended)

This is the **fastest and most reproducible** way to run the application.

```bash
# 1. Clone the repository
git clone https://github.com/Prem-Aravindan/local-voice-agent.git
cd local-voice-agent

# 2. Start all services
docker compose up
```

Docker Compose starts two containers:

| Container | URL | Description |
|-----------|-----|-------------|
| `backend` | http://localhost:8000 | FastAPI server |
| `frontend` | http://localhost:3000 | Next.js web UI |

> ⚠️ **First run:** The backend will automatically download the Coqui XTTS v2 model (~1.8 GB) on the first TTS request. This is a one-time download stored in `data/models/`.

To stop:
```bash
docker compose down
```

To rebuild after code changes:
```bash
docker compose up --build
```

---

## Option B — Manual Local Setup

### Backend

```bash
# 1. Go to the backend directory
cd backend

# 2. Create a virtual environment (keeps dependencies isolated)
python -m venv .venv

# 3. Activate it
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows PowerShell

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Start the API server with auto-reload (for development)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend is now running at http://localhost:8000.  
Interactive API docs: http://localhost:8000/docs

### Frontend

Open a **separate terminal**:

```bash
# 1. Go to the frontend directory
cd frontend

# 2. Install Node.js dependencies
npm install

# 3. Start the development server
npm run dev
```

The frontend is now running at http://localhost:3000.

---

## Verify the Installation

Once both services are running, run these quick checks:

```bash
# 1. Health check
curl http://localhost:8000/healthz
# Expected:  {"status":"ok","version":"1.0.0"}

# 2. List voices (empty on a fresh install)
curl http://localhost:8000/api/v1/voices
# Expected:  []

# 3. Open the interactive API docs
open http://localhost:8000/docs      # macOS
xdg-open http://localhost:8000/docs  # Linux
```

---

## First-Run Walkthrough

Follow these steps to create and use your first cloned voice:

### Step 1 — Create a voice profile

1. Open http://localhost:3000/voices
2. Enter a **Name** (e.g. "My Voice") and optional description
3. Click **Create** → the voice appears in the list with status `pending`

### Step 2 — Record samples

1. Navigate to http://localhost:3000/record
2. Select your voice profile from the dropdown
3. Work through the five recording **sections**:

   | Section | Target duration | Purpose |
   |---------|----------------|---------|
   | Warmup | ~2 min | Loosen up, simple sentences |
   | Storybook | ~10 min | Extended narrative speech |
   | Numbers & Data | ~2 min | Digits, dates, measurements |
   | Assistant Style | ~3 min | Natural conversational phrases |
   | Expressive Speech | ~3 min | Excited, serious, curious tone |

4. Click **Start Recording** before each prompt, read it aloud, then **Stop**
5. Aim for **10 minutes minimum** (20 minutes ideal) total recorded audio

> 💡 Alternatively, if you already have WAV recordings, use the **Upload Sample** button to skip live recording.

### Step 3 — Train the embedding

1. Go back to http://localhost:3000/voices
2. Find your voice and click **Train**
3. Status changes: `pending` → `running` → `ready` (takes 2–5 min on CPU)

> 💡 Poll the status by refreshing the page or calling `GET /api/v1/voice/{voice_id}` until `status == "ready"`.

### Step 4 — Generate speech

1. Open http://localhost:3000/generate
2. Select your trained voice from the dropdown
3. Enter any text (up to 5 000 characters)
4. Optionally adjust language, speed, and temperature
5. Click **Generate Speech** → an audio player appears
6. Play back or download the generated WAV file

---

## Environment Variables

All configuration is done via environment variables (or a `.env` file in the project root).

### Backend

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./database/app.db` | SQLAlchemy connection string |
| `DATA_DIR` | `./data` | Root directory for all audio/embedding files |
| `LOGS_DIR` | `./logs` | Application log output directory |
| `SAMPLE_RATE` | `24000` | Recording/synthesis sample rate in Hz |
| `TTS_MODEL_NAME` | `tts_models/multilingual/multi-dataset/xtts_v2` | Coqui TTS model identifier |
| `TTS_DEVICE` | `cpu` | Inference device: `cpu` or `cuda` |

### Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_BASE` | `http://localhost:8000/api/v1` | Base URL of the backend API |

Example `.env` file:

```bash
# .env (place in project root or export in shell)
DATABASE_URL=sqlite:///./database/app.db
DATA_DIR=./data
TTS_DEVICE=cpu
NEXT_PUBLIC_API_BASE=http://localhost:8000/api/v1
```

---

## GPU Acceleration

Running the TTS model on a CUDA-capable GPU reduces synthesis latency from ~10 seconds to ~2 seconds.

### Requirements

- NVIDIA GPU with ≥ 4 GB VRAM
- CUDA toolkit installed (version matching your PyTorch wheel)

### Enable GPU

```bash
# Set the device
export TTS_DEVICE=cuda

# Install GPU-enabled PyTorch (example for CUDA 12.1)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

In `docker-compose.yml` add the device under the `backend` service:

```yaml
services:
  backend:
    environment:
      TTS_DEVICE: cuda
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

---

## Common Problems

### `sounddevice` not found / microphone not working

```
OSError: No Default Input Device Available
```

- **Cause:** The audio device library cannot find a microphone.
- **Fix (Linux):** Install PortAudio: `sudo apt install libportaudio2`
- **Fix (macOS):** Grant microphone permission in System Preferences → Security & Privacy.
- **Workaround:** Use the **Upload Sample** endpoint to upload pre-recorded WAV files instead of live recording.

### Model download takes a long time

The first TTS request downloads ~1.8 GB from Hugging Face. This is **normal**. Subsequent requests use the cached model.

### `database/app.db` permission errors

Ensure the `database/` directory exists and is writable:

```bash
mkdir -p database
```

### Frontend can't reach the backend

Check that `NEXT_PUBLIC_API_BASE` points to the correct host. The default `http://localhost:8000/api/v1` only works when both services are on the same machine.

### Docker build fails with `pip install` errors

```bash
# Rebuild without layer cache
docker compose build --no-cache
```
