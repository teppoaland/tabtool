"""Import a ready-made Guitar Pro 5 or MusicXML tab into the library."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from app import config, db
from app.external_store import archive_external

MAX_IMPORT_BYTES = 20 * 1024 * 1024
GP_SUFFIXES = {".gp5"}
MUSICXML_SUFFIXES = {".musicxml", ".xml"}


class UnsupportedTab(ValueError):
    """The uploaded file is not a supported tab format."""


class TabTooLarge(ValueError):
    """The uploaded file exceeds the import size limit."""


class TabParseError(ValueError):
    """The uploaded file could not be parsed as a tab."""


def _clean(value: Any, fallback: str) -> str:
    text = " ".join(str(value or "").split())
    return text or fallback


def _time_signature_from_gp(header: Any) -> list[int]:
    signature = getattr(header, "timeSignature", None)
    numerator = int(getattr(signature, "numerator", 4) or 4)
    denominator = getattr(signature, "denominator", 4)
    denominator = int(getattr(denominator, "value", denominator) or 4)
    return [numerator, denominator]


def _parse_gp5(path: Path, filename: str) -> dict[str, Any]:
    import guitarpro

    try:
        song = guitarpro.parse(str(path))
    except Exception as exc:  # noqa: BLE001 - reported to the caller
        raise TabParseError(f"GP5-tiedostoa ei voitu lukea: {exc}") from exc

    title = _clean(getattr(song, "title", ""), Path(filename).stem)
    artist = _clean(getattr(song, "artist", ""), "")
    bpm = float(getattr(song, "tempo", 120) or 120)
    headers = list(getattr(song, "measureHeaders", []) or [])
    measures = len(headers)
    notes = 0
    for track in getattr(song, "tracks", []) or []:
        for measure in getattr(track, "measures", []) or []:
            for voice in getattr(measure, "voices", []) or []:
                for beat in getattr(voice, "beats", []) or []:
                    notes += len(getattr(beat, "notes", []) or [])

    tuning = "custom"
    tracks = list(getattr(song, "tracks", []) or [])
    if tracks:
        values = {
            int(string.number): int(string.value)
            for string in getattr(tracks[0], "strings", []) or []
        }
        if [values.get(number) for number in range(1, 7)] == [
            64,
            59,
            55,
            50,
            45,
            40,
        ]:
            tuning = "standard"

    time_signature = _time_signature_from_gp(
        headers[0] if headers else None
    )
    return {
        "title": title,
        "artist": artist,
        "bpm": bpm,
        "time_signature": time_signature,
        "tuning": tuning,
        "measures": measures,
        "detected_notes": notes,
        "tab_notes": notes,
        "warnings": [],
    }


def _parse_musicxml(path: Path, filename: str) -> dict[str, Any]:
    try:
        from music21 import converter, meter
    except Exception as exc:  # noqa: BLE001 - optional heavy dependency
        raise TabParseError(f"music21 ei ole käytettävissä: {exc}") from exc

    try:
        score = converter.parse(str(path))
    except Exception as exc:  # noqa: BLE001 - reported to the caller
        raise TabParseError(f"MusicXML-tiedostoa ei voitu lukea: {exc}") from exc

    metadata = getattr(score, "metadata", None)
    title_value = ""
    if metadata is not None:
        title_value = getattr(metadata, "title", "") or getattr(
            metadata, "movementName", ""
        )
    title = _clean(title_value, Path(filename).stem)
    artist = _clean(
        getattr(metadata, "composer", "") if metadata is not None else "",
        "",
    )

    parts = list(getattr(score, "parts", []) or [])
    measures = (
        len(list(parts[0].getElementsByClass("Measure"))) if parts else 0
    )
    notes = len(list(score.recurse().notes))

    bpm = 120.0
    try:
        boundaries = score.metronomeMarkBoundaries()
    except Exception:
        boundaries = []
    if boundaries:
        number = getattr(boundaries[0][2], "number", None)
        try:
            bpm = float(number) if number else 120.0
        except (TypeError, ValueError):
            bpm = 120.0

    time_signature = [4, 4]
    try:
        signature = next(
            iter(score.recurse().getElementsByClass(meter.TimeSignature)),
            None,
        )
        if signature is not None:
            time_signature = [
                int(signature.numerator),
                int(signature.denominator),
            ]
    except Exception:
        pass

    return {
        "title": title,
        "artist": artist,
        "bpm": bpm,
        "time_signature": time_signature,
        "tuning": "standard",
        "measures": measures,
        "detected_notes": notes,
        "tab_notes": notes,
        "warnings": [],
    }


def _write_meta(path: Path, meta: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    os.replace(temporary, path)


def import_tab_bytes(data: bytes, filename: str) -> dict[str, Any]:
    """Store an uploaded tab, register it, and return its database row."""
    suffix = Path(filename).suffix.lower()
    if suffix in GP_SUFFIXES:
        kind = "gp5"
        stored_name = "tab.gp5"
    elif suffix in MUSICXML_SUFFIXES:
        kind = "musicxml"
        stored_name = "tab.musicxml"
    else:
        raise UnsupportedTab(
            "Tuo GP5- tai MusicXML-tiedosto (.gp5, .musicxml, .xml)."
        )
    if not data:
        raise TabParseError("Tiedosto on tyhjä.")
    if len(data) > MAX_IMPORT_BYTES:
        raise TabTooLarge(
            f"Tiedosto on liian suuri (max {MAX_IMPORT_BYTES // (1024 * 1024)} MB)."
        )

    tab_id = db.new_id()
    tabs_root = Path(config.DATA_DIR) / "tabs"
    tabs_root.mkdir(parents=True, exist_ok=True)
    pending = tabs_root / f".pending-import-{tab_id}"
    final = tabs_root / tab_id
    pending.mkdir(parents=True, exist_ok=False)
    try:
        stored_path = pending / stored_name
        stored_path.write_bytes(data)
        if kind == "gp5":
            parsed = _parse_gp5(stored_path, filename)
        else:
            parsed = _parse_musicxml(stored_path, filename)

        meta = {
            "title": parsed["title"],
            "artist": parsed["artist"],
            "source": f"import:{Path(filename).name}",
            "source_type": "import",
            "duration_seconds": 0,
            "bpm": parsed["bpm"],
            "time_signature": parsed["time_signature"],
            "tuning": parsed["tuning"],
            "grid_division": 16,
            "pipeline_version": "import",
            "options": {},
            "model": None,
            "stem": "import",
            "detected_notes": parsed["detected_notes"],
            "tab_notes": parsed["tab_notes"],
            "measures": parsed["measures"],
            "warnings": [],
            "created_at": db.utc_now(),
            "files": {kind: stored_name},
            "audio_path": "",
        }
        _write_meta(pending / "meta.json", meta)
        if final.exists():
            raise TabParseError("Tab-hakemisto on jo olemassa.")
        os.replace(pending, final)
    except Exception:
        shutil.rmtree(pending, ignore_errors=True)
        raise

    try:
        db.import_tabs_from_disk()
    except Exception:
        shutil.rmtree(final, ignore_errors=True)
        raise
    tab = db.get_tab(tab_id)
    if tab is None:
        shutil.rmtree(final, ignore_errors=True)
        raise TabParseError("Tabia ei saatu rekisteröityä.")
    try:
        archive_external(
            final / stored_name,
            "tabs",
            str(meta.get("artist") or ""),
            str(meta.get("title") or ""),
        )
    except Exception:  # noqa: BLE001 - archive must not break the import
        pass
    return tab
