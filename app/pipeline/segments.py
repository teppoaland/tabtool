"""Turn a measure's notes into continuous note/rest segments."""

from __future__ import annotations

from dataclasses import dataclass

from app.pipeline.model import GRID_TICKS, TabMeasure, TabNote

# Durations that can be written as a single Guitar Pro / MusicXML note.
# Values are in GP ticks (960 per quarter note).
ALLOWED_TICKS: tuple[int, ...] = (
    3840,  # whole
    2880,  # half dotted
    1920,  # half
    1440,  # quarter dotted
    960,   # quarter
    720,   # eighth dotted
    480,   # eighth
    360,   # 16th dotted
    240,   # 16th
    180,   # 32nd dotted
    120,   # 32nd
    90,    # 64th dotted
    60,    # 64th
)

# MusicXML divisions per quarter. 16 lets us express 1/16, dotted 1/16,
# 1/32 and dotted 1/32 as integer durations.
MUSICXML_DIVISIONS = 16


@dataclass(frozen=True)
class Segment:
    start_tick: int
    duration_ticks: int
    notes: tuple[TabNote, ...]

    @property
    def end_tick(self) -> int:
        return self.start_tick + self.duration_ticks

    @property
    def is_rest(self) -> bool:
        return not self.notes


def split_duration(ticks: int) -> list[int]:
    """Split a duration into representable note lengths (largest first)."""
    if ticks <= 0:
        return []
    chunks: list[int] = []
    remaining = ticks
    while remaining > 0:
        for chunk in ALLOWED_TICKS:
            if chunk <= remaining:
                chunks.append(chunk)
                remaining -= chunk
                break
        else:
            raise ValueError(f"Cannot split duration {ticks} ticks")
    return chunks


def duration_type(ticks: int) -> tuple[str, int]:
    """Return (MusicXML type, dot count) for an allowed duration."""
    mapping = {
        3840: ("whole", 0),
        2880: ("half", 1),
        1920: ("half", 0),
        1440: ("quarter", 1),
        960: ("quarter", 0),
        720: ("eighth", 1),
        480: ("eighth", 0),
        360: ("16th", 1),
        240: ("16th", 0),
        180: ("32nd", 1),
        120: ("32nd", 0),
        90: ("64th", 1),
        60: ("64th", 0),
    }
    if ticks not in mapping:
        raise ValueError(f"Unsupported duration for MusicXML: {ticks}")
    return mapping[ticks]


def measure_segments(
    measure: TabMeasure, grid_ticks: int = GRID_TICKS
) -> list[Segment]:
    """Return note/rest segments covering the whole measure.

    A new segment starts whenever the active note set changes or a note is
    re-articulated at the same position.
    """
    del grid_ticks  # boundaries are derived from the notes; kept for API symmetry
    measure_end = measure.end_tick

    boundaries = {measure.start_tick, measure_end}
    for note in measure.notes:
        start = max(measure.start_tick, note.start_tick)
        end = min(measure_end, note.start_tick + note.duration_ticks)
        if end > start:
            boundaries.add(start)
            boundaries.add(end)

    ordered = sorted(boundaries)
    segments: list[Segment] = []

    for start, end in zip(ordered, ordered[1:]):
        if end <= start:
            continue
        active = tuple(
            sorted(
                (
                    note
                    for note in measure.notes
                    if note.start_tick < end
                    and note.start_tick + note.duration_ticks > start
                ),
                key=lambda note: (note.string, note.fret),
            )
        )
        has_onset = any(note.start_tick == start for note in measure.notes)
        signature = tuple((note.string, note.fret, note.pitch) for note in active)

        if (
            segments
            and not has_onset
            and segments[-1].end_tick == start
            and tuple(
                (note.string, note.fret, note.pitch)
                for note in segments[-1].notes
            )
            == signature
        ):
            previous = segments[-1]
            segments[-1] = Segment(
                start_tick=previous.start_tick,
                duration_ticks=previous.duration_ticks + (end - start),
                notes=previous.notes,
            )
        else:
            segments.append(
                Segment(
                    start_tick=start,
                    duration_ticks=end - start,
                    notes=active,
                )
            )

    return segments
