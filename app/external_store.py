"""Archive externally sourced files with human-readable names.

The private ``data/`` root stays the source of truth. YouTube audio and
imported GP5/MusicXML tabs are mirrored into ``EXTERNAL_DIR`` so the same
files are easy to find and reuse elsewhere. A hard link is created when
the target is on the same volume (no extra disk usage); otherwise a copy
is written. Archiving never raises: a failure must not break the job.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from app import config

CATEGORIES = {"audio", "tabs"}

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def display_name(artist: str, title: str, fallback: str = "track") -> str:
    """Build a filesystem-safe ``Artist - Title`` name."""
    artist_text = " ".join(str(artist or "").split())
    title_text = " ".join(str(title or "").split())
    if artist_text and title_text:
        value = f"{artist_text} - {title_text}"
    else:
        value = title_text or artist_text
    value = _ILLEGAL.sub("", value)
    value = " ".join(value.split()).strip(" .-_")
    return (value or fallback)[:120]


def archive_external(
    source: str | Path,
    category: str,
    artist: str,
    title: str,
) -> Path | None:
    """Mirror ``source`` into ``EXTERNAL_DIR/<category>/Artist - Title.ext``."""
    if category not in CATEGORIES:
        return None
    source_path = Path(source)
    if not source_path.is_file():
        return None
    try:
        target_dir = Path(config.EXTERNAL_DIR) / category
        target_dir.mkdir(parents=True, exist_ok=True)
        name = display_name(artist, title, source_path.stem)
        target = target_dir / f"{name}{source_path.suffix.lower()}"
        temporary = target_dir / f".{target.name}.tmp"
        if temporary.exists():
            temporary.unlink()
        try:
            os.link(source_path, temporary)
        except OSError:
            shutil.copy2(source_path, temporary)
        os.replace(temporary, target)
        return target
    except OSError:
        return None


def archive_mp3(
    source: str | Path,
    artist: str,
    title: str,
) -> Path | None:
    """Encode a WAV track into ``EXTERNAL_DIR/audio/mp3/<Artist>/``.

    The MP3 copy is meant for listening elsewhere (car, phone, band
    rehearsals). It is rebuilt when the WAV is newer than the MP3.
    """
    source_path = Path(source)
    if source_path.suffix.lower() != ".wav" or not source_path.is_file():
        return None
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return None
    try:
        artist_name = display_name(artist, "", "Unknown Artist")
        target_dir = Path(config.EXTERNAL_DIR) / "audio" / "mp3" / artist_name
        target_dir.mkdir(parents=True, exist_ok=True)
        name = display_name(artist, title, source_path.stem)
        target = target_dir / f"{name}.mp3"
        if target.is_file() and target.stat().st_size > 0:
            if target.stat().st_mtime >= source_path.stat().st_mtime:
                return target
        temporary = target_dir / f".{target.stem}.tmp.mp3"
        if temporary.exists():
            temporary.unlink()
        result = subprocess.run(
            [
                ffmpeg,
                "-v",
                "error",
                "-y",
                "-i",
                str(source_path),
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "2",
                str(temporary),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0 or not temporary.is_file():
            temporary.unlink(missing_ok=True)
            return None
        os.replace(temporary, target)
        return target
    except OSError:
        return None
