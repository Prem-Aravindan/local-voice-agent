"""Voice engine: audio recorder with guided protocol support."""

from __future__ import annotations

import queue
import threading
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from app.config import AUDIO_BIT_DEPTH, AUDIO_CHANNELS, RECORDINGS_DIR, SAMPLE_RATE

try:
    import numpy as np
    import sounddevice as sd

    _SOUNDDEVICE_AVAILABLE = True
except ImportError:  # pragma: no cover
    _SOUNDDEVICE_AVAILABLE = False


@dataclass
class RecordingSession:
    """State object returned by the recorder."""

    voice_id: str
    section: str
    file_path: Path
    duration: float = 0.0
    is_recording: bool = False
    error: str | None = None


class VoiceRecorder:
    """Records audio from the default microphone and saves it as a WAV file.

    Supports guided recording sessions based on the protocol defined in
    ``app.config.RECORDING_PROTOCOL``.
    """

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        channels: int = AUDIO_CHANNELS,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self._audio_queue: queue.Queue[bytes] = queue.Queue()
        self._stop_event = threading.Event()
        self._record_thread: threading.Thread | None = None
        self._current_session: RecordingSession | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, voice_id: str, section: str = "warmup") -> RecordingSession:
        """Begin recording audio for *voice_id* / *section*.

        Returns a :class:`RecordingSession` with ``is_recording=True``
        on success or ``error`` set on failure.
        """
        if not _SOUNDDEVICE_AVAILABLE:
            session = RecordingSession(
                voice_id=voice_id,
                section=section,
                file_path=Path(""),
                error="sounddevice is not installed; install voice-agent backend dependencies.",
            )
            return session

        dest_dir = RECORDINGS_DIR / voice_id / section
        dest_dir.mkdir(parents=True, exist_ok=True)
        file_path = _next_wav_path(dest_dir)

        session = RecordingSession(
            voice_id=voice_id, section=section, file_path=file_path, is_recording=True
        )
        self._current_session = session
        self._stop_event.clear()
        self._audio_queue = queue.Queue()

        self._record_thread = threading.Thread(
            target=self._record_loop, args=(session,), daemon=True
        )
        self._record_thread.start()
        return session

    def stop(self) -> RecordingSession | None:
        """Stop the current recording and flush audio to disk."""
        if self._current_session is None:
            return None
        self._stop_event.set()
        if self._record_thread is not None:
            self._record_thread.join(timeout=10)
        self._current_session.is_recording = False
        return self._current_session

    def is_active(self) -> bool:
        return self._current_session is not None and self._current_session.is_recording

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _record_loop(self, session: RecordingSession) -> None:
        """Run in a background thread: stream audio and write WAV file."""
        frames: list[bytes] = []

        def _callback(
            indata: "np.ndarray",  # noqa: F821
            frame_count: int,
            time_info: object,
            status: "sd.CallbackFlags",  # noqa: F821
        ) -> None:
            if status:
                pass  # log or ignore overflow/underflow
            frames.append(indata.copy().tobytes())

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                callback=_callback,
            ):
                self._stop_event.wait()  # block until stop() is called
        except Exception as exc:  # pragma: no cover
            session.error = str(exc)
            session.is_recording = False
            return

        # Write frames to WAV
        if frames:
            import numpy as np

            audio_data = np.frombuffer(b"".join(frames), dtype=np.int16)
            session.duration = len(audio_data) / self.sample_rate
            _write_wav(session.file_path, audio_data, self.sample_rate, self.channels)


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def _next_wav_path(directory: Path) -> Path:
    """Return the next available sample_NNN.wav path inside *directory*."""
    existing = sorted(directory.glob("sample_*.wav"))
    idx = len(existing) + 1
    return directory / f"sample_{idx:03d}.wav"


def _write_wav(path: Path, audio: "np.ndarray", sample_rate: int, channels: int) -> None:  # noqa: F821
    """Write a PCM-16 WAV file to *path*."""
    import numpy as np

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(AUDIO_BIT_DEPTH // 8)
        wf.setframerate(sample_rate)
        wf.writeframes(audio.astype(np.int16).tobytes())
