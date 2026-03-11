"""Voice engine: build a clean dataset from raw recordings."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import librosa
    import numpy as np
    import soundfile as sf

    _AUDIO_LIBS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _AUDIO_LIBS_AVAILABLE = False


@dataclass
class DatasetBuildResult:
    """Result returned after processing a set of recordings."""

    voice_id: str
    dataset_dir: Path
    sample_paths: list[Path] = field(default_factory=list)
    total_duration: float = 0.0
    error: str | None = None


class DatasetBuilder:
    """Processes raw WAV recordings into a clean training dataset.

    Steps for each audio file:
    1. Load and resample to target sample rate.
    2. Normalise volume (peak normalisation).
    3. Trim leading/trailing silence.
    4. Validate minimum length.
    5. Write to dataset directory.
    """

    MIN_SAMPLE_DURATION: float = 1.0  # seconds
    TARGET_SAMPLE_RATE: int = 24_000

    def __init__(
        self,
        target_sample_rate: int = TARGET_SAMPLE_RATE,
        min_sample_duration: float = MIN_SAMPLE_DURATION,
    ) -> None:
        self.target_sample_rate = target_sample_rate
        self.min_sample_duration = min_sample_duration

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, voice_id: str, recordings_dir: Path, dataset_dir: Path) -> DatasetBuildResult:
        """Process all WAV files under *recordings_dir* and write cleaned
        samples to *dataset_dir*.

        Returns a :class:`DatasetBuildResult` describing the outcome.
        """
        result = DatasetBuildResult(voice_id=voice_id, dataset_dir=dataset_dir)

        if not _AUDIO_LIBS_AVAILABLE:
            result.error = (
                "librosa / soundfile are not installed; "
                "install voice-agent backend dependencies."
            )
            return result

        wav_files = sorted(recordings_dir.rglob("*.wav"))
        if not wav_files:
            result.error = f"No WAV files found under {recordings_dir}"
            return result

        dataset_dir.mkdir(parents=True, exist_ok=True)

        for idx, wav_path in enumerate(wav_files, start=1):
            try:
                processed = self._process_file(wav_path)
                if processed is None:
                    logger.warning("Skipped %s: too short after processing", wav_path)
                    continue
                audio, sr = processed
                out_path = dataset_dir / f"sample_{idx:03d}.wav"
                sf.write(str(out_path), audio, sr, subtype="PCM_16")
                duration = len(audio) / sr
                result.sample_paths.append(out_path)
                result.total_duration += duration
                logger.info("Processed %s → %s (%.1fs)", wav_path.name, out_path.name, duration)
            except Exception as exc:
                logger.warning("Failed to process %s: %s", wav_path, exc)

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process_file(self, path: Path) -> tuple["np.ndarray", int] | None:  # noqa: F821
        """Load, resample, normalise, and trim a single WAV file.

        Returns ``(audio_array, sample_rate)`` or ``None`` if the result
        is too short to be useful.
        """
        import librosa
        import numpy as np

        audio, _ = librosa.load(str(path), sr=self.target_sample_rate, mono=True)

        # Trim silence (top_db=30 dB below peak)
        audio, _ = librosa.effects.trim(audio, top_db=30)

        # Peak normalise to -3 dBFS to avoid clipping
        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = audio / peak * 0.7

        # Validate minimum length
        if len(audio) / self.target_sample_rate < self.min_sample_duration:
            return None

        return audio, self.target_sample_rate
