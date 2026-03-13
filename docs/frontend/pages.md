# 📄 Pages Reference

This document describes each page in the frontend — its purpose, the UX flow, and what API calls it makes.

---

## Table of Contents

- [Root Layout (`layout.tsx`)](#root-layout-layouttsx)
- [Home Page (`/`)](#home-page-)
- [Voices Page (`/voices`)](#voices-page-voices)
- [Record Page (`/record`)](#record-page-record)
- [Generate Page (`/generate`)](#generate-page-generate)

---

## Root Layout (`layout.tsx`)

> 📂 Source: `frontend/app/layout.tsx`

**Purpose:** Wraps every page with a consistent navigation bar and HTML shell.

**Navigation links:**

| Label | Route | Icon |
|-------|-------|------|
| 🏠 Home | `/` | Dashboard overview |
| 🎤 Voices | `/voices` | Manage voice profiles |
| ⏺️ Record | `/record` | Record voice samples |
| 🔊 Generate | `/generate` | Generate speech |

The layout also injects global font settings, the `<html lang="en">` tag, and the Tailwind base styles from `globals.css`.

---

## Home Page (`/`)

> 📂 Source: `frontend/app/page.tsx`

**Purpose:** Welcome screen and starting point. Explains what the app does and provides navigation to the three main features.

**Layout:**

```
┌─────────────────────────────────────────────────────┐
│            Voice Clone Agent                        │
│   Your personal, local-first voice cloning tool    │
│                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────┐ │
│  │ 🎤 Voices    │ │ ⏺ Record     │ │ 🔊 Generate  │ │
│  │              │ │              │ │             │ │
│  │ Create and   │ │ Follow the   │ │ Convert     │ │
│  │ manage your  │ │ guided       │ │ text to     │ │
│  │ voice        │ │ protocol     │ │ speech with │ │
│  │ profiles     │ │              │ │ your voice  │ │
│  │              │ │              │ │             │ │
│  │ [Go →]       │ │ [Go →]       │ │ [Go →]      │ │
│  └──────────────┘ └──────────────┘ └─────────────┘ │
└─────────────────────────────────────────────────────┘
```

**No API calls.** This page is static.

---

## Voices Page (`/voices`)

> 📂 Source: `frontend/app/voices/page.tsx`

**Purpose:** Full voice profile management — create, view, train, and delete voices.

### UX Flow

```
Page loads
    │
    ▼ GET /api/v1/voices
Display list of voice profiles (or "No voices yet" if empty)

User fills in name + optional description
    │
    ▼ POST /api/v1/voice/create
New voice appears in list with status badge "pending"

User clicks [Train] on a pending voice
    │
    ▼ POST /api/v1/voice/{id}/train
Job is enqueued. Status badge updates (requires manual refresh or polling)

User clicks [Delete] on a voice
    │
    ▼ DELETE /api/v1/voice/{id}
Voice is removed from the list
```

### Status Badges

| Status | Colour | Meaning |
|--------|--------|---------|
| `pending` | 🟡 Yellow | Voice created, not yet trained |
| `ready` | 🟢 Green | Training complete — voice can generate speech |
| `failed` | 🔴 Red | Training failed — check logs for error |

### API Calls

| Action | Method | Endpoint |
|--------|--------|----------|
| Load voices | `GET` | `/voices` |
| Create voice | `POST` | `/voice/create` |
| Train voice | `POST` | `/voice/{id}/train` |
| Delete voice | `DELETE` | `/voice/{id}` |

---

## Record Page (`/record`)

> 📂 Source: `frontend/app/record/page.tsx`

**Purpose:** Guided recording wizard. Walks the user through five protocol sections, recording audio for each prompt.

### UX Flow

```
Page loads
    │
    ▼ GET /api/v1/voices  (to populate voice selector)
    ▼ GET /api/v1/voice/protocol  (to load prompts)

User selects a voice from dropdown
User selects a section (warmup / storybook / numbers / assistant / expressive)

Prompts for selected section are displayed one at a time

User clicks [Start Recording]
    │
    ▼ Browser: MediaRecorder.start()  (captures mic audio as WebM/OGG blob)
    │
    ▼ UI shows a recording indicator (red dot + timer)

User reads the prompt aloud, then clicks [Stop Recording]
    │
    ▼ Browser: MediaRecorder.stop()  (blob is ready)
    │
    ▼ POST /api/v1/voice/sample  (multipart: voice_id + section + WAV blob)
    │
    ▼ "✅ Sample saved!" confirmation

User continues with next prompt in the section
```

### Recording Implementation

The browser uses the **MediaRecorder Web API** to capture microphone audio:

```typescript
// Simplified from record/page.tsx

const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
const recorder = new MediaRecorder(stream);
const chunks: Blob[] = [];

recorder.ondataavailable = (e) => chunks.push(e.data);
recorder.onstop = async () => {
  const blob = new Blob(chunks, { type: "audio/wav" });
  await api.uploadSample(voiceId, blob, section);
};

recorder.start();    // → recording begins
// ... user records ...
recorder.stop();     // → triggers onstop
```

> 💡 **Why record in the browser instead of the backend?**  
> Recording in the browser avoids microphone access over HTTP (which browsers restrict) and removes the need for a server-side audio device. The WAV blob is uploaded to the backend after recording completes.

### Navigation Between Sections

The recording page tracks which section is active and highlights prompts. Users can switch sections freely — there is no enforced order. The backend stores all recordings regardless of order.

### API Calls

| Action | Method | Endpoint |
|--------|--------|----------|
| Load voices | `GET` | `/voices` |
| Load prompts | `GET` | `/voice/protocol` |
| Upload sample | `POST` | `/voice/sample` |

---

## Generate Page (`/generate`)

> 📂 Source: `frontend/app/generate/page.tsx`

**Purpose:** Text-to-speech generation interface. Lets the user pick a trained voice, enter text, tweak parameters, and play/download the result.

### UX Flow

```
Page loads
    │
    ▼ GET /api/v1/voices  (filter to status == "ready")

User selects a voice from dropdown
User types text (1–5000 characters)
User optionally adjusts:
    • Language (default: English)
    • Speed (default: 1.0x)
    • Temperature (default: 0.7)

User clicks [Generate Speech]
    │
    ▼ POST /api/v1/tts  { voice_id, text, language, speed, temperature }
    │
    ▼ Loading spinner while waiting for synthesis (5–30 sec on CPU)
    │
    ▼ Response: { audio_id }
    │
    ▼ Audio player appears:  GET /api/v1/audio/{audio_id}
       • ▶️ Play button
       • ⬇️ Download button
```

### Parameter Controls

| Control | Type | Range | Default | Effect |
|---------|------|-------|---------|--------|
| Language | Dropdown | en, es, fr, de, it, pt, zh-cn, ja, … | `en` | Phoneme rendering |
| Speed | Slider | 0.1 – 3.0 | `1.0` | Speaking rate |
| Temperature | Slider | 0.0 – 1.0 | `0.7` | Naturalness vs. consistency |

### Audio Player

After generation, an `<audio>` HTML element is rendered:

```html
<audio controls src="/api/v1/audio/{audio_id}" />
```

A download link is also provided so the user can save the WAV to their computer.

### API Calls

| Action | Method | Endpoint |
|--------|--------|----------|
| Load voices | `GET` | `/voices` |
| Generate speech | `POST` | `/tts` |
| Stream/download audio | `GET` | `/audio/{audio_id}` |
