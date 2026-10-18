"""Fretboard assignment tests."""

from __future__ import annotations

from app.pipeline.fretboard import (
    assign_fretboard,
    candidates_for_pitch,
    enforce_string_monophony,
)
from app.pipeline.model import (
    DROP_D_TUNING,
    STANDARD_TUNING,
    QuantizedNote,
    TabNote,
)


def _note(pitch: int, start: int = 0, duration: int = 960) -> QuantizedNote:
    return QuantizedNote(
        pitch=pitch,
        start_tick=start,
        duration_ticks=duration,
        velocity=95,
    )


def test_open_string_candidates() -> None:
    assert (1, 0) in candidates_for_pitch(64, STANDARD_TUNING)
    assert (2, 0) in candidates_for_pitch(59, STANDARD_TUNING)
    assert (6, 0) in candidates_for_pitch(40, STANDARD_TUNING)


def test_single_open_strings_are_assigned() -> None:
    notes = [
        _note(40, 0),
        _note(45, 960),
        _note(50, 1920),
        _note(55, 2880),
    ]
    tab_notes, warnings = assign_fretboard(notes, STANDARD_TUNING)
    assert not warnings
    positions = {(note.string, note.fret) for note in tab_notes}
    assert (6, 0) in positions
    assert (5, 0) in positions
    assert (4, 0) in positions
    assert (3, 0) in positions


def test_e_major_chord_is_playable() -> None:
    pitches = [40, 47, 52, 56, 59, 64]
    notes = [_note(pitch, 0) for pitch in pitches]
    tab_notes, warnings = assign_fretboard(notes, STANDARD_TUNING, max_span=5)
    assert not warnings
    assert len(tab_notes) == 6
    strings = [note.string for note in tab_notes]
    assert len(set(strings)) == 6
    frets = [note.fret for note in tab_notes]
    assert max(frets) - min(frets) <= 5
    for note in tab_notes:
        assert (
            STANDARD_TUNING.open_pitch(note.string) + note.fret == note.pitch
        )


def test_drop_d_low_string() -> None:
    tab_notes, warnings = assign_fretboard(
        [_note(38, 0)], DROP_D_TUNING
    )
    assert not warnings
    assert [(note.string, note.fret) for note in tab_notes] == [(6, 0)]


def test_out_of_range_note_is_dropped() -> None:
    tab_notes, warnings = assign_fretboard(
        [_note(20, 0)], STANDARD_TUNING
    )
    assert tab_notes == []
    assert any("outside" in warning for warning in warnings)


def test_overlapping_same_string_is_shortened() -> None:
    notes = [
        TabNote(40, 6, 0, 0, 960),
        TabNote(40, 6, 0, 480, 960),
    ]
    result, warnings = enforce_string_monophony(notes, STANDARD_TUNING)
    assert len(result) == 2
    first, second = result
    assert first.string == 6 and first.duration_ticks == 480
    assert second.string == 6 and second.start_tick == 480
    assert warnings


def test_overlapping_note_moves_to_free_string() -> None:
    notes = [
        TabNote(45, 5, 0, 0, 960),
        TabNote(45, 5, 0, 480, 960),
    ]
    result, _ = enforce_string_monophony(notes, STANDARD_TUNING)
    assert len(result) == 2
    first, second = result
    assert first.string == 5 and first.duration_ticks == 960
    assert second.string == 6 and second.fret == 5

