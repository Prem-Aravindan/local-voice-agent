"""Voice engine: text-to-speech synthesis using a cloned voice embedding."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import torch

    _TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover
    _TORCH_AVAILABLE = False

try:
    from TTS.api import TTS as _TTSLib

    _TTS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _TTS_AVAILABLE = False


class TTSEngine:
    """Synthesises speech from text using a speaker embedding.

    When the TTS library is not available, a silent WAV stub is written so
    that the API layer remains functional for integration tests.
    """

    def __init__(self, model_name: str, device: str = "cpu") -> None:
        self.model_name = model_name
        self.device = device

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        text: str,
        embedding_path: Path,
        output_path: Path,
        language: str = "en",
        speed: float = 1.0,
        temperature: float = 0.7,
    ) -> Path:
        """Synthesise *text* using the voice described by *embedding_path*.

        Saves the result as a WAV file at *output_path* and returns the path.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not _TTS_AVAILABLE:
            logger.warning("TTS library not installed; writing silent stub audio.")
            return self._write_stub(output_path)

        tts_instance = _get_tts_model(self.model_name, self.device)

        if not _TORCH_AVAILABLE:
            return self._write_stub(output_path)

        import torch

        embedding = torch.load(str(embedding_path), map_location=self.device)

        if "stub" in embedding:
            logger.warning("Stub embedding detected; writing silent stub audio.")
            return self._write_stub(output_path)

        gpt_cond_latent = embedding["gpt_cond_latent"]
        speaker_embedding = embedding["speaker_embedding"]

        model = tts_instance.synthesizer.tts_model  # type: ignore[attr-defined]
        out = model.inference(
            text=text,
            language=language,
            gpt_cond_latent=gpt_cond_latent,
            speaker_embedding=speaker_embedding,
            temperature=temperature,
            speed=speed,
        )
        wav = out["wav"]
        import soundfile as sf

        sf.write(str(output_path), wav, 24000, subtype="PCM_16")
        logger.info("Generated audio saved to %s", output_path)
        return output_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _write_stub(output_path: Path) -> Path:
        """Write a 1-second silent WAV file as a stub."""
        import struct
        import wave

        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(struct.pack("<" + "h" * 24000, *([0] * 24000)))
        return output_path


@lru_cache(maxsize=1)
def _get_tts_model(model_name: str, device: str) -> object:
    """Return a cached TTS model instance (avoids repeated loading)."""
    if not _TTS_AVAILABLE:
        return None
    from TTS.api import TTS

    logger.info("Loading TTS model %s on %s …", model_name, device)
    return TTS(model_name).to(device)
