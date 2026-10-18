"""Export a TabDocument to a compact MusicXML tab score."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from app.pipeline.model import TabDocument
from app.pipeline.segments import (
    MUSICXML_DIVISIONS,
    duration_type,
    measure_segments,
    split_duration,
)

PITCH_NAMES = ("C", "C", "D", "D", "E", "F", "F", "G", "G", "A", "A", "B")
PITCH_ALTERS = (0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0)
TICKS_PER_DIVISION = 960 // MUSICXML_DIVISIONS


def _add_pitch(note_element: ET.Element, pitch: int) -> None:
    pitch_element = ET.SubElement(note_element, "pitch")
    ET.SubElement(pitch_element, "step").text = PITCH_NAMES[pitch % 12]
    alter = PITCH_ALTERS[pitch % 12]
    if alter:
        ET.SubElement(pitch_element, "alter").text = str(alter)
    ET.SubElement(pitch_element, "octave").text = str(pitch // 12 - 1)


def _add_note(
    parent: ET.Element,
    *,
    pitch: int | None,
    string: int | None,
    fret: int | None,
    ticks: int,
    chord: bool,
    tie_start: bool,
    tie_stop: bool,
) -> None:
    note = ET.SubElement(parent, "note")
    if chord:
        ET.SubElement(note, "chord")
    if pitch is None:
        ET.SubElement(note, "rest")
    else:
        _add_pitch(note, pitch)

    ET.SubElement(note, "duration").text = str(ticks // TICKS_PER_DIVISION)
    if tie_start:
        ET.SubElement(note, "tie", {"type": "start"})
    if tie_stop:
        ET.SubElement(note, "tie", {"type": "stop"})

    ET.SubElement(note, "voice").text = "1"
    note_type, dots = duration_type(ticks)
    ET.SubElement(note, "type").text = note_type
    for _ in range(dots):
        ET.SubElement(note, "dot")

    if pitch is not None and string is not None and fret is not None:
        notations = ET.SubElement(note, "notations")
        if tie_start:
            ET.SubElement(notations, "tied", {"type": "start"})
        if tie_stop:
            ET.SubElement(notations, "tied", {"type": "stop"})
        technical = ET.SubElement(notations, "technical")
        ET.SubElement(technical, "string").text = str(string)
        ET.SubElement(technical, "fret").text = str(fret)


def _add_attributes(measure: ET.Element, document: TabDocument) -> None:
    attributes = ET.SubElement(measure, "attributes")
    ET.SubElement(attributes, "divisions").text = str(MUSICXML_DIVISIONS)
    key = ET.SubElement(attributes, "key")
    ET.SubElement(key, "fifths").text = "0"

    numerator, denominator = document.time_signature
    time = ET.SubElement(attributes, "time")


def _add_tempo(measure: ET.Element, bpm: float) -> None:
    direction = ET.SubElement(measure, "direction", {"placement": "above"})
    direction_type = ET.SubElement(direction, "direction-type")
    metronome = ET.SubElement(direction_type, "metronome")
    ET.SubElement(metronome, "beat-unit").text = "quarter"
    ET.SubElement(metronome, "per-minute").text = str(max(1, round(bpm)))
    ET.SubElement(direction, "sound", {"tempo": str(max(1, round(bpm)))})


def export_musicxml(document: TabDocument, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    root = ET.Element("score-partwise", {"version": "4.0"})
    work = ET.SubElement(root, "work")
    ET.SubElement(work, "work-title").text = document.title or "Untitled"
    identification = ET.SubElement(root, "identification")
    ET.SubElement(identification, "creator", {"type": "composer"}).text = (
        document.artist or ""
    )

    part_list = ET.SubElement(root, "part-list")
    score_part = ET.SubElement(part_list, "score-part", {"id": "P1"})
    ET.SubElement(score_part, "part-name").text = "Guitar"

    part = ET.SubElement(root, "part", {"id": "P1"})

    for measure_index, model in enumerate(document.measures):
        measure = ET.SubElement(part, "measure", {"number": str(model.number)})
        if measure_index == 0:
            _add_attributes(measure, document)
            _add_tempo(measure, document.bpm)

        for segment in measure_segments(model):
            chunks = split_duration(segment.duration_ticks)
            for chunk_index, chunk in enumerate(chunks):
                tie_start = chunk_index < len(chunks) - 1
                if segment.notes:
                    for note_index, note in enumerate(segment.notes):
                        _add_note(
                            measure,
                            pitch=note.pitch,
                            string=note.string,
                            fret=note.fret,
                            ticks=chunk,
                            chord=note_index > 0,
                            tie_start=tie_start,
                            tie_stop=chunk_index > 0 or note.tie,
                        )
                else:
                    _add_note(
                        measure,
                        pitch=None,
                        string=None,
                        fret=None,
                        ticks=chunk,
                        chord=False,
                        tie_start=False,
                        tie_stop=False,
                    )

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(output, encoding="utf-8", xml_declaration=True)
    return output

    ET.SubElement(time, "beats").text = str(numerator)
    ET.SubElement(time, "beat-type").text = str(denominator)

    clef = ET.SubElement(attributes, "clef")
    ET.SubElement(clef, "sign").text = "TAB"
    ET.SubElement(clef, "line").text = "5"

    details = ET.SubElement(attributes, "staff-details")
    ET.SubElement(details, "staff-lines").text = str(document.tuning.string_count)
    for line, (_, pitch) in enumerate(document.tuning.ordered_strings(), start=1):
        tuning = ET.SubElement(details, "staff-tuning", {"line": str(line)})
        ET.SubElement(tuning, "tuning-step").text = PITCH_NAMES[pitch % 12]
        alter = PITCH_ALTERS[pitch % 12]
        if alter:
            ET.SubElement(tuning, "tuning-alter").text = str(alter)
        ET.SubElement(tuning, "tuning-octave").text = str(pitch // 12 - 1)
