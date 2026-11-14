"""Piece storage for PianoCapture: one folder and one JSON per processed window."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from piano import config


def new_piece_id() -> str:
    return uuid.uuid4().hex[:12]


def piece_dir(piece_id: str) -> Path:
    clean = "".join(char for char in str(piece_id) if char.isalnum())
    if not clean:
        raise ValueError("Invalid piece id")
    return config.PIECES_DIR / clean


def _piece_json(piece_id: str) -> Path:
    return piece_dir(piece_id) / "piece.json"


def save_piece(piece: dict) -> dict:
    directory = config.PIECES_DIR / str(piece["id"])
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "piece.json").write_text(
        json.dumps(piece, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return piece


def load_piece(piece_id: str) -> dict:
    path = _piece_json(piece_id)
    if not path.exists():
        raise FileNotFoundError(piece_id)
    return json.loads(path.read_text(encoding="utf-8"))


def piece_audio(piece_id: str) -> Path:
    path = piece_dir(piece_id) / "audio.wav"
    if not path.exists():
        raise FileNotFoundError(piece_id)
    return path


def piece_midi(piece_id: str) -> Path | None:
    path = piece_dir(piece_id) / "notes.mid"
    return path if path.exists() else None


def list_pieces(limit: int = 20) -> list[dict]:
    """Return the newest pieces, summary only (no note arrays)."""
    if not config.PIECES_DIR.exists():
        return []
    entries: list[tuple[float, dict]] = []
    for folder in config.PIECES_DIR.iterdir():
        if not folder.is_dir():
            continue
        path = folder / "piece.json"
        try:
            piece = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        entries.append((folder.stat().st_mtime, piece))
    entries.sort(key=lambda item: item[0], reverse=True)
    summaries = []
    for _mtime, piece in entries[: max(1, int(limit))]:
        summaries.append(
            {
                "id": piece.get("id"),
                "created": piece.get("created"),
                "title": (piece.get("source") or {}).get("title"),
                "artist": (piece.get("source") or {}).get("artist"),
                "window": piece.get("window"),
                "note_count": piece.get("note_count", 0),
            }
        )
    return summaries


def created_stamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")
