"""Voice engine: create and persist speaker embeddings."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import torch

    _TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover
    _TORCH_AVAILABLE = False

try:
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import Xtts

    _XTTS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _XTTS_AVAILABLE = False


class EmbeddingEngine:
    """Generates and stores speaker embeddings using the XTTS speaker encoder.

    When XTTS is not available (e.g. during unit tests), a stub embedding is
    used so that the rest of the system remains testable.
    """

    def __init__(self, model_name: str, device: str = "cpu") -> None:
        self.model_name = model_name
        self.device = device
        self._model: object | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_embedding(self, audio_paths: list[Path], output_path: Path) -> Path:
        """Compute a speaker embedding from *audio_paths* and save it to
        *output_path* (a ``.pt`` file).

        Returns the path to the saved embedding.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not _TORCH_AVAILABLE:
            return self._save_stub_embedding(output_path)

        if _XTTS_AVAILABLE:
            return self._create_xtts_embedding(audio_paths, output_path)

        logger.warning("TTS library not available; using stub embedding.")
        return self._save_stub_embedding(output_path)

    def load_embedding(self, embedding_path: Path) -> object:
        """Load and return a previously saved embedding tensor."""
        if not _TORCH_AVAILABLE:
            raise RuntimeError("PyTorch is required to load embeddings.")
        import torch

        return torch.load(str(embedding_path), map_location=self.device)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_xtts_embedding(self, audio_paths: list[Path], output_path: Path) -> Path:
        """Use the XTTS speaker encoder to compute an embedding."""
        import torch
        from TTS.api import TTS

        tts = TTS(self.model_name).to(self.device)
        # XTTS exposes get_conditioning_latents for speaker conditioning
        model = tts.synthesizer.tts_model  # type: ignore[attr-defined]
        gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(
            audio_path=[str(p) for p in audio_paths]
        )
        embedding = {
            "gpt_cond_latent": gpt_cond_latent,
            "speaker_embedding": speaker_embedding,
        }
        torch.save(embedding, str(output_path))
        logger.info("Saved XTTS embedding to %s", output_path)
        return output_path

    def _save_stub_embedding(self, output_path: Path) -> Path:
        """Persist a placeholder embedding for testing / offline development."""
        import torch

        stub = {"stub": torch.zeros(1)}
        torch.save(stub, str(output_path))
        logger.warning("Saved STUB embedding to %s", output_path)
        return output_path
