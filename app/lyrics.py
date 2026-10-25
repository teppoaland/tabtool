"""Sidecar lyrics for a tab (v2.06).

Lyrics live **next to** the tab, never inside it::

    data/lyrics/<tab_id>.json

    {"tab_id": "...", "updated_at": "...", "locked": false,
     "measures": {"10": "Mun sydän palaa", "11": "ja jatkuu..."}}

The GP5/MusicXML/MIDI files and the tab metadata stay byte-for-byte
untouched, so the playback chain (``.clinerules/07-playback-frozen.md``)
never learns about lyrics. The viewer reads this file and paints the line
for the current bar in its own overlay.

A finished lyric can be locked (v2.18): the flag lives in this file only, and
a locked sidecar refuses writes until it is opened again. The tab lock and
the playback settings are a different feature.

A save goes through a temp file and ``os.replace`` (pipeline invariant 5):
a failed write never leaves a half-written JSON behind. The tab id is the
only user-supplied path part and it may not escape the lyrics directory.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app import config

# A phone-typed lyric is short; these limits keep a stray paste from
# producing a file nobody can render.
MAX_BAR = 10000
MAX_LINES = 2000
MAX_LINE_CHARS = 300

_BAR_KEY = re.compile(r"^[0-9]{1,5}$")


class LyricsLocked(Exception):
    """A save hit a locked sidecar (v2.18); the route turns it into a 409."""


def lyrics_dir() -> Path:
    """Return the private lyrics directory (created on first write)."""
    return Path(config.DATA_DIR) / "lyrics"


def lyrics_path(tab_id: str) -> Path:
    """Resolve the sidecar path; the tab id never escapes the folder."""
    name = str(tab_id or "").strip()
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        raise ValueError("invalid tab id")
    return lyrics_dir() / f"{name}.json"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_measures(raw: Any) -> dict[str, str]:
    """Validate and normalize the ``{"bar": "text"}`` mapping.

    Raises ``ValueError`` with a user-readable message, which the route turns
    into a 422. Bars are returned in numeric order so the sidecar is stable.
    """
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("Sanat pitää antaa muodossa {tahti: teksti}.")
    if len(raw) > MAX_LINES:
        raise ValueError(f"Sanoja voi olla enintään {MAX_LINES} rivillä.")

    cleaned: dict[int, str] = {}
    for key, value in raw.items():
        bar_text = str(key).strip()
        if not _BAR_KEY.match(bar_text):
            raise ValueError(f"Tahdin numero ei kelpaa: {key}")
        bar = int(bar_text)
        if bar < 1:
            raise ValueError(f"Tahdin numero ei kelpaa: {key}")
        if bar > MAX_BAR:
            raise ValueError(f"Tahdin numero on liian suuri: {bar}")
        if not isinstance(value, str):
            raise ValueError(f"Tahdin {bar} sanat eivät ole tekstiä.")
        # A newline inside one line would break the one-line overlay; the
        # editor treats a new line as a new bar instead.
        text = " ".join(value.split())
        if not text:
            continue
        if len(text) > MAX_LINE_CHARS:
            raise ValueError(
                f"Tahdin {bar} sanat ovat liian pitkät (max {MAX_LINE_CHARS} merkkiä)."
            )
        cleaned[bar] = text

    return {str(bar): cleaned[bar] for bar in sorted(cleaned)}


def read(tab_id: str) -> dict[str, Any]:
    """Return the stored lyrics; a missing or unreadable file means no lyrics."""
    path = lyrics_path(tab_id)
    payload: dict[str, Any] = {
        "tab_id": tab_id,
        "measures": {},
        "updated_at": "",
        "locked": False,
    }
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return payload
    if not isinstance(raw, dict):
        return payload
    try:
        payload["measures"] = clean_measures(raw.get("measures"))
    except ValueError:
        # A hand-edited file must never break the viewer; the next save
        # rewrites it in the correct shape.
        payload["measures"] = {}
    payload["updated_at"] = str(raw.get("updated_at") or "")
    payload["locked"] = raw.get("locked") is True
    return payload


def _store(tab_id: str, payload: dict[str, Any]) -> None:
    """Write one sidecar payload atomically (temp file + ``os.replace``)."""
    path = lyrics_path(tab_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def write(tab_id: str, measures: Any) -> dict[str, Any]:
    """Store the lyrics atomically and return what was saved.

    Raises ``LyricsLocked`` when the sidecar is locked: a finished lyric may
    not be rewritten by a stray bar click or a late paste (v2.18).
    """
    if read(tab_id).get("locked"):
        raise LyricsLocked("Sanat on lukittu. Avaa lukitus ennen tallennusta.")
    cleaned = clean_measures(measures)
    payload = {
        "tab_id": tab_id,
        "updated_at": _now(),
        "measures": cleaned,
        "locked": False,
    }
    _store(tab_id, payload)
    return payload


def set_locked(tab_id: str, locked: bool) -> dict[str, Any]:
    """Lock or unlock the sidecar; the stored lines are kept as they are."""
    existing = read(tab_id)
    measures = existing.get("measures")
    payload = {
        "tab_id": tab_id,
        "updated_at": _now(),
        "measures": measures if isinstance(measures, dict) else {},
        "locked": bool(locked),
    }
    _store(tab_id, payload)
    return payload


def delete(tab_id: str) -> bool:
    """Remove the sidecar when the tab itself is deleted."""
    try:
        path = lyrics_path(tab_id)
    except ValueError:
        return False
    try:
        path.unlink()
    except OSError:
        return False
    return True
