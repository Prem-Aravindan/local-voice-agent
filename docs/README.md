# 📚 Local Voice Agent — Documentation

> **Who this is for:** Anyone who wants to understand, use, extend, or contribute to the Local Voice Agent codebase — from complete beginners to experienced engineers.

---

## What Is This Project?

**Local Voice Agent** is a fully local, privacy-first application that lets you:

1. **Record** your own voice following a structured protocol
2. **Clone** your voice by extracting a speaker embedding (ML model)
3. **Synthesise** natural speech from any text using that cloned voice

Everything runs on your own hardware — no cloud services, no API keys, no data leaving your machine.

---

## 🗺️ Documentation Map

| Document | What you will learn |
|----------|---------------------|
| **[Architecture](./architecture.md)** | How all components fit together; data-flow diagrams |
| **[Getting Started](./getting-started.md)** | Install, configure, and run the app locally or with Docker |
| **Backend** | |
| ↳ [Overview](./backend/overview.md) | Package structure and design principles |
| ↳ [API Reference](./backend/api-reference.md) | Every HTTP endpoint: method, URL, request/response |
| ↳ [Database](./backend/database.md) | Schema, ORM models, relationships, migrations |
| ↳ [Services](./backend/services.md) | Business-logic layer (VoiceService, TTSService) |
| ↳ [Voice Engine](./backend/voice-engine.md) | ML/audio pipeline — recorder, preprocessing, embedding, TTS |
| ↳ [Configuration](./backend/configuration.md) | All environment variables and the `config.py` module |
| **Frontend** | |
| ↳ [Overview](./frontend/overview.md) | Project structure, tech stack, design decisions |
| ↳ [Pages](./frontend/pages.md) | UX flows for each page and their components |
| ↳ [API Client](./frontend/api-client.md) | TypeScript API utility layer |
| **[Deployment](./deployment.md)** | Docker Compose, GPU support, production hardening |
| **[Contributing](./contributing.md)** | Development workflow, testing, code conventions |

---

## ⚡ 30-Second Overview

```
┌─────────────────────────────────────────────────────┐
│                   Browser (Next.js)                  │
│  /voices  ──  /record  ──  /generate                 │
└────────────────────┬────────────────────────────────┘
                     │  HTTP (REST JSON / WAV)
┌────────────────────▼────────────────────────────────┐
│               FastAPI  (Python)                      │
│  /api/v1/voice/*   /api/v1/tts   /api/v1/audio/*     │
└──────┬─────────────┬─────────────────────┬──────────┘
       │             │                     │
 SQLite DB     data/ filesystem      ML models
 (metadata)  (WAV recordings,       (Coqui XTTS v2
              embeddings,            ~1.8 GB)
              generated audio)
```

---

## 🧭 Legend used throughout the docs

| Symbol | Meaning |
|--------|---------|
| ✅ | Recommended / best-practice path |
| ⚠️ | Warning — read before proceeding |
| 💡 | Tip or insight |
| 🔑 | Key concept |
| 📂 | File / directory reference |
| 🔗 | External dependency / link |

---

## Tech Stack at a Glance

| Layer | Technology | Why chosen |
|-------|-----------|-----------|
| Backend API | FastAPI (Python) | Async, type-safe, auto-generates OpenAPI docs |
| ML / TTS | Coqui XTTS v2 | State-of-the-art open-source multilingual voice cloning |
| Audio I/O | sounddevice, librosa, soundfile | Portable, cross-platform audio capture and processing |
| Database | SQLite + SQLAlchemy | Zero-config, file-based, perfect for local-first apps |
| DB Migrations | Alembic | Incremental, version-controlled schema changes |
| Frontend | Next.js 15 (React 18) | File-based routing, SSR, React ecosystem |
| Styling | Tailwind CSS 3 | Utility-first, rapid UI development |
| Containers | Docker Compose | One-command startup, reproducible environment |
| Testing | pytest | Standard Python testing framework |
