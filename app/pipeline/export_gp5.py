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
    force_tie: bool,
):
    duration = guitarpro.Duration.fromTime(duration_ticks)
    if notes:
        beat = guitarpro.Beat(
            voice=voice,
            duration=duration,
            status=guitarpro.BeatStatus.normal,
        )
        beat.start = start_tick
        for note in notes:
            note_type = (
                guitarpro.NoteType.tie
                if force_tie or note.tie
                else guitarpro.NoteType.normal
            )
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


def _fill_track(guitarpro, track, document: TabDocument) -> None:
    for measure, model in zip(track.measures, document.measures):
        voice = measure.voices[0]
        for segment in measure_segments(model):
            offset = 0
            chunks = split_duration(segment.duration_ticks)
            for index, chunk in enumerate(chunks):
                beat = _make_beat(
                    guitarpro,
                    voice,
                    segment.start_tick + offset,
                    chunk,
                    segment.notes,
                    force_tie=index > 0,
                )
                voice.beats.append(beat)
                offset += chunk


def _make_song(guitarpro, title: str, artist: str, bpm: float) -> object:
    song = guitarpro.Song(
        versionTuple=(5, 1, 0),
        title=title,
        artist=artist,
        tempo=max(1, min(300, round(bpm))),
    )
    song.measureHeaders = []
    return song


def export_gp5(document: TabDocument, path: str | Path) -> Path:
    import guitarpro

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    song = _make_song(
        guitarpro, document.title, document.artist, document.bpm
    )

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
    _fill_track(guitarpro, track, document)

    guitarpro.write(song, str(output), encoding="utf-8")
    return output


def export_gp5_variants(
    variants: list[tuple[TabDocument, str]], path: str | Path
) -> Path:
    """Write one GP5 with a track per variant (same timeline, different layouts).

    ``variants`` is a list of ``(document, label)``. The first document defines
    the title, artist, tempo and measure headers; every document must share the
    same measure count and time signature.
    """
    import guitarpro

    if not variants:
        raise ValueError("variants must not be empty")
    first = variants[0][0]
    counts = {len(document.measures) for document, _label in variants}
    if len(counts) != 1:
        raise ValueError("all variants must have the same measure count")

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    song = _make_song(guitarpro, first.title, first.artist, first.bpm)
    numerator, denominator = first.time_signature
    time_signature = guitarpro.TimeSignature(
        numerator=numerator,
        denominator=guitarpro.Duration(denominator),
    )
    for measure in first.measures:
        song.addMeasureHeader(
            guitarpro.MeasureHeader(
                number=measure.number,
                start=measure.start_tick,
                timeSignature=time_signature,
            )
        )

    tracks = []
    for index, (document, label) in enumerate(variants, start=1):
        track = guitarpro.Track(
            song=song,
            number=index,
            name=str(label)[:40],
            fretCount=document.max_fret,
            strings=[
                guitarpro.GuitarString(number, pitch)
                for number, pitch in document.tuning.ordered_strings()
            ],
        )
        _fill_track(guitarpro, track, document)
        tracks.append(track)
    song.tracks = tracks

    guitarpro.write(song, str(output), encoding="utf-8")
    return output
