"""Export tests using a small synthetic tab document."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from app.pipeline.build import build_document
from app.pipeline.export_gp5 import export_gp5
from app.pipeline.export_midi import export_midi
from app.pipeline.export_musicxml import export_musicxml
from app.pipeline.model import STANDARD_TUNING, TabNote
from app.pipeline.segments import measure_segments


def _document():
    chord = [
        TabNote(40, 6, 0, 0, 960),
        TabNote(47, 5, 2, 0, 960),
        TabNote(52, 4, 2, 0, 960),
        TabNote(56, 3, 1, 0, 960),
        TabNote(59, 2, 0, 0, 960),
        TabNote(64, 1, 0, 0, 960),
    ]
    single = [TabNote(67, 1, 3, 960, 1920)]
    return build_document(
        title="Test Song",
        artist="TabTool",
        bpm=120,
        time_signature="4/4",
        tuning=STANDARD_TUNING,
        tab_notes=chord + single,
        measure_count=2,
    )


def test_segments_cover_measure() -> None:
    document = _document()
    segments = measure_segments(document.measures[0])
    assert segments
    assert segments[0].start_tick == 0
    assert segments[-1].end_tick == document.measures[0].end_tick
    assert sum(segment.duration_ticks for segment in segments) == (
        document.measures[0].length_ticks
    )


def test_export_gp5(tmp_path: Path) -> None:
    import guitarpro

    path = export_gp5(_document(), tmp_path / "tab.gp5")
    assert path.exists() and path.stat().st_size > 0
    song = guitarpro.parse(str(path))
    assert song.title == "Test Song"
    assert len(song.measureHeaders) == 2
    assert len(song.tracks) == 1
    assert sum(
        len(beat.notes)
        for measure in song.tracks[0].measures
        for voice in measure.voices
        for beat in voice.beats
    ) > 0


def test_export_musicxml(tmp_path: Path) -> None:
    path = export_musicxml(_document(), tmp_path / "tab.musicxml")
    assert path.exists() and path.stat().st_size > 0
    root = ET.parse(path).getroot()
    assert root.tag == "score-partwise"
    measures = root.findall(".//part/measure")
    assert len(measures) == 2
    assert root.find(".//technical/string") is not None


def test_export_midi(tmp_path: Path) -> None:
    import pretty_midi

    path = export_midi(_document(), tmp_path / "tab.mid")
    assert path.exists() and path.stat().st_size > 0
    midi = pretty_midi.PrettyMIDI(str(path))
    assert sum(len(instrument.notes) for instrument in midi.instruments) > 0
