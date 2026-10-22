"""Import a ready-made Guitar Pro (GP3/GP4/GP5) or MusicXML tab."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from app import config, db
from app.external_store import archive_external
from app.tuning import describe_pitches

MAX_IMPORT_BYTES = 20 * 1024 * 1024
GP_SUFFIXES = {".gp3", ".gp4", ".gp5"}
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


def _normalize_gp5(song: Any, path: Path) -> None:
    """Rewrite a GP3/GP4 song as a real GP5 file in place.

    alphaTab and the GP5 export expect version 5 data; PyGuitarPro reads all
    three versions, so a GP4 upload is converted instead of rejected.
    """
    version = getattr(song, "versionTuple", (5, 1, 0)) or (5, 1, 0)
    try:
        major = int(tuple(version)[0])
    except (TypeError, ValueError, IndexError):
        major = 5
    if major >= 5:
        return

    import guitarpro

    temporary = path.with_name(path.name + ".tmp")
    try:
        guitarpro.write(song, str(temporary), version=(5, 1, 0), encoding="utf-8")
        os.replace(temporary, path)
    except Exception as exc:  # noqa: BLE001 - reported to the caller
        temporary.unlink(missing_ok=True)
        raise TabParseError(
            f"GP{max(major, 3)}-tiedoston muunto GP5:ksi epäonnistui: {exc}"
        ) from exc


def _parse_gp(path: Path, filename: str) -> dict[str, Any]:
    import guitarpro

    try:
        try:
            song = guitarpro.parse(str(path), encoding="utf-8")
        except UnicodeDecodeError:
            song = guitarpro.parse(str(path), encoding="cp1252")
    except Exception as exc:  # noqa: BLE001 - reported to the caller
        raise TabParseError(f"GP-tiedostoa ei voitu lukea: {exc}") from exc

    _normalize_gp5(song, path)

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
    tuning_notes: list[str] = []
    tuning_label = ""
    tracks = list(getattr(song, "tracks", []) or [])
    if tracks:
        values = {
            int(string.number): int(string.value)
            for string in getattr(tracks[0], "strings", []) or []
        }
        numbers = sorted(values, reverse=True)
        ordered = [values[number] for number in numbers]
        if ordered and all(isinstance(value, int) for value in ordered):
            info = describe_pitches(ordered)
            tuning = str(info["key"])
            tuning_notes = list(info["notes"])
            tuning_label = str(info["text"])

    time_signature = _time_signature_from_gp(
        headers[0] if headers else None
    )
    return {
        "title": title,
        "artist": artist,
        "bpm": bpm,
        "time_signature": time_signature,
        "tuning": tuning,
        "tuning_notes": tuning_notes,
        "tuning_label": tuning_label,
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
        "tuning_notes": [],
        "tuning_label": "Standard E · EADGBE",
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
            "Tuo GP3/GP4/GP5- tai MusicXML-tiedosto "
            "(.gp3, .gp4, .gp5, .musicxml, .xml)."
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
            parsed = _parse_gp(stored_path, filename)
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
            "tuning_notes": parsed.get("tuning_notes", []),
            "tuning_label": parsed.get("tuning_label", ""),
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
