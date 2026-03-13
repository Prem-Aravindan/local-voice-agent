# ⚙️ Services Layer

The services layer is the **business logic** of the application. It sits between the HTTP routers (which understand requests and responses) and the storage layer (database + filesystem). Neither the API routers nor the voice engine need to know about each other — they communicate only through services.

---

## Table of Contents

- [Why a Service Layer?](#why-a-service-layer)
- [VoiceService](#voiceservice)
  - [Voice CRUD](#voice-crud)
  - [Recording Management](#recording-management)
  - [Training Job Lifecycle](#training-job-lifecycle)
  - [Embedding Persistence](#embedding-persistence)
- [TTSService](#ttsservice)
  - [Speech Generation](#speech-generation)
  - [Audio Retrieval](#audio-retrieval)

---

## Why a Service Layer?

Without a service layer, business rules end up scattered across API handlers, making them hard to test and reuse. Services:

- Keep API handlers **thin** (validate input, call service, return response)
- Are independently **testable** without an HTTP server
- Centralise **all database writes** in one place
- Can be called from both HTTP handlers **and** background workers

---

## VoiceService

> 📂 Source: `backend/app/services/voice_service.py`

All methods are `@staticmethod` — no instance needed, just import and call.

```python
from app.services.voice_service import VoiceService
```

---

### Voice CRUD

#### `create_voice(db, name, description=None) → Voice`

Creates a new voice profile and sets up its directory structure on disk.

**Steps:**
1. Generate a UUID for the voice
2. Create directory `data/recordings/{voice_id}/` for future recordings
3. `INSERT INTO voices (voice_id, name, description, status="pending", samples_path)`
4. Return the new `Voice` ORM object

**Raises:** `ValueError` if a voice with the same name already exists.

---

#### `get_voice(db, voice_id) → Voice | None`

Fetches a single voice by its UUID. Returns `None` if not found.

---

#### `get_voice_by_name(db, name) → Voice | None`

Fetches a voice by its unique name. Returns `None` if not found.

---

#### `list_voices(db) → List[Voice]`

Returns all voice profiles ordered by `created_at` descending (newest first).

---

#### `delete_voice(db, voice_id) → bool`

Deletes a voice and **all associated data**:

1. Load the `Voice` record
2. Delete all `Recording` rows for this voice
3. Delete WAV files under `data/recordings/{voice_id}/`
4. Delete the embedding at `data/embeddings/{voice_id}/embedding.pt`
5. `DELETE FROM voices WHERE voice_id = …`

Returns `True` on success, `False` if the voice was not found.

---

### Recording Management

#### `add_recording(db, voice_id, file_path, duration_seconds, section) → Recording`

Persists metadata for a WAV file that was just saved to disk.

**Steps:**
1. Verify the voice exists (raises `ValueError` if not)
2. `INSERT INTO recordings (recording_id, voice_id, file_path, duration_seconds, section)`
3. Return the new `Recording` ORM object

---

#### `list_recordings(db, voice_id) → List[Recording]`

Returns all recordings for a voice, ordered by `created_at` ascending (oldest first).

---

### Training Job Lifecycle

#### `create_training_job(db, voice_id) → TrainingJob`

Creates a new job record in `queued` state.

```python
job = VoiceService.create_training_job(db, voice_id)
# job.status == "queued"
```

---

#### `update_job_status(db, job_id, status, error_message=None) → TrainingJob`

Updates the job status and optionally records an error. Sets `completed_at` to the current UTC time when status is `"done"` or `"failed"`.

```python
# On success
VoiceService.update_job_status(db, job_id, "done")

# On failure
VoiceService.update_job_status(db, job_id, "failed",
    error_message="Dataset build returned no samples")
```

---

### Embedding Persistence

#### `set_embedding_path(db, voice_id, embedding_path) → Voice`

Called by the background worker after a successful embedding extraction.

**Steps:**
1. `UPDATE voices SET embedding_path = …, status = "ready"`
2. Write `data/embeddings/{voice_id}/metadata.json` with voice details (useful for external tools and debugging)
3. Return the updated `Voice` object

**`metadata.json` contents:**

```json
{
  "voice_id": "…",
  "name": "…",
  "status": "ready",
  "embedding_path": "…",
  "samples_path": "…",
  "created_at": "…"
}
```

---

## TTSService

> 📂 Source: `backend/app/services/tts_service.py`

---

### Speech Generation

#### `generate(db, voice_id, text, language, speed, temperature) → GeneratedAudio`

Orchestrates the full TTS pipeline:

```
TTSService.generate()
    │
    ▼
1. Retrieve the Voice record from DB
   └── Raises ValueError if voice not found or status != "ready"
    │
    ▼
2. Generate a new audio_id (UUID)
    │
    ▼
3. Determine output path:
   data/generated/{voice_id}/{audio_id}.wav
    │
    ▼
4. TTSEngine.synthesise(
       text         = text,
       embedding_path = voice.embedding_path,
       output_path    = output_path,
       language       = language,
       speed          = speed,
       temperature    = temperature
   )
    │
    ▼
5. INSERT INTO generated_audio (audio_id, voice_id, text, file_path, speed, temperature)
    │
    ▼
6. Return GeneratedAudio ORM object
```

**Why does the service hold the TTSEngine instance?**

The `TTSEngine` is expensive to initialise (loads ~1.8 GB of model weights). The service module keeps a **module-level singleton**:

```python
# tts_service.py
_engine: TTSEngine | None = None

def _get_engine() -> TTSEngine:
    global _engine
    if _engine is None:
        _engine = TTSEngine(model_name=settings.TTS_MODEL_NAME,
                            device=settings.TTS_DEVICE)
    return _engine
```

This ensures the model is loaded only once per process, regardless of how many concurrent TTS requests arrive.

---

### Audio Retrieval

#### `get_audio(db, audio_id) → GeneratedAudio | None`

Looks up a `GeneratedAudio` record by its UUID. Returns `None` if not found.

Used by `GET /api/v1/audio/{audio_id}` to resolve the file path before serving the WAV.
