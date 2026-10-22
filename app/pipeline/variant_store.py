"""Serialize a TabDocument for a generated fingering variant (v1.72).

The viewer reads a single combined GP5 with one track per variant. To finalize
("keep this one, delete the rest") without re-running the ML pipeline, the
variant's notes are snapshotted to JSON. Finalizing restores the snapshot at
the tab's current BPM so a later TAB BPM change is never lost.
"""

from __future__ import annotations

from app.pipeline.model import TabDocument, TabMeasure, TabNote, get_tuning


def snapshot_document(document: TabDocument) -> dict:
    return {
        "title": document.title,
        "artist": document.artist,
        "bpm": document.bpm,
        "time_signature": list(document.time_signature),
        "tuning": document.tuning.key,
        "max_fret": document.max_fret,
        "grid_division": document.grid_division,
        "measures": [
            {
                "number": measure.number,
                "start_tick": measure.start_tick,
                "length_ticks": measure.length_ticks,
                "notes": [
                    {
                        "pitch": note.pitch,
                        "string": note.string,
                        "fret": note.fret,
                        "start_tick": note.start_tick,
                        "duration_ticks": note.duration_ticks,
                        "velocity": note.velocity,
                        "tie": note.tie,
                    }
                    for note in measure.notes
                ],
            }
            for measure in document.measures
        ],
    }


def restore_document(snapshot: dict) -> TabDocument:
    tuning = get_tuning(str(snapshot["tuning"]))
    measures = [
        TabMeasure(
            number=int(measure["number"]),
            start_tick=int(measure["start_tick"]),
            length_ticks=int(measure["length_ticks"]),
            notes=[
                TabNote(
                    pitch=int(note["pitch"]),
                    string=int(note["string"]),
                    fret=int(note["fret"]),
                    start_tick=int(note["start_tick"]),
                    duration_ticks=int(note["duration_ticks"]),
                    velocity=int(note.get("velocity", 95)),
                    tie=bool(note.get("tie", False)),
                )
                for note in measure["notes"]
            ],
        )
        for measure in snapshot["measures"]
    ]
    return TabDocument(
        title=str(snapshot.get("title") or "Tab"),
        artist=str(snapshot.get("artist") or ""),
        bpm=float(snapshot["bpm"]),
        time_signature=tuple(snapshot["time_signature"]),
        tuning=tuning,
        measures=measures,
        max_fret=int(snapshot.get("max_fret", 24)),
        grid_division=int(snapshot.get("grid_division", 16)),
    )
