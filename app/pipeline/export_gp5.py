"""Export a TabDocument to Guitar Pro 5 (.gp5)."""

from __future__ import annotations

from pathlib import Path

from app.pipeline.model import TabDocument, TabNote
from app.pipeline.segments import measure_segments, split_duration


def _make_beat(
    guitarpro,
    voice,
    start_tick: int,
    duration_ticks: int,
    notes: tuple[TabNote, ...],
    tie: bool,
):
    duration = guitarpro.Duration.fromTime(duration_ticks)
    if notes:
        beat = guitarpro.Beat(
            voice=voice,
            duration=duration,
            status=guitarpro.BeatStatus.normal,
        )
        beat.start = start_tick
        note_type = guitarpro.NoteType.tie if tie else guitarpro.NoteType.normal
        for note in notes:
            beat.notes.append(
                guitarpro.Note(
                    beat=beat,
                    value=note.fret,
                    string=note.string,
                    velocity=max(1, min(127, note.velocity)),
                    type=note_type,
                )
            )
    else:
        beat = guitarpro.Beat(
            voice=voice,
            duration=duration,
            status=guitarpro.BeatStatus.rest,
        )
        beat.start = start_tick
    return beat


def export_gp5(document: TabDocument, path: str | Path) -> Path:
    import guitarpro

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    song = guitarpro.Song(
        versionTuple=(5, 1, 0),
        title=document.title,
        artist=document.artist,
        tempo=max(1, min(300, round(document.bpm))),
    )
    song.measureHeaders = []

    numerator, denominator = document.time_signature
    time_signature = guitarpro.TimeSignature(
        numerator=numerator,
        denominator=guitarpro.Duration(denominator),
    )
    for measure in document.measures:
        header = guitarpro.MeasureHeader(
            number=measure.number,
            start=measure.start_tick,
            timeSignature=time_signature,
        )
        song.addMeasureHeader(header)

    track = guitarpro.Track(
        song=song,
        number=1,
        name="Guitar",
        fretCount=document.max_fret,
        strings=[
            guitarpro.GuitarString(number, pitch)
            for number, pitch in document.tuning.ordered_strings()
        ],
    )
    song.tracks = [track]

    for measure, model in zip(track.measures, document.measures):
        voice = measure.voices[0]
        for segment in measure_segments(model):
            offset = 0
            chunks = split_duration(segment.duration_ticks)
            for index, chunk in enumerate(chunks):
                tie = segment.notes[0].tie if segment.notes else False
                if index > 0:
                    tie = True
                beat = _make_beat(
                    guitarpro,
                    voice,
                    segment.start_tick + offset,
                    chunk,
                    segment.notes,
                    tie,
                )
                voice.beats.append(beat)
                offset += chunk

    guitarpro.write(song, str(output))
    return output
