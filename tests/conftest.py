"""Pytest configuration: add backend/ to sys.path so 'app' and 'voice_engine' are importable."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure that `app` and `voice_engine` packages are importable
_BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))
