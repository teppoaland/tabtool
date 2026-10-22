from __future__ import annotations

from pathlib import Path

import guitarpro
import pytest

from app.pipeline.build import build_document
from app.pipeline.export_gp5 import export_gp5
from app.pipeline.model import STANDARD_TUNING, TabNote
from app.tab_edit import TabEditError, count_notes, expand_repeat

BARS = 4
BAR_TICKS = 3840


def _song(tmp_path: Path, repeat: bool = True):
    """A 4-bar GP5 with one distinct note per bar (fret = bar number)."""
    notes = [
        TabNote(40 + index, 6, index + 1, index * BAR_TICKS, 960)
        for index in range(BARS)
    ]
    document = build_document(
        title="Repeat Song",
        artist="Repeat Band",
        bpm=120,
        time_signature="4/4",
        tuning=STANDARD_TUNING,
        tab_notes=notes,
        measure_count=BARS,
    )
    path = tmp_path / "repeat.gp5"
    export_gp5(document, path)
    if not repeat:
        return guitarpro.parse(str(path), encoding="utf-8")

    song = guitarpro.parse(str(path), encoding="utf-8")
    song.measureHeaders[1].isRepeatOpen = True
    song.measureHeaders[1].repeatClose = 1  # GP5 stores plays - 1
    guitarpro.write(song, str(path), encoding="utf-8")
    return guitarpro.parse(str(path), encoding="utf-8")


def _frets(song, track_index: int = 0) -> list[list[int]]:
    return [
        [
            note.value
            for voice in measure.voices
            for beat in voice.beats
            for note in beat.notes
        ]
        for measure in song.tracks[track_index].measures
    ]


def test_expand_repeat_materialises_the_block(tmp_path: Path) -> None:
    song = _song(tmp_path)
    assert len(song.measureHeaders) == BARS
    assert count_notes(song) == BARS

    stats = expand_repeat(song, bar=2, times=17)

    assert stats["bars_before"] == BARS
    assert stats["bars_after"] == BARS + 16
    assert stats["plays"] == 17
    assert stats["notes_added"] == 16
    assert len(song.measureHeaders) == BARS + 16

    headers = song.measureHeaders
    assert [header.number for header in headers] == list(range(1, BARS + 17))
    assert all(not header.isRepeatOpen for header in headers)
    assert all((header.repeatClose or -1) < 0 for header in headers)
    steps = {headers[index + 1].start - headers[index].start for index in range(len(headers) - 1)}
    assert steps == {BAR_TICKS}

    frets = _frets(song)
    assert frets[0] == [1]
    # Bar 2 is played 17 times in total: bars 2…18.
    assert all(frets[index] == [2] for index in range(1, 18))
    assert frets[18] == [3]
    assert frets[19] == [4]
    assert len(frets) == len(headers)


def test_expand_repeat_survives_a_write_and_read(tmp_path: Path) -> None:
    song = _song(tmp_path)
    expand_repeat(song, bar=2, times=17)

    path = tmp_path / "expanded.gp5"
    guitarpro.write(song, str(path), encoding="utf-8")
    stored = guitarpro.parse(str(path), encoding="utf-8")

    assert len(stored.measureHeaders) == BARS + 16
    assert count_notes(stored) == BARS + 16
    assert all(not header.isRepeatOpen for header in stored.measureHeaders)
    assert all((header.repeatClose or -1) < 0 for header in stored.measureHeaders)
    assert _frets(stored)[16] == [2]


def test_expand_repeat_clears_the_repeat_texts(tmp_path: Path) -> None:
    song = _song(tmp_path)
    song.tracks[0].measures[1].voices[0].beats[0].text = "Should be played 17 times"

    expand_repeat(song, bar=2, times=3)

    texts = [
        beat.text
        for measure in song.tracks[0].measures
        for voice in measure.voices
        for beat in voice.beats
    ]
    assert texts.count("Should be played 17 times") == 1


def test_expand_repeat_needs_a_repeat_mark(tmp_path: Path) -> None:
    song = _song(tmp_path, repeat=False)
    with pytest.raises(TabEditError):
        expand_repeat(song, bar=2, times=17)


def test_expand_repeat_rejects_a_single_play(tmp_path: Path) -> None:
    song = _song(tmp_path)
    with pytest.raises(TabEditError):
        expand_repeat(song, bar=2, times=1)


def test_expand_repeat_rejects_unknown_bar(tmp_path: Path) -> None:
    song = _song(tmp_path)
    with pytest.raises(TabEditError):
        expand_repeat(song, bar=99, times=17)
