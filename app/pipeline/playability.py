"""Score a fretboard assignment by how natural it is to play (v1.72).

The score is a deterministic 0-10 number: a higher number means fewer hand
shifts, smaller stretches, fewer string skips and fewer lost notes. It is used
to pick the default variant and is shown next to each variant in the viewer.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.pipeline.model import TabNote


@dataclass(frozen=True)
class Playability:
    score: float
    shifts_per_bar: float
    max_shift: int
    avg_fret: float
    max_fret: int
    max_span: int
    open_ratio: float
    avg_string_jump: float
    skipped_strings: int
    notes_lost: int
    sustain_conflicts: int


def _groups(notes: list[TabNote]) -> list[list[TabNote]]:
    by_tick: dict[int, list[TabNote]] = {}
    for note in notes:
        by_tick.setdefault(note.start_tick, []).append(note)
    return [by_tick[tick] for tick in sorted(by_tick)]


def _hand_fret(group: list[TabNote]) -> int:
    fretted = [note.fret for note in group if note.fret > 0]
    return min(fretted) if fretted else 0


def score_fretboard(
    notes: list[TabNote],
    measure_count: int = 1,
    warnings: list[str] | None = None,
) -> Playability:
    """Return the playability of one fretboard layout."""
    groups = _groups(notes)
    total_notes = len(notes)

    shifts = 0
    max_shift = 0
    prev_hand: int | None = None
    for group in groups:
        hand = _hand_fret(group)
        if prev_hand is not None:
            delta = abs(hand - prev_hand)
            shifts += delta
            max_shift = max(max_shift, delta)
        prev_hand = hand

    spans = [max(g, key=lambda n: n.fret).fret - min(g, key=lambda n: n.fret).fret for g in groups]
    max_span = max(spans) if spans else 0

    fret_values = [note.fret for note in notes]
    avg_fret = sum(fret_values) / total_notes if total_notes else 0.0
    max_fret = max(fret_values) if fret_values else 0
    open_ratio = sum(1 for fret in fret_values if fret == 0) / total_notes if total_notes else 0.0
    above_12 = sum(1 for fret in fret_values if fret > 12) / total_notes if total_notes else 0.0

    # String jumps only between consecutive single-note groups (arpeggios).
    singles = [group[0] for group in groups if len(group) == 1]
    jumps = [
        abs(singles[index + 1].string - singles[index].string)
        for index in range(len(singles) - 1)
    ]
    avg_string_jump = sum(jumps) / len(jumps) if jumps else 0.0
    skipped_strings = sum(1 for jump in jumps if jump > 2)

    issue_text = "\n".join(warnings or []).lower()
    notes_lost = (
        issue_text.count("dropped")
        + issue_text.count("shortened")
        + issue_text.count("skipped")
    )
    sustain_conflicts = issue_text.count("shortened") + issue_text.count(
        "overlapping"
    )

    transitions = len(groups) - 1
    score = 10.0
    score -= 1.8 * min(shifts / max(1, measure_count), 4.0)
    score -= 1.2 * max(0.0, max_span - 4)
    score -= 0.8 * min(1.0, above_12)
    score -= 0.6 * min(1.0, skipped_strings / max(1, transitions))
    score -= 2.0 * min(1.0, notes_lost / max(1, total_notes))
    score += 0.5 * min(open_ratio, 0.5)
    score = round(max(0.0, min(10.0, score)), 1)

    return Playability(
        score=score,
        shifts_per_bar=round(shifts / max(1, measure_count), 3),
        max_shift=max_shift,
        avg_fret=round(avg_fret, 2),
        max_fret=max_fret,
        max_span=max_span,
        open_ratio=round(open_ratio, 3),
        avg_string_jump=round(avg_string_jump, 3),
        skipped_strings=skipped_strings,
        notes_lost=notes_lost,
        sustain_conflicts=sustain_conflicts,
    )
