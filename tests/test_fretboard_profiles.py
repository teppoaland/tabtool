"""Fretboard profiles produce different, deterministic, playable layouts (v1.72)."""

from __future__ import annotations

from app.pipeline.fretboard import PROFILES, assign_fretboard
from app.pipeline.model import STANDARD_TUNING, QuantizedNote


def _note(pitch: int, start: int = 0, duration: int = 480) -> QuantizedNote:
    return QuantizedNote(
        pitch=pitch, start_tick=start, duration_ticks=duration, velocity=95
    )


RIFF = [52, 53, 55, 57, 59, 60]


def _run(profile: str) -> list[tuple[int, int]]:
    notes = [_note(pitch, index * 480) for index, pitch in enumerate(RIFF)]
    tab_notes, warnings = assign_fretboard(
        notes, STANDARD_TUNING, profile=profile
    )
    assert not any("Dropped" in w or "outside" in w for w in warnings)
    return [(note.string, note.fret) for note in tab_notes]


def test_profiles_exist_with_distinct_labels() -> None:
    assert list(PROFILES) == ["open", "box", "smooth"]
    assert len({profile.label for profile in PROFILES.values()}) == 3


def test_profiles_are_deterministic() -> None:
    for key in PROFILES:
        assert _run(key) == _run(key)


def test_profiles_are_pitch_valid() -> None:
    for key in PROFILES:
        for string, fret in _run(key):
            assert STANDARD_TUNING.open_pitch(string) + fret in RIFF


def test_open_profile_uses_open_strings_when_available() -> None:
    notes = [_note(59, 0)]
    tab_notes, _ = assign_fretboard(notes, STANDARD_TUNING, profile="open")
    assert [(note.string, note.fret) for note in tab_notes] == [(2, 0)]


def test_profiles_differ_on_a_mid_neck_phrase() -> None:
    results = {key: _run(key) for key in PROFILES}
    joined = {key: tuple(value) for key, value in results.items()}
    assert len(set(joined.values())) >= 2, joined
