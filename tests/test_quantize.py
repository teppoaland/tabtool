"""Quantization tests."""

from __future__ import annotations

from app.pipeline.model import NoteEvent
from app.pipeline.quantize import merge_note_events, quantize_notes


def test_quarter_note_at_120_bpm() -> None:
    result = quantize_notes(
        [NoteEvent(64, 0.0, 0.5)],
        bpm=120,
        time_signature="4/4",
        grid_division=16,
        total_duration_seconds=2.0,
    )
    assert result.measure_count == 1
    assert len(result.notes) == 1
    note = result.notes[0]
    assert note.start_tick == 0
    assert note.duration_ticks == 960
    assert note.tie is False


def test_eighth_note_is_snapped() -> None:
    result = quantize_notes(
        [NoteEvent(64, 0.25, 0.5)],
        bpm=120,
        time_signature="4/4",
        grid_division=16,
        total_duration_seconds=1.0,
    )
    note = result.notes[0]
    assert note.start_tick == 480
    assert note.duration_ticks == 480


def test_note_is_split_across_measure_boundary() -> None:
    result = quantize_notes(
        [NoteEvent(64, 1.9, 2.1)],
        bpm=120,
        time_signature="4/4",
        grid_division=16,
        total_duration_seconds=2.2,
    )
    assert result.measure_count == 2
    assert len(result.notes) == 2
    first, second = result.notes
    assert first.start_tick == 3600
    assert first.duration_ticks == 240
    assert second.start_tick == 3840
    assert second.duration_ticks == 240
    assert second.tie is True


def test_duplicate_notes_are_merged() -> None:
    merged = merge_note_events(
        [NoteEvent(64, 0.0, 0.4), NoteEvent(64, 0.1, 0.5)]
    )
    assert len(merged) == 1
    assert merged[0].end == 0.5


def test_invalid_pitch_is_dropped() -> None:
    result = quantize_notes(
        [NoteEvent(200, 0.0, 0.5)],
        bpm=120,
        time_signature="4/4",
        grid_division=16,
        total_duration_seconds=1.0,
    )
    assert result.notes == []
    assert any("invalid MIDI pitch" in warning for warning in result.warnings)
