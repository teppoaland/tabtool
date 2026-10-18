"""Assemble the tab document from quantized and fretboard notes."""

from __future__ import annotations

from app.pipeline.model import (
    DEFAULT_GRID_DIVISION,
    TabDocument,
    TabMeasure,
    TabNote,
    Tuning,
    measure_length_ticks,
    parse_time_signature,
)


def build_document(
    *,
    title: str,
    artist: str,
    bpm: float,
    time_signature: str | tuple[int, int],
    tuning: Tuning,
    tab_notes: list[TabNote],
    measure_count: int,
    max_fret: int = 24,
    grid_division: int = DEFAULT_GRID_DIVISION,
    source_audio: str = "",
    warnings: list[str] | None = None,
) -> TabDocument:
    numerator, denominator = parse_time_signature(time_signature)
    length = measure_length_ticks(numerator, denominator)
    count = max(1, measure_count)
    measures = [
        TabMeasure(
            number=index + 1,
            start_tick=index * length,
            length_ticks=length,
        )
        for index in range(count)
    ]

    issues = list(warnings or [])
    for note in tab_notes:
        measure_index = note.start_tick // length
        if 0 <= measure_index < count:
            measures[measure_index].notes.append(note)
        else:
            issues.append(
                f"Dropped note at tick {note.start_tick} outside {count} measures."
            )

    for measure in measures:
        measure.notes.sort(key=lambda note: (note.start_tick, note.string))

    return TabDocument(
        title=title,
        artist=artist,
        bpm=float(bpm),
        time_signature=(numerator, denominator),
        tuning=tuning,
        measures=measures,
        max_fret=max_fret,
        grid_division=grid_division,
        source_audio=source_audio,
        warnings=issues,
    )
