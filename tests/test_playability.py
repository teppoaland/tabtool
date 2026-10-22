"""Playability metrics reward natural fingerings (v1.72)."""

from __future__ import annotations

from app.pipeline.model import TabNote
from app.pipeline.playability import score_fretboard


def _note(
    pitch: int, string: int, fret: int, start: int, duration: int = 480
) -> TabNote:
    return TabNote(
        pitch=pitch,
        string=string,
        fret=fret,
        start_tick=start,
        duration_ticks=duration,
    )


def test_stationary_position_scores_higher_than_jumps() -> None:
    comfortable = [
        _note(52, 4, 2, 0),
        _note(55, 3, 0, 480),
        _note(57, 3, 2, 960),
        _note(59, 2, 0, 1440),
    ]
    jumpy = [
        _note(40, 6, 0, 0),
        _note(64, 1, 0, 480),
        _note(52, 4, 12, 960),
        _note(57, 3, 2, 1440),
    ]
    good = score_fretboard(comfortable, measure_count=1)
    bad = score_fretboard(jumpy, measure_count=1)
    assert good.score > bad.score


def test_metrics_are_computed() -> None:
    notes = [
        _note(52, 4, 2, 0),
        _note(55, 3, 0, 0),
        _note(57, 3, 2, 960),
        _note(59, 2, 0, 1440),
    ]
    result = score_fretboard(notes, measure_count=1)
    assert 0.0 <= result.score <= 10.0
    assert result.open_ratio == 0.5
    assert result.max_span == 2
    assert result.avg_fret == 1.0
    assert result.max_fret == 2
    assert result.skipped_strings == 0


def test_score_is_bounded() -> None:
    empty = score_fretboard([], measure_count=1)
    assert 0.0 <= empty.score <= 10.0
