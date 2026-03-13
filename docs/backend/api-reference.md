# 📡 API Reference

All endpoints are served under the base path **`/api/v1`**.

> Interactive docs (Swagger UI): http://localhost:8000/docs  
> ReDoc alternative: http://localhost:8000/redoc

---

## Table of Contents

- [Legend](#legend)
- [Voice Management](#voice-management)
  - [List Voices](#get-voices)
  - [Create Voice](#post-voicecreate)
  - [Get Voice](#get-voicevoice_id)
  - [Delete Voice](#delete-voicevoice_id)
  - [Train Voice](#post-voicevoice_idtrain)
  - [Get Recording Protocol](#get-voiceprotocol)
  - [Start Recording](#post-voicerecordstart)
  - [Stop Recording](#post-voicerecordstop)
  - [Upload Sample](#post-voicesample)
- [Text-to-Speech](#text-to-speech)
  - [Generate Speech](#post-tts)
- [Audio Download](#audio-download)
  - [Download Audio](#get-audioaudio_id)
- [Health Check](#get-healthz)

---

## Legend

```
● Required field
○ Optional field
→ Returns
```

| Symbol | Meaning |
|--------|---------|
| `[str]` | String field |
| `[int]` | Integer field |
| `[float]` | Float field |
| `[enum]` | One of a fixed set of values |
| `[uuid]` | UUID string |
| `[ts]` | ISO 8601 timestamp |

---

## Voice Management

> 📂 Source: `backend/app/api/voices.py`

---

### `GET /voices`

List all voice profiles.

**Response `200`**

```json
[
  {
    "voice_id":      "[uuid]",           // Unique voice identifier
    "name":          "[str]",            // Human-readable name
    "description":   "[str | null]",     // Optional description
    "status":        "pending|ready|failed",
    "embedding_path":"[str | null]",     // Path to .pt file once trained
    "samples_path":  "[str | null]",     // Path to recordings directory
    "created_at":    "[ts]"
  }
]
```

Returns an empty array `[]` when no voices have been created yet.

---

### `POST /voice/create`

Create a new voice profile. The voice starts with `status = "pending"` until trained.

**Request body**

```json
{
  "name":        "[str]",    // ● Unique name for this voice
  "description": "[str]"     // ○ Free-text description
}
```

**Response `201`**

```json
{
  "voice_id":      "[uuid]",
  "name":          "[str]",
  "description":   "[str | null]",
  "status":        "pending",
  "embedding_path": null,
  "samples_path":  "[str]",
  "created_at":    "[ts]"
}
```

**Error `409`** — A voice with the same name already exists.

---

### `GET /voice/{voice_id}`

Retrieve details for a single voice profile.

**Path parameter:** `voice_id` — UUID of the voice.

**Response `200`** — Same shape as a single item from `GET /voices`.

**Error `404`** — Voice not found.

---

### `DELETE /voice/{voice_id}`

Delete a voice profile and **all associated data**:
- All `Recording` rows in the database
- All WAV files under `data/recordings/{voice_id}/`
- The embedding file at `data/embeddings/{voice_id}/embedding.pt`
- The `Voice` row itself

**Path parameter:** `voice_id` — UUID of the voice.

**Response `204 No Content`** — Deletion successful.

**Error `404`** — Voice not found.

---

### `POST /voice/{voice_id}/train`

Enqueue a background job to build the speaker embedding.

**Path parameter:** `voice_id` — UUID of the voice.

**What happens after this call:**

1. A `TrainingJob` record is created with `status = "queued"`
2. The HTTP response is returned immediately (non-blocking)
3. A background worker picks up the job and processes it asynchronously

**Response `200`**

```json
{
  "job_id":     "[uuid]",
  "voice_id":   "[uuid]",
  "status":     "queued",
  "created_at": "[ts]"
}
```

**Error `404`** — Voice not found.

> 💡 Poll `GET /voice/{voice_id}` and watch `status` change from `pending` → `ready` (or `failed`).

---

### `GET /voice/protocol`

Return the full recording protocol: the structured prompts used to guide voice recording across five sections.

**Response `200`**

```json
{
  "warmup": [
    "The quick brown fox jumps over the lazy dog.",
    "…"
  ],
  "storybook": ["…"],
  "numbers":   ["…"],
  "assistant": ["…"],
  "expressive":["…"]
}
```

This data comes directly from `config.py → RECORDING_PROTOCOL`.

---

### `POST /voice/record/start`

Start a **live microphone** recording session.

> ⚠️ Only one recording can be active at a time. A second call while a session is active returns an error.

**Request body**

```json
{
  "voice_id": "[uuid]",   // ● Which voice profile to record for
  "section":  "[enum]"    // ● warmup | storybook | numbers | assistant | expressive
}
```

**Response `200`**

```json
{
  "is_recording": true,
  "voice_id":     "[uuid]",
  "section":      "[str]",
  "started_at":   "[ts]"
}
```

**Error `400`** — Recording already in progress or microphone unavailable.

---

### `POST /voice/record/stop`

Stop the active microphone recording and persist the WAV file.

**Response `200`**

```json
{
  "is_recording":    false,
  "voice_id":        "[uuid]",
  "section":         "[str]",
  "file_path":       "[str]",      // Absolute path to saved WAV
  "duration_seconds":"[float]"     // Length of the recording
}
```

**Error `400`** — No recording is currently active.

---

### `POST /voice/sample`

Upload a pre-recorded WAV file as a voice sample.  
Use this as an alternative to live recording.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `voice_id` | string (form) | ✅ | Voice to associate the sample with |
| `section` | string (form) | ✅ | `warmup \| storybook \| numbers \| assistant \| expressive` |
| `file` | file (WAV) | ✅ | The audio file to upload |

**Audio requirements:**

| Parameter | Required value |
|-----------|---------------|
| Format | WAV (PCM) |
| Sample rate | 24 000 Hz (will be resampled if different) |
| Channels | Mono preferred |

**Response `201`**

```json
{
  "recording_id":    "[uuid]",
  "voice_id":        "[uuid]",
  "file_path":       "[str]",
  "duration_seconds":"[float]",
  "section":         "[str]",
  "created_at":      "[ts]"
}
```

---

## Text-to-Speech

> 📂 Source: `backend/app/api/tts.py`

---

### `POST /tts`

Synthesise speech from text using a trained voice.

> ⚠️ The voice must have `status == "ready"` before this call will succeed.

**Request body**

```json
{
  "voice_id":    "[uuid]",    // ● The trained voice to use
  "text":        "[str]",     // ● Text to synthesise (1–5000 characters)
  "language":    "[str]",     // ○ ISO 639-1 code, default "en"
  "speed":       "[float]",   // ○ Playback rate 0.1–3.0, default 1.0
  "temperature": "[float]"    // ○ Randomness 0.0–1.0, default 0.7
}
```

**Supported languages**

| Code | Language |
|------|----------|
| `en` | English |
| `es` | Spanish |
| `fr` | French |
| `de` | German |
| `it` | Italian |
| `pt` | Portuguese |
| `zh-cn` | Mandarin Chinese |
| `ja` | Japanese |
| *(and more)* | See XTTS v2 docs |

**Temperature guide**

| Value | Effect |
|-------|--------|
| 0.1 – 0.3 | Very consistent, robotic-sounding |
| 0.5 – 0.7 | Natural variation (recommended) |
| 0.8 – 1.0 | More expressive but less predictable |

**Response `201`**

```json
{
  "audio_id":    "[uuid]",    // Use this to download the audio
  "voice_id":    "[uuid]",
  "text":        "[str]",
  "file_path":   "[str]",
  "speed":       "[float]",
  "temperature": "[float]",
  "created_at":  "[ts]"
}
```

**Error `404`** — Voice not found.  
**Error `400`** — Voice is not yet trained (`status != "ready"`).

---

## Audio Download

> 📂 Source: `backend/app/api/audio.py`

---

### `GET /audio/{audio_id}`

Download a previously generated audio file as a WAV.

**Path parameter:** `audio_id` — UUID returned by `POST /tts`.

**Response `200`** — `Content-Type: audio/wav`, binary WAV file body.

**Error `404`** — Audio record not found or WAV file missing from disk.

---

## `GET /healthz`

Simple liveness check. Used by Docker health checks and monitoring tools.

**Response `200`**

```json
{
  "status":  "ok",
  "version": "1.0.0"
}
```
