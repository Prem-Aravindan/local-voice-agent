# 🐳 Deployment Guide

This document covers all deployment options — from local Docker Compose to production hardening.

---

## Table of Contents

- [Docker Compose (recommended)](#docker-compose-recommended)
  - [How It Works](#how-it-works)
  - [Volumes](#volumes)
  - [Customising the Compose File](#customising-the-compose-file)
- [Manual Deployment (without Docker)](#manual-deployment-without-docker)
- [GPU Support](#gpu-support)
- [Production Hardening](#production-hardening)
  - [Reverse Proxy with nginx](#reverse-proxy-with-nginx)
  - [Authentication](#authentication)
  - [PostgreSQL Instead of SQLite](#postgresql-instead-of-sqlite)
  - [Process Management](#process-management)
  - [Monitoring and Logging](#monitoring-and-logging)
- [Environment Variables Reference](#environment-variables-reference)
- [Docker Images](#docker-images)
  - [Backend Dockerfile](#backend-dockerfile)
  - [Frontend Dockerfile](#frontend-dockerfile)

---

## Docker Compose (recommended)

### How It Works

```bash
# From the repository root:
docker compose up
```

Docker Compose starts two containers and wires them together:

```
┌──────────────────────────┐     HTTP      ┌──────────────────────────┐
│  frontend (Node.js)      │ ───────────►  │  backend (Python)        │
│  http://localhost:3000   │               │  http://localhost:8000   │
└──────────────────────────┘               └──────────────────────────┘
                                                         │
                                                  ┌──────▼──────┐
                                                  │  data/      │
                                                  │  database/  │
                                                  │  logs/      │
                                                  └─────────────┘
                                                  (bind-mounted volumes)
```

**Service dependencies:** The frontend container waits for the backend to be healthy before starting (controlled by `depends_on`).

### Volumes

| Volume | Host path | Container path | Purpose |
|--------|-----------|----------------|---------|
| `data` | `./data` | `/app/data` | Audio files and embeddings |
| `database` | `./database` | `/app/database` | SQLite database file |
| `logs` | `./logs` | `/app/logs` | Application logs |

Data persists across container restarts because it is bind-mounted to the host filesystem.

### Customising the Compose File

```yaml
# docker-compose.yml — key sections to customise

services:
  backend:
    build:
      context: ./backend
      dockerfile: ../docker/Dockerfile.backend
    ports:
      - "8000:8000"           # Change first number to use a different host port
    environment:
      TTS_DEVICE: cpu         # Change to "cuda" to enable GPU
      DATA_DIR: /app/data
      DATABASE_URL: sqlite:///./database/app.db
    volumes:
      - ./data:/app/data
      - ./database:/app/database
      - ./logs:/app/logs

  frontend:
    build:
      context: ./frontend
      dockerfile: ../docker/Dockerfile.frontend
      args:
        NEXT_PUBLIC_API_BASE: http://localhost:8000/api/v1   # ← Update if backend URL changes
    ports:
      - "3000:3000"
    depends_on:
      - backend
```

---

## Manual Deployment (without Docker)

### Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set required environment variables
export DATABASE_URL=sqlite:///./database/app.db
export DATA_DIR=./data

# Run database migrations
alembic upgrade head

# Start the production server with multiple workers
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2          # Use 1 if running TTS (model is not multi-process safe)
```

> ⚠️ **Worker count:** XTTS v2 loads the model into memory. With multiple workers, each worker loads its own copy, multiplying VRAM/RAM usage. Keep `--workers 1` unless you are not using TTS.

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Build the production bundle
npm run build

# Start the production server
npm start                 # Default: http://localhost:3000
```

---

## GPU Support

Enabling CUDA reduces TTS synthesis latency from ~10 seconds to ~2 seconds.

### Requirements

- NVIDIA GPU with ≥ 4 GB VRAM
- CUDA toolkit (version matching your PyTorch wheel)
- `nvidia-docker` for Docker GPU support

### CPU → CUDA Migration Steps

```bash
# 1. Uninstall CPU-only PyTorch
pip uninstall torch torchaudio

# 2. Install CUDA-enabled PyTorch (adjust cu121 to match your CUDA version)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121

# 3. Set the device
export TTS_DEVICE=cuda
```

### Docker GPU

In `docker-compose.yml`:

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

Verify GPU is visible inside the container:

```bash
docker compose exec backend python -c "import torch; print(torch.cuda.is_available())"
# Expected: True
```

---

## Production Hardening

> ⚠️ The default setup is designed for **local use only**. Follow these steps before exposing the application to a network.

### Reverse Proxy with nginx

Place nginx in front of both services to handle TLS, rate limiting, and routing:

```nginx
# /etc/nginx/sites-available/voice-agent

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;

        # Increase timeout for long TTS synthesis requests
        proxy_read_timeout 120s;
    }

    # Limit upload size for audio samples (~100 MB max)
    client_max_body_size 100M;
}
```

### Authentication

The application has **no authentication layer**. Before exposing it publicly, add one of:

| Option | Complexity | Notes |
|--------|-----------|-------|
| HTTP Basic Auth (nginx) | Low | Simple username/password gate |
| OAuth 2.0 / OIDC (e.g. Auth0) | Medium | Full user management |
| JWT middleware (FastAPI) | Medium | Add `fastapi-users` or custom dependency |

### PostgreSQL Instead of SQLite

For multi-user or high-concurrency deployments:

```bash
# 1. Install the driver
pip install psycopg2-binary

# 2. Update the connection string
export DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/voiceagent

# 3. Run migrations
alembic upgrade head
```

### Process Management

Use `systemd` or `supervisor` to keep the server running after reboots:

```ini
# /etc/systemd/system/voice-agent-backend.service
[Unit]
Description=Voice Agent Backend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/local-voice-agent/backend
Environment="TTS_DEVICE=cpu"
ExecStart=/home/ubuntu/local-voice-agent/backend/.venv/bin/uvicorn \
          app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable voice-agent-backend
sudo systemctl start  voice-agent-backend
```

### Monitoring and Logging

- **Application logs:** Written to `LOGS_DIR` (default `./logs/`)
- **Structured logging:** Consider replacing `logging` with `structlog` for JSON log output
- **Metrics:** Add a Prometheus exporter (e.g. `prometheus-fastapi-instrumentator`)
- **Alerts:** Set up alerts on error rates and synthesis latency

---

## Environment Variables Reference

A complete reference is in the [Configuration guide](./backend/configuration.md). Key variables for deployment:

| Variable | Recommended production value |
|----------|------------------------------|
| `DATABASE_URL` | `postgresql+psycopg2://…` or absolute SQLite path |
| `DATA_DIR` | Absolute path on persistent storage |
| `TTS_DEVICE` | `cuda` if GPU available, else `cpu` |
| `NEXT_PUBLIC_API_BASE` | Your public backend URL (e.g. `https://your-domain.com/api/v1`) |

---

## Docker Images

### Backend Dockerfile

> 📂 Source: `docker/Dockerfile.backend`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    libportaudio2 \        # sounddevice microphone support
    libsndfile1 \          # soundfile WAV I/O
    ffmpeg \               # audio format conversion
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create runtime directories
RUN mkdir -p /app/data /app/database /app/logs

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile

> 📂 Source: `docker/Dockerfile.frontend`

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

# Build-time API URL injection
ARG NEXT_PUBLIC_API_BASE=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE}

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage — smaller image
FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000
CMD ["npm", "start"]
```

> 💡 `NEXT_PUBLIC_API_BASE` is baked into the JavaScript bundle at **build time**. If you need to change the backend URL after the image is built, you must rebuild the frontend image.
