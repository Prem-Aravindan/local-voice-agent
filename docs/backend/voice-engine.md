# 🎙️ Voice Engine

The `voice_engine` package contains all **ML and audio-processing** code. It is intentionally isolated from FastAPI and the database — modules here operate purely on files and tensors.

---

## Table of Contents

- [Package Overview](#package-overview)
- [Recorder](#recorder)
  - [How Live Recording Works](#how-live-recording-works)
  - [Public API](#recorder-public-api)
  - [Output Format](#recorder-output-format)
- [DatasetBuilder](#datasetbuilder)
  - [Preprocessing Pipeline](#preprocessing-pipeline)
  - [Public API](#datasetbuilder-public-api)
- [EmbeddingEngine](#embeddingengine)
  - [What is a Speaker Embedding?](#what-is-a-speaker-embedding)
  - [How XTTS Extracts Embeddings](#how-xtts-extracts-embeddings)
  - [Public API](#embeddingengine-public-api)
  - [Output Format](#embedding-output-format)
- [TTSEngine](#ttsengine)
  - [Synthesis Pipeline](#synthesis-pipeline)
  - [Public API](#ttsengine-public-api)
- [Fallback Behaviour](#fallback-behaviour)
- [End-to-End Pipeline Summary](#end-to-end-pipeline-summary)

---

## Package Overview

```
voice_engine/
├── __init__.py
├── recorder.py          # Microphone → WAV  (sounddevice)
├── dataset_builder.py   # WAV → cleaned WAV  (librosa + soundfile)
├── embedding.py         # Cleaned WAVs → speaker embedding tensor  (XTTS v2)
└── tts_engine.py        # Text + embedding → speech WAV  (XTTS v2)
```

**Data flow through the pipeline:**

```
Microphone ──► recorder.py ──► WAV files
                                  │
                                  ▼
                         dataset_builder.py ──► cleaned WAV files
                                                       │
                                                       ▼
                                              embedding.py ──► embedding.pt
                                                                     │
                                                                     ▼
                                            text + embedding ──► tts_engine.py ──► speech.wav
```

---

## Recorder

> 📂 Source: `backend/voice_engine/recorder.py`

### How Live Recording Works

The recorder uses `sounddevice` to open the system microphone. Audio data arrives in chunks via a **callback function** that runs in a background thread (managed by sounddevice internally). Each chunk is placed on a `queue.Queue`, and a separate writer thread drains the queue and writes PCM data to the WAV file.

```
Microphone hardware
      │  PCM chunks (callback thread)
      ▼
  queue.Queue  ──► writer thread ──► sample_NNN.wav
      │
  (thread-safe)
```

Threading design:
- The `sounddevice` callback thread is owned by the audio library — do **not** block it.
- The writer thread is started by `start()` and stopped by `stop()`.
- A `threading.Event` signals the writer thread to flush remaining data and exit.

### Recorder Public API

```python
recorder = VoiceRecorder()

# Start capturing from the microphone
session: RecordingSession = recorder.start(voice_id="…", section="warmup")
# session.is_recording == True

# ... user reads prompts aloud ...

# Stop and save
session: RecordingSession = recorder.stop()
# session.is_recording == False
# session.duration_seconds == 42.3
# session.file_path == "data/recordings/{voice_id}/warmup/sample_001.wav"

# Check status without stopping
active: bool = recorder.is_active()
```

**`RecordingSession` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `is_recording` | bool | Whether recording is active |
| `voice_id` | str | Voice profile being recorded |
| `section` | str | Protocol section |
| `file_path` | str \| None | Path to saved WAV (set after `stop()`) |
| `duration_seconds` | float \| None | Duration in seconds (set after `stop()`) |
| `error` | str \| None | Error message if recording failed |

### Recorder Output Format

| Parameter | Value |
|-----------|-------|
| Format | WAV (PCM) |
| Sample rate | 24 000 Hz |
| Channels | 1 (mono) |
| Bit depth | 16-bit |
| Path pattern | `data/recordings/{voice_id}/{section}/sample_NNN.wav` |

---

## DatasetBuilder

> 📂 Source: `backend/voice_engine/dataset_builder.py`

### Preprocessing Pipeline

Raw recordings may have silence, background noise, and inconsistent volume levels. The `DatasetBuilder` cleans them before feeding into the embedding engine.

**Per-file steps:**

```
Input WAV
    │
    ▼ 1. Load with librosa
       (handles various sample rates and bit depths)
    │
    ▼ 2. Resample → 24 000 Hz (mono)
       (XTTS v2 requires 24 kHz input)
    │
    ▼ 3. Trim leading/trailing silence
       librosa.effects.trim(y, top_db=30)
       (removes segments quieter than 30 dB below peak)
    │
    ▼ 4. Peak-normalize to -3 dBFS
       y = y / max(|y|) * 0.7
       (avoids clipping while maximising dynamic range)
    │
    ▼ 5. Validate minimum duration ≥ 1.0 second
       (too-short clips degrade embedding quality)
    │
    ▼ 6. Write cleaned WAV
       soundfile.write("…/dataset/cleaned_NNN.wav", y, 24000, subtype="PCM_16")
    │
    ▼ Output: path added to result list
```

> 💡 **Why normalize?** The XTTS model is trained on audio with consistent volume levels. Normalizing your recordings to -3 dBFS keeps the input distribution close to the training distribution, improving voice similarity.

### DatasetBuilder Public API

```python
result: DatasetBuildResult = DatasetBuilder.build(
    recordings_dir="/absolute/path/to/data/recordings/{voice_id}",
    output_dir="/absolute/path/to/data/recordings/{voice_id}/dataset"
)

result.sample_paths    # List[str] — paths to cleaned WAVs
result.total_duration  # float — total seconds of clean audio
result.error           # str | None — set if build failed
```

**Quality targets:**

| Metric | Recommendation |
|--------|---------------|
| Minimum total duration | 10 minutes |
| Recommended total duration | 20 minutes |
| Per-sample minimum | 1 second (shorter samples are skipped) |

---

## EmbeddingEngine

> 📂 Source: `backend/voice_engine/embedding.py`

### What is a Speaker Embedding?

A speaker embedding is a **dense vector** (array of numbers) that represents the unique acoustic characteristics of a voice — its timbre, pitch, rhythm, and cadence. Think of it as a voice "fingerprint".

XTTS v2 actually produces two complementary representations:

| Tensor | Purpose |
|--------|---------|
| `gpt_cond_latent` | Conditions the GPT-based language model on the speaker's style |
| `speaker_embedding` | A compact vector used by the flow-based decoder |

Both are required for synthesis and are saved together in one file.

### How XTTS Extracts Embeddings

```
Cleaned WAV files (multiple recordings)
    │
    ▼ XTTS v2 model loaded via TTS library
    │
    ▼ model.get_conditioning_latents(audio_paths=[...])
    │  Internally:
    │  • Loads each WAV
    │  • Passes through a speaker encoder (transformer)
    │  • Averages representations across all input files
    │  • Returns gpt_cond_latent + speaker_embedding tensors
    │
    ▼ torch.save({"gpt_cond_latent": …, "speaker_embedding": …}, path)
    │
Output: data/embeddings/{voice_id}/embedding.pt
```

> 💡 **Why multiple recordings?** Averaging over many samples makes the embedding more robust — occasional noise, stumbles, or unusual pronunciations are averaged out.

### EmbeddingEngine Public API

```python
result: EmbeddingResult = EmbeddingEngine.create_embedding(
    sample_paths=["…/cleaned_001.wav", "…/cleaned_002.wav"],
    voice_id="…"
)

result.embedding_path  # str — path to saved .pt file
result.error           # str | None — set if extraction failed
```

### Embedding Output Format

The `.pt` file is a PyTorch serialised dictionary:

```python
{
  "gpt_cond_latent":  torch.Tensor,  # shape: [1, seq_len, 1024]
  "speaker_embedding": torch.Tensor  # shape: [1, 512]
}
```

These tensors are loaded directly into `model.inference()` during synthesis — no further processing needed.

---

## TTSEngine

> 📂 Source: `backend/voice_engine/tts_engine.py`

### Synthesis Pipeline

```
Input: text (str) + embedding_path (.pt) + language + speed + temperature
    │
    ▼ 1. Load XTTS v2 model  (@lru_cache — loaded only once per process)
    │
    ▼ 2. Load embedding dict from .pt file
       gpt_cond_latent, speaker_embedding = torch.load(embedding_path)
    │
    ▼ 3. model.inference(
           text              = text,
           language          = language,      # e.g. "en"
           gpt_cond_latent   = gpt_cond_latent,
           speaker_embedding = speaker_embedding,
           temperature       = temperature,   # 0.0 – 1.0
           speed             = speed          # 0.1 – 3.0
       )
    │  Returns a dict: {"wav": numpy_array, "sample_rate": 24000}
    │
    ▼ 4. soundfile.write(output_path, wav_array, 24000, subtype="PCM_16")
    │
Output: data/generated/{voice_id}/{audio_id}.wav
```

**Parameter effects:**

| Parameter | Range | Effect |
|-----------|-------|--------|
| `temperature` | 0.0 – 1.0 | Higher = more natural variation but less predictable |
| `speed` | 0.1 – 3.0 | Speaking rate multiplier; 1.0 = normal |
| `language` | ISO 639-1 | Multilingual support; affects phoneme rendering |

### TTSEngine Public API

```python
engine = TTSEngine(
    model_name="tts_models/multilingual/multi-dataset/xtts_v2",
    device="cpu"          # or "cuda"
)

output_path: str = engine.synthesise(
    text="Hello, world!",
    embedding_path="data/embeddings/{voice_id}/embedding.pt",
    output_path="data/generated/{voice_id}/{audio_id}.wav",
    language="en",
    speed=1.0,
    temperature=0.7
)
```

---

## Fallback Behaviour

All four modules implement **graceful fallbacks** when their ML/audio dependencies are unavailable (e.g., in CI test environments without PyTorch):

| Module | Missing library | Fallback behaviour |
|--------|----------------|--------------------|
| `Recorder` | `sounddevice` | Returns `RecordingSession` with `error="sounddevice unavailable"` |
| `DatasetBuilder` | `librosa` / `soundfile` | Returns `DatasetBuildResult` with `error="…"` |
| `EmbeddingEngine` | `TTS` / `torch` | Saves a stub `{"stub": zeros(1)}` embedding |
| `TTSEngine` | `TTS` / `torch` | Writes a silent 1-second WAV stub |

This allows the application (and all tests) to run without installing heavy ML dependencies, making development and CI much faster.

---

## End-to-End Pipeline Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    RECORDING PHASE                          │
│                                                             │
│  VoiceRecorder.start()                                      │
│       ↓  (sounddevice callback + threading)                 │
│  VoiceRecorder.stop()  →  sample_NNN.wav (24kHz mono PCM16) │
└─────────────────────────────────────────────────────────────┘
                         ↓  (background task triggered)
┌─────────────────────────────────────────────────────────────┐
│                    TRAINING PHASE                           │
│                                                             │
│  DatasetBuilder.build()                                     │
│       ↓  (resample, trim, normalize)                        │
│  cleaned_NNN.wav files                                      │
│       ↓                                                     │
│  EmbeddingEngine.create_embedding()                         │
│       ↓  (XTTS v2 speaker encoder)                          │
│  embedding.pt  {gpt_cond_latent, speaker_embedding}         │
└─────────────────────────────────────────────────────────────┘
                         ↓  (on demand, per TTS request)
┌─────────────────────────────────────────────────────────────┐
│                    SYNTHESIS PHASE                          │
│                                                             │
│  TTSEngine.synthesise(text, embedding_path, …)              │
│       ↓  (XTTS v2 inference with gpt_cond_latent            │
│           + speaker_embedding)                              │
│  {audio_id}.wav  (24kHz mono PCM16)                         │
└─────────────────────────────────────────────────────────────┘
```
