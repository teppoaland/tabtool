"""Prune transcription noise before quantizing (v1.73)."""

from __future__ import annotations

from app.pipeline.model import NoteEvent
from app.pipeline.prune import prune_notes


def _n(pitch: int, start: float, end: float, velocity: int = 100) -> NoteEvent:
    return NoteEvent(
        pitch=pitch, start=start, end=end, velocity=velocity
    )


def test_drops_quiet_octave_harmonic() -> None:
    notes = [_n(40, 0.0, 0.5, 100), _n(52, 0.0, 0.2, 40)]
    out = prune_notes(notes)
    assert [note.pitch for note in out] == [40]


def test_keeps_loud_octave_double_stop() -> None:
    notes = [_n(40, 0.0, 0.5, 90), _n(52, 0.0, 0.5, 90)]
    out = prune_notes(notes)
    assert sorted(note.pitch for note in out) == [40, 52]


def test_caps_polyphony() -> None:
    notes = [_n(pitch, 0.0, 0.5, 100) for pitch in (40, 45, 50, 55, 59, 64)]
    out = prune_notes(notes)
    assert len(out) == 4


def test_onsets_beyond_window_are_kept_separate() -> None:
    notes = [_n(40, 0.0, 0.1, 100), _n(52, 0.2, 0.3, 40)]
    out = prune_notes(notes)
    assert len(out) == 2


def test_prune_is_deterministic() -> None:
    notes = [_n(40, 0.0, 0.5, 100), _n(52, 0.0, 0.2, 40), _n(59, 0.0, 0.5, 80)]
    assert prune_notes(notes) == prune_notes(notes)
