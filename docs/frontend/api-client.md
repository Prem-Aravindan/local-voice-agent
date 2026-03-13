# 🔌 Frontend API Client

All HTTP communication between the frontend and backend is centralised in a single file.

> 📂 Source: `frontend/app/lib/api.ts`

---

## Table of Contents

- [Why Centralise API Calls?](#why-centralise-api-calls)
- [Base URL Configuration](#base-url-configuration)
- [TypeScript Types](#typescript-types)
- [API Methods](#api-methods)
- [Error Handling](#error-handling)
- [Extending the Client](#extending-the-client)

---

## Why Centralise API Calls?

By putting every `fetch()` call in one file:

- The backend URL is configured in **one place** (`NEXT_PUBLIC_API_BASE`)
- TypeScript types are defined once and reused everywhere
- API errors are handled consistently
- Page components stay clean — they just call `api.listVoices()` instead of writing `fetch(…)` boilerplate

---

## Base URL Configuration

```typescript
// api.ts
const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";
```

Override at build time or in `.env.local`:

```bash
NEXT_PUBLIC_API_BASE=http://my-server:8000/api/v1
```

---

## TypeScript Types

```typescript
// ── Voice profile ────────────────────────────────────────────
interface Voice {
  voice_id:       string;                                // UUID
  name:           string;                                // Unique name
  description:    string | null;                         // Optional notes
  status:         "pending" | "ready" | "failed";        // Training status
  embedding_path: string | null;                         // Path to .pt file
  samples_path:   string | null;                         // Path to recordings dir
  created_at:     string;                                // ISO 8601 timestamp
}

// ── Recording ────────────────────────────────────────────────
interface RecordingRecord {
  recording_id:     string;
  voice_id:         string;
  file_path:        string;
  duration_seconds: number;
  section:          "warmup" | "storybook" | "numbers" | "assistant" | "expressive";
  created_at:       string;
}

// ── Generated audio ──────────────────────────────────────────
interface AudioRecord {
  audio_id:    string;                                   // UUID — used in download URL
  voice_id:    string;
  text:        string;                                   // The input text
  file_path:   string;
  speed:       number;
  temperature: number;
  created_at:  string;
}

// ── TTS request ──────────────────────────────────────────────
interface TTSRequest {
  voice_id:     string;
  text:         string;                // 1–5000 characters
  language?:    string;               // ISO 639-1, default "en"
  speed?:       number;               // 0.1–3.0, default 1.0
  temperature?: number;               // 0.0–1.0, default 0.7
}

// ── Recording protocol ───────────────────────────────────────
type Protocol = Record<string, string[]>;
// e.g. { "warmup": ["sentence…", …], "storybook": […], … }
```

---

## API Methods

### `api.listVoices() → Promise<Voice[]>`

Fetch all voice profiles.

```typescript
const voices = await api.listVoices();
// GET /voices → Voice[]
```

---

### `api.getVoice(voiceId) → Promise<Voice>`

Fetch a single voice by UUID.

```typescript
const voice = await api.getVoice("abc-123");
// GET /voice/abc-123 → Voice
```

---

### `api.createVoice(name, description?) → Promise<Voice>`

Create a new voice profile.

```typescript
const voice = await api.createVoice("Alice", "My assistant voice");
// POST /voice/create  { name, description } → Voice (status: "pending")
```

---

### `api.deleteVoice(voiceId) → Promise<void>`

Delete a voice and all its associated data.

```typescript
await api.deleteVoice("abc-123");
// DELETE /voice/abc-123 → 204 No Content
```

---

### `api.trainVoice(voiceId) → Promise<TrainingJob>`

Enqueue a training job for the voice. Returns immediately; the job runs in the background.

```typescript
const job = await api.trainVoice("abc-123");
// POST /voice/abc-123/train → TrainingJob (status: "queued")
```

Poll `api.getVoice(voiceId)` until `voice.status === "ready"`.

---

### `api.getProtocol() → Promise<Protocol>`

Retrieve the recording protocol prompts.

```typescript
const protocol = await api.getProtocol();
// GET /voice/protocol → { warmup: [...], storybook: [...], ... }

const warmupPrompts = protocol["warmup"];
```

---

### `api.uploadSample(voiceId, file, section) → Promise<RecordingRecord>`

Upload a WAV file as a voice sample.

```typescript
// file can be a File object (from <input type="file">) or a Blob (from MediaRecorder)
const recording = await api.uploadSample("abc-123", audioBlob, "warmup");
// POST /voice/sample  (multipart/form-data) → RecordingRecord
```

---

### `api.generateSpeech(request) → Promise<AudioRecord>`

Synthesise speech from text.

```typescript
const audio = await api.generateSpeech({
  voice_id:    "abc-123",
  text:        "Hello, how can I help you today?",
  language:    "en",
  speed:       1.0,
  temperature: 0.7,
});
// POST /tts → AudioRecord

// Now you can play it:
const url = api.audioUrl(audio.audio_id);
```

---

### `api.audioUrl(audioId) → string`

Returns the URL to stream or download a generated audio file. This is **not** an async call — it just constructs the URL string.

```typescript
const url = api.audioUrl("xyz-789");
// Returns: "http://localhost:8000/api/v1/audio/xyz-789"

// Use in JSX:
<audio controls src={url} />
<a href={url} download="speech.wav">Download</a>
```

---

## Error Handling

All API methods throw a `Error` with a descriptive message when:
- The HTTP response status is 4xx or 5xx
- The network request fails entirely

Usage pattern in page components:

```typescript
try {
  const voices = await api.listVoices();
  setVoices(voices);
} catch (err) {
  setError(err instanceof Error ? err.message : "Unknown error");
}
```

---

## Extending the Client

To add a new API method:

1. Add the TypeScript type for the new request/response shape (if needed)
2. Add the method to the `api` object in `api.ts`
3. Use consistent error handling (`response.ok` check + `throw new Error(…)`)

```typescript
// Example: add a method to list recordings for a voice
async listRecordings(voiceId: string): Promise<RecordingRecord[]> {
  const res = await fetch(`${BASE}/voice/${voiceId}/recordings`);
  if (!res.ok) throw new Error(`Failed to list recordings: ${res.statusText}`);
  return res.json();
},
```
