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
