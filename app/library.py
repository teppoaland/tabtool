"""Remove a tab together with its private data.

A deleted song loses its tab directory, database rows, audio, stems and the
lyrics sidecar (``data/lyrics/<tab_id>.json``). The external MP3 listening
copy (``EXTERNAL_DIR/audio/mp3``) is kept, so the user can still listen to
the song elsewhere.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from app import config, db, lyrics
from app.external_store import display_name


def _mp3_path(artist: str, title: str) -> Path | None:
    artist_name = display_name(artist, "", "Unknown Artist")
    name = display_name(artist, title, "track")
    candidate = (
        Path(config.EXTERNAL_DIR)
        / "audio"
        / "mp3"
        / artist_name
        / f"{name}.mp3"
    )
    return candidate if candidate.is_file() else None


def _remove_tab_directory(tab: dict[str, Any]) -> None:
    try:
        directory = db.resolve_under_data(str(tab.get("directory") or ""))
    except ValueError:
        return
    tabs_root = (Path(config.DATA_DIR) / "tabs").resolve()
    if directory == tabs_root or directory.parent != tabs_root:
        return
    shutil.rmtree(directory, ignore_errors=True)


def _remove_audio(audio_path: str) -> bool:
    if not audio_path:
        return False
    try:
        path = db.resolve_under_data(audio_path)
    except ValueError:
        return False
    if not path.is_file():
        return False
    try:
        path.unlink()
    except OSError:
        return False
    stems_root = Path(config.DATA_DIR) / "stems"
    if stems_root.is_dir():
        for directory in stems_root.glob(f"*/{path.stem}"):
            if directory.is_dir():
                shutil.rmtree(directory, ignore_errors=True)
    return True


def delete_tab_data(tab_id: str) -> dict[str, Any]:
    """Delete a tab and everything derived from it; keep the MP3 copy."""
    tab = db.get_tab(tab_id)
    if tab is None:
        raise LookupError(tab_id)

    meta = tab.get("meta") if isinstance(tab.get("meta"), dict) else {}
    audio_path = str(tab.get("audio_path") or "").strip()
    if not audio_path and isinstance(meta, dict):
        audio_path = str(meta.get("audio_path") or "").strip()

    title = str(tab.get("title") or "")
    artist = str(tab.get("artist") or "")
    mp3 = _mp3_path(artist, title)

    _remove_tab_directory(tab)
    # Lyrics are a sidecar (v2.06), so they are not inside the tab directory.
    lyrics.delete(tab_id)
    db.delete_tab_records(tab_id)

    # Shared audio (for example an imported tab attached to an AI tab) is
    # removed only when no remaining tab or track points at it.
    audio_removed = False
    if audio_path and db.audio_reference_count(audio_path) == 0:
        audio_removed = _remove_audio(audio_path)

    return {
        "tab_id": tab_id,
        "title": title,
        "artist": artist,
        "audio_removed": audio_removed,
        "mp3_kept": mp3 is not None,
        "mp3_path": str(mp3) if mp3 is not None else "",
    }
