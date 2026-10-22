"""Prune transcription noise before quantizing (v1.73).

Basic Pitch reports many extra notes: octave/12th harmonics of the real note,
low-frequency bleed and transient bursts. The fretboard DP then spends its
budget trying to finger impossible clusters. This module only removes notes –
it never moves or changes a kept note – and is deliberately conservative.
"""

from __future__ import annotations

from app.pipeline.model import NoteEvent

# Notes whose onset is within this many seconds form one chord/cluster.
ONSET_WINDOW_S = 0.06
# A cluster is capped to this many simultaneous notes (kept loudest-first).
MAX_POLYPHONY = 4
# Intervals (in semitones) treated as harmonics of a lower note.
HARMONIC_INTERVALS = (12, 19)


def _prune_group(
    group: list[NoteEvent], harmonic_velocity_ratio: float
) -> list[NoteEvent]:
    """Keep the strongest notes; drop quiet harmonics of a kept note."""
    if len(group) <= 1:
        return list(group)
    ordered = sorted(group, key=lambda note: (-note.velocity, note.pitch))
    kept: list[NoteEvent] = []
    for candidate in ordered:
        is_harmonic = False
        for base in kept:
            interval = candidate.pitch - base.pitch
            if interval in HARMONIC_INTERVALS and candidate.velocity <= (
                base.velocity * harmonic_velocity_ratio
            ):
                is_harmonic = True
                break
        if not is_harmonic:
            kept.append(candidate)
    return kept


def prune_notes(
    notes: list[NoteEvent],
    max_polyphony: int = MAX_POLYPHONY,
    harmonic_velocity_ratio: float = 0.6,
) -> list[NoteEvent]:
    """Return a cleaned copy of ``notes``, grouped by onset then pruned."""
    ordered = sorted(notes, key=lambda note: (note.start, note.pitch))

    groups: list[list[NoteEvent]] = []
    for note in ordered:
        if groups and note.start - groups[-1][-1].start <= ONSET_WINDOW_S:
            groups[-1].append(note)
        else:
            groups.append([note])

    kept: list[NoteEvent] = []
    for group in groups:
        pruned = _prune_group(group, harmonic_velocity_ratio)
        if len(pruned) > max_polyphony:
            pruned = pruned[:max_polyphony]
        kept.extend(pruned)

    kept.sort(key=lambda note: (note.start, note.pitch))
    return kept
