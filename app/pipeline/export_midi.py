"""Export a TabDocument to a Standard MIDI file."""

from __future__ import annotations

from pathlib import Path

from app.pipeline.model import TabDocument, seconds_from_ticks


def export_midi(document: TabDocument, path: str | Path) -> Path:
    import pretty_midi

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    midi = pretty_midi.PrettyMIDI(initial_tempo=float(document.bpm))
    instrument = pretty_midi.Instrument(program=25, name="Guitar")

    for measure in document.measures:
        for note in measure.notes:
            start = seconds_from_ticks(note.start_tick, document.bpm)
            end = seconds_from_ticks(
                note.start_tick + note.duration_ticks, document.bpm
            )
            if end <= start:
                continue
            instrument.notes.append(
                pretty_midi.Note(
                    velocity=max(1, min(127, note.velocity)),
                    pitch=max(0, min(127, note.pitch)),
                    start=start,
                    end=end,
                )
            )

    midi.instruments.append(instrument)
    midi.write(str(output))
    return output
