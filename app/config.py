"""Central configuration and path handling for TabTool.

All filesystem paths must come from this module. Nothing else should
hard-code absolute paths.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from app import __version__

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _path_from_env(name: str, default: Path) -> Path:
    """Read a path from the environment, resolving relative paths under BASE_DIR."""
    raw = os.getenv(name)
    if not raw:
        return default.resolve()
    value = Path(raw).expanduser()
    if not value.is_absolute():
        value = BASE_DIR / value
    return value.resolve()


APP_NAME = "TabTool"
VERSION = __version__

HOST = os.getenv("TABTOOL_HOST", "127.0.0.1").strip() or "127.0.0.1"
PORT = int(os.getenv("TABTOOL_PORT", "8000"))
LAN_PIN = os.getenv("TABTOOL_LAN_PIN", "").strip()
MAX_UPLOAD_MB = int(os.getenv("TABTOOL_MAX_UPLOAD_MB", "250"))
AUDIO_RETENTION_DAYS = int(os.getenv("TABTOOL_AUDIO_RETENTION_DAYS", "7"))
LOG_LEVEL = os.getenv("TABTOOL_LOG_LEVEL", "INFO").upper()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
SPOTIFY_REDIRECT_URI = os.getenv(
    "SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8000/auth/callback"
).strip()

BASE_PATH = BASE_DIR
STATIC_DIR = BASE_DIR / "app" / "static"
DOCS_DIR = BASE_DIR / "docs"
DATA_DIR = _path_from_env("TABTOOL_DATA_DIR", BASE_DIR / "data")

DATA_SUBDIRS = ("audio", "stems", "tabs", "cache", "logs", "models")


def ensure_data_dirs() -> list[Path]:
    """Create the private data directory tree if it does not exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    created: list[Path] = [DATA_DIR]
    for name in DATA_SUBDIRS:
        path = DATA_DIR / name
        path.mkdir(parents=True, exist_ok=True)
        created.append(path)
    return created


def is_loopback(host: str | None) -> bool:
    """Return True for loopback clients (including FastAPI's TestClient)."""
    if host is None:
        return False
    normalized = host.strip().lower()
    if normalized.startswith("::ffff:"):
        normalized = normalized[7:]
    return normalized in {"127.0.0.1", "::1", "localhost", "testclient"}
