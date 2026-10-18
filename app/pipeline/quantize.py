"""Quantize detected notes to a musical grid and split them across measures."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil

from app.pipeline.model import (
    DEFAULT_GRID_DIVISION,
    TICKS_PER_QUARTER,
    NoteEvent,
    QuantizedNote,
    measure_length_ticks,
    parse_time_signature,
)


@dataclass
class QuantizeResult:
    notes: list[QuantizedNote]
    measure_count: int
    measure_length_ticks: int
    bpm: float
    grid_ticks: int
    warnings: list[str] = field(default_factory=list)


def merge_note_events(notes: list[NoteEvent], tolerance: float = 0.03) -> list[NoteEvent]:
    """Merge duplicate / overlapping detections of the same pitch."""
    ordered = sorted(notes, key=lambda note: (note.pitch, note.start, note.end))
    merged: list[NoteEvent] = []
    for note in ordered:
        if note.end <= note.start:
            continue
        if merged:
            previous = merged[-1]
            if (
                previous.pitch == note.pitch
                and note.start <= previous.end + tolerance
                and note.end > previous.end
            ):
                merged[-1] = NoteEvent(
                    pitch=previous.pitch,
                    start=previous.start,
                    end=note.end,
                    velocity=max(previous.velocity, note.velocity),
                )
                continue
        merged.append(note)
    return merged


def _snap(value: float, step: int) -> int:
    if step <= 0:
        raise ValueError("step must be positive")
    return int(round(value / step)) * step


def quantize_notes(
    notes: list[NoteEvent],
    bpm: float,
    time_signature: str | tuple[int, int] = (4, 4),
    grid_division: int = DEFAULT_GRID_DIVISION,
    total_duration_seconds: float | None = None,
    max_measures: int = 2000,
) -> QuantizeResult:
    """Snap notes to a grid and split notes that cross measure boundaries."""
    if bpm <= 0:
        raise ValueError("bpm must be positive")
    if grid_division not in {4, 8, 16, 32, 64}:
        raise ValueError("grid_division must be one of 4, 8, 16, 32, 64")

    numerator, denominator = parse_time_signature(time_signature)
    measure_len = measure_length_ticks(numerator, denominator)
    grid_ticks = TICKS_PER_QUARTER * 4 // grid_division
    tick_seconds = (60.0 / bpm) / TICKS_PER_QUARTER

    warnings: list[str] = []
    merged = merge_note_events(notes)
    if not merged:
        warnings.append("No notes detected.")

    quantized: list[QuantizedNote] = []
    max_end_tick = 0
    max_allowed_tick = max_measures * measure_len

    for note in merged:
        if not 0 <= note.pitch <= 127:
            warnings.append(f"Dropped note with invalid MIDI pitch {note.pitch}.")
            continue

        start_tick = max(0, _snap(note.start / tick_seconds, grid_ticks))
        end_tick = _snap(note.end / tick_seconds, grid_ticks)
        if end_tick <= start_tick:
            end_tick = start_tick + grid_ticks
        if start_tick >= max_allowed_tick:
            warnings.append(
                f"Dropped note at tick {start_tick} (beyond {max_measures} measures)."
            )
            continue

        duration = min(end_tick - start_tick, max_allowed_tick - start_tick)
        if duration <= 0:
            continue

        first_measure = start_tick // measure_len
        last_measure = (start_tick + duration - 1) // measure_len
        for measure_index in range(first_measure, last_measure + 1):
            measure_start = measure_index * measure_len
            measure_end = measure_start + measure_len
            segment_start = max(start_tick, measure_start)
            segment_end = min(start_tick + duration, measure_end)
            if segment_end <= segment_start:
                continue
            quantized.append(
                QuantizedNote(
                    pitch=note.pitch,
                    start_tick=segment_start,
                    duration_ticks=segment_end - segment_start,
                    velocity=note.velocity,
                    tie=segment_start > start_tick,
                )
            )
            max_end_tick = max(max_end_tick, segment_end)

    note_measures = ceil(max_end_tick / measure_len) if max_end_tick else 0
    duration_measures = 0
    if total_duration_seconds is not None and total_duration_seconds > 0:
        duration_ticks = _snap(total_duration_seconds / tick_seconds, grid_ticks)
        duration_measures = ceil(duration_ticks / measure_len)
    measure_count = max(1, min(max_measures, max(note_measures, duration_measures)))

    quantized.sort(key=lambda note: (note.start_tick, note.pitch))
    return QuantizeResult(
        notes=quantized,
        measure_count=measure_count,
        measure_length_ticks=measure_len,
        bpm=float(bpm),
        grid_ticks=grid_ticks,
        warnings=warnings,
    )
