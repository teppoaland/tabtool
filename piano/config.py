"""Paths and limits for PianoCapture.

Everything lives under ``data_piano/`` at the repository root (gitignored), so
the tool can be deleted or moved without touching TabTool's ``data/``.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _path_from_env(name: str, default: Path) -> Path:
    raw = os.getenv(name)
    if not raw:
        return default.resolve()
    value = Path(raw).expanduser()
    if not value.is_absolute():
        value = BASE_DIR / value
    return value.resolve()


DATA_DIR = _path_from_env("PIANO_DATA_DIR", BASE_DIR / "data_piano")
SOURCES_DIR = DATA_DIR / "sources"
PIECES_DIR = DATA_DIR / "pieces"
TMP_DIR = DATA_DIR / "tmp"

HOST = os.getenv("PIANO_HOST", "127.0.0.1").strip() or "127.0.0.1"
PORT = int(os.getenv("PIANO_PORT", "8020"))

# How much of the beginning is downloaded and analysed for the intro.
PROBE_SECONDS = float(os.getenv("PIANO_PROBE_SECONDS", "75"))
# The tool is for short fragments (intros, verses), not whole songs.
MAX_WINDOW_SECONDS = float(os.getenv("PIANO_MAX_WINDOW_SECONDS", "300"))
MIN_WINDOW_SECONDS = 3.0
MAX_SOURCE_SECONDS = float(os.getenv("PIANO_MAX_SOURCE_SECONDS", "1200"))

STAGE_QUEUED = "queued"
STAGE_RUNNING = "running"
STAGE_READY = "ready"
STAGE_FAILED = "failed"


def ensure_data_dirs() -> list[Path]:
    created: list[Path] = []
    for path in (DATA_DIR, SOURCES_DIR, PIECES_DIR, TMP_DIR):
        path.mkdir(parents=True, exist_ok=True)
        created.append(path)
    return created
