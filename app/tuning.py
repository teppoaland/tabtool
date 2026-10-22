"""Human-readable tuning descriptions (e.g. ``D Standard · DGCFAD``).

The GP5 file knows the exact open strings; ``tabs.tuning`` alone only holds a
key like ``standard`` or ``custom``. These helpers turn MIDI pitches into a
label, the letter names and a per-string list, and recognise the presets in
``app.pipeline.model``.
"""

from __future__ import annotations

from typing import Any, Sequence

from app.pipeline.model import TUNINGS, Tuning

_SHARPS = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
_FLATS = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")


def _low_to_high(tuning: Tuning) -> tuple[int, ...]:
    return tuple(pitch for _number, pitch in sorted(tuning.strings, reverse=True))


def _letter(pitch: int) -> str:
    return _FLATS[int(pitch) % 12]


def note_name(pitch: int) -> str:
    """``40`` -> ``E2`` (flats for black keys, as guitarists write them)."""
    return f"{_letter(int(pitch))}{int(pitch) // 12 - 1}"


def _describe(values: Sequence[int], key: str, label: str) -> dict[str, object]:
    pitches = tuple(int(value) for value in values)
    letters = "".join(_letter(pitch) for pitch in pitches)
    return {
        "key": key,
        "label": label,
        "short": letters,
        "notes": [note_name(pitch) for pitch in pitches],
        "text": f"{label} · {letters}",
    }


def describe_pitches(pitches: Sequence[int]) -> dict[str, object]:
    """Describe open strings given low string first (E2, A2, …)."""
    values = tuple(int(pitch) for pitch in pitches)
    for tuning in TUNINGS.values():
        if _low_to_high(tuning) == values:
            return _describe(values, tuning.key, tuning.name)
    return _describe(values, "custom", "Custom")


def describe_tuning(key: str) -> dict[str, object] | None:
    tuning = TUNINGS.get(str(key or "").strip().lower())
    if tuning is None:
        return None
    return _describe(_low_to_high(tuning), tuning.key, tuning.name)


def describe_key(key: str) -> str:
    """``drop_d`` -> ``Drop D``; unknown keys are returned title-cased."""
    tuning = TUNINGS.get(str(key or "").strip().lower())
    if tuning is not None:
        return tuning.name
    text = str(key or "").strip()
    return text[:1].upper() + text[1:] if text else ""


def open_strings(song: Any) -> list[int]:
    """Open strings (low string first) of the tab's guitar track.

    Multi-track GP5s often list vocals or keys first, so reading track 0 gave
    the wrong tuning (a Drop D guitar showed as ``Standard E``). The guitar is
    the six-string track with the most notes; drums store zero pitches and are
    skipped.
    """
    best_score: tuple[int, int, int] | None = None
    best_pitches: list[int] = []
    fallback: list[int] = []
    for track in getattr(song, "tracks", []) or []:
        values = {
            int(string.number): int(string.value)
            for string in getattr(track, "strings", []) or []
        }
        if not values:
            continue
        pitches = [values[number] for number in sorted(values, reverse=True)]
        if any(pitch <= 0 for pitch in pitches):
            continue
        if not fallback:
            fallback = pitches
        notes = 0
        for measure in getattr(track, "measures", []) or []:
            for voice in getattr(measure, "voices", []) or []:
                for beat in getattr(voice, "beats", []) or []:
                    notes += len(getattr(beat, "notes", []) or [])
        score = (1 if len(pitches) == 6 else 0, notes, len(pitches))
        if best_score is None or score > best_score:
            best_score = score
            best_pitches = pitches
    return best_pitches or fallback
