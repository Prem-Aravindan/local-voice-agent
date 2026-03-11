"""Application-wide configuration loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Base paths
# ---------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parents[3]  # voice-agent/

DATA_DIR: Path = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
VOICES_DIR: Path = DATA_DIR / "voices"
RECORDINGS_DIR: Path = DATA_DIR / "recordings"
EMBEDDINGS_DIR: Path = DATA_DIR / "embeddings"
MODELS_DIR: Path = DATA_DIR / "models"
GENERATED_DIR: Path = DATA_DIR / "generated"
LOGS_DIR: Path = Path(os.getenv("LOGS_DIR", str(BASE_DIR / "logs")))

# Ensure directories exist at import time
for _d in (
    VOICES_DIR,
    RECORDINGS_DIR,
    EMBEDDINGS_DIR,
    MODELS_DIR,
    GENERATED_DIR,
    LOGS_DIR,
):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# API settings
# ---------------------------------------------------------------------------
API_V1_PREFIX: str = "/api/v1"
APP_TITLE: str = "Voice Clone Agent"
APP_VERSION: str = "1.0.0"
APP_DESCRIPTION: str = (
    "Local-first voice cloning application: record, clone, and synthesise speech."
)

# ---------------------------------------------------------------------------
# Audio recording settings
# ---------------------------------------------------------------------------
SAMPLE_RATE: int = int(os.getenv("SAMPLE_RATE", "24000"))
AUDIO_CHANNELS: int = 1
AUDIO_BIT_DEPTH: int = 16  # PCM 16-bit

# ---------------------------------------------------------------------------
# TTS model settings
# ---------------------------------------------------------------------------
TTS_MODEL_NAME: str = os.getenv("TTS_MODEL_NAME", "tts_models/multilingual/multi-dataset/xtts_v2")
TTS_DEVICE: str = os.getenv("TTS_DEVICE", "cpu")  # "cuda" if GPU is available

# ---------------------------------------------------------------------------
# Recording protocol prompt texts
# ---------------------------------------------------------------------------
RECORDING_PROTOCOL: dict[str, list[str]] = {
    "warmup": [
        "The quick brown fox jumps over the lazy dog.",
        "Today is a beautiful day to test the voice system.",
        "Artificial intelligence is transforming the world.",
        "She sells seashells by the seashore.",
        "How much wood would a woodchuck chuck if a woodchuck could chuck wood?",
    ],
    "storybook": [
        (
            "Once upon a time, in a land far away, there lived a brave adventurer named Alex. "
            "Alex had always dreamed of discovering hidden treasures beyond the misty mountains."
        ),
        (
            "One morning Alex packed a worn leather satchel and set off along a winding forest path. "
            "The trees whispered ancient secrets, and sunlight danced through the canopy above."
        ),
        (
            "After many hours of walking, Alex reached the edge of a crystal-clear lake. "
            "Reflected in its surface was a magnificent castle perched on a distant cliff."
        ),
        (
            "Without hesitation, Alex boarded a small wooden boat and rowed across the shimmering water. "
            "Each stroke of the oar brought the castle closer, and excitement grew with every passing minute."
        ),
        (
            "Inside the castle, Alex found a vast library filled with glowing books. "
            "Each book contained the story of someone who had dared to chase their dreams."
        ),
    ],
    "numbers": [
        "January first, two thousand twenty-four.",
        "The total price is three hundred and forty-five dollars and ninety-nine cents.",
        "The temperature is twenty-two point five degrees Celsius.",
        "Please dial one-eight-hundred-five-five-five-zero-one-two-three.",
        "The package weighs four kilograms and two hundred grams.",
        "The meeting is scheduled for the fifteenth of March at two-thirty PM.",
    ],
    "assistant": [
        "Hello, how can I help you today?",
        "Your reminder has been scheduled for tomorrow at nine AM.",
        "The meeting will begin in ten minutes.",
        "I'm currently processing your request, please hold on.",
        "Your package has been shipped and will arrive in three to five business days.",
        "I found three results matching your search query.",
    ],
    "expressive": [
        "Wow, that's absolutely incredible! I can hardly believe it!",
        "I wonder what will happen next. The suspense is almost unbearable.",
        "This discovery could change everything we know about the universe.",
        "Oh no, the bridge is out — we have to find another way across!",
        "And so, with a grateful heart, she finally returned home.",
        "Listen carefully: this is the most important thing I will ever tell you.",
    ],
}
