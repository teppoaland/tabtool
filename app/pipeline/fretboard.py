"""Assign detected pitches to guitar strings and frets."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from app.pipeline.model import GRID_TICKS, QuantizedNote, TabNote, Tuning

# Keep the search small enough for a local CPU-only machine.
MAX_STATES = 36
MAX_CANDIDATES_PER_CHORD = 160


@dataclass(frozen=True)
class _Candidate:
    strings: tuple[int, ...]
    frets: tuple[int, ...]
    mean_fret: float
    span: int
    open_count: int
    base_cost: float
    hand_fret: float = 0.0
    string_center: float = 0.0


@dataclass(frozen=True)
class FretboardProfile:
    """Fingering policy: weights for the DP cost function (v1.72).

    Each profile scores the same notes differently, producing a different
    playable layout (open-string campfire shapes, a compact mid-neck box, or
    minimal hand movement). All profiles are deterministic.
    """

    key: str
    label: str
    open_bonus: float = 0.2
    low_fret_penalty: float = 0.0
    high_fret_penalty: float = 0.05
    span_weight: float = 1.5
    box_center: int | None = None
    box_width: int = 2
    box_penalty_weight: float = 0.6
    shift_weight: float = 1.0
    string_jump_weight: float = 0.15
    skip_weight: float = 0.05


PROFILES: dict[str, FretboardProfile] = {
    "open": FretboardProfile(
        key="open",
        label="V1 · Avoimet kielet",
        open_bonus=0.6,
        low_fret_penalty=0.04,
        high_fret_penalty=0.12,
        span_weight=1.5,
        shift_weight=0.8,
        string_jump_weight=0.1,
    ),
    "box": FretboardProfile(
        key="box",
        label="V2 · Boksi",
        open_bonus=0.15,
        high_fret_penalty=0.05,
        span_weight=2.0,
        shift_weight=1.2,
        string_jump_weight=0.15,
        skip_weight=0.05,
    ),
    "smooth": FretboardProfile(
        key="smooth",
        label="V3 · Vähän liikettä",
        open_bonus=0.2,
        high_fret_penalty=0.05,
        span_weight=1.2,
        shift_weight=2.5,
        string_jump_weight=0.12,
    ),
}


def get_profile(value: str | FretboardProfile | None) -> FretboardProfile | None:
    if value is None or isinstance(value, FretboardProfile):
        return value
    key = str(value).strip().lower()
    if key not in PROFILES:
        raise ValueError(f"Unknown fretboard profile: {value!r}")
    return PROFILES[key]


@dataclass(frozen=True)
class _PathState:
    cost: float
    candidate_index: int
    previous_index: int


def candidates_for_pitch(
    pitch: int, tuning: Tuning, max_fret: int = 24
) -> list[tuple[int, int]]:
    """Return (string, fret) positions that produce the given MIDI pitch."""
    positions: list[tuple[int, int]] = []
    for number, open_pitch in tuning.ordered_strings():
        fret = pitch - open_pitch
        if 0 <= fret <= max_fret:
            positions.append((number, fret))
    return positions


def _legacy_candidate_cost(frets: Iterable[int]) -> tuple[float, int, int, float]:
    values = tuple(frets)
    span = max(values) - min(values)
    mean = sum(values) / len(values)
    open_count = sum(1 for fret in values if fret == 0)
    high_fret = max(0, max(values) - 12)
    cost = span * 1.5 + mean * 0.02 + high_fret * 0.05 - open_count * 0.2
    return cost, span, open_count, mean


def _profile_candidate_cost(
    frets: Iterable[int], profile: FretboardProfile
) -> tuple[float, int, int, float, float, float]:
    values = tuple(frets)
    span = max(values) - min(values)
    mean = sum(values) / len(values)
    open_count = sum(1 for fret in values if fret == 0)
    max_fret = max(values)
    hand_fret = min((fret for fret in values if fret > 0), default=0)
    high_fret = max(0, max_fret - 12)
    box_penalty = 0.0
    if profile.box_center is not None:
        box_penalty = max(0.0, abs(mean - profile.box_center) - profile.box_width)
    cost = (
        span * profile.span_weight
        + mean * (0.02 + profile.low_fret_penalty)
        + high_fret * profile.high_fret_penalty
        - open_count * profile.open_bonus
        + box_penalty * profile.box_penalty_weight
    )
    return cost, span, open_count, mean, hand_fret, max_fret


def _profile_transition(
    previous: _Candidate, current: _Candidate, profile: FretboardProfile
) -> float:
    """Penalise hand movement and string crossing between two chords."""
    shift = abs(current.hand_fret - previous.hand_fret)
    jump = abs(current.string_center - previous.string_center)
    skip = max(0.0, jump - 2.0)
    return (
        shift * profile.shift_weight
        + jump * profile.string_jump_weight
        + skip * profile.skip_weight
    )


def _enumerate_candidates(
    notes: list[QuantizedNote],
    tuning: Tuning,
    max_fret: int,
    max_span: int,
    limit: int = MAX_CANDIDATES_PER_CHORD,
    profile: FretboardProfile | None = None,
) -> list[_Candidate]:
    """Enumerate playable string/fret combinations for one chord."""
    if not notes:
        return []

    positions_per_note = [
        candidates_for_pitch(note.pitch, tuning, max_fret) for note in notes
    ]
    if any(not positions for positions in positions_per_note):
        return []

    # Assign the most constrained notes first to prune the search.
    order = sorted(
        range(len(notes)),
        key=lambda index: (len(positions_per_note[index]), -notes[index].pitch),
    )
    strings_for_note: dict[int, int] = {}
    frets_for_note: dict[int, int] = {}
    results: list[_Candidate] = []

    def recurse(depth: int, used_strings: set[int], current_frets: list[int]) -> None:
        if len(results) >= limit:
            return
        if depth == len(order):
            strings = tuple(strings_for_note[i] for i in range(len(notes)))
            frets = tuple(frets_for_note[i] for i in range(len(notes)))
            if profile is None:
                base_cost, span, open_count, mean = _legacy_candidate_cost(frets)
                if span <= max_span:
                    results.append(
                        _Candidate(
                            strings=strings,
                            frets=frets,
                            mean_fret=mean,
                            span=span,
                            open_count=open_count,
                            base_cost=base_cost,
                        )
                    )
            else:
                base_cost, span, open_count, mean, hand_fret, _max = (
                    _profile_candidate_cost(frets, profile)
                )
                if span <= max_span:
                    results.append(
                        _Candidate(
                            strings=strings,
                            frets=frets,
                            mean_fret=mean,
                            span=span,
                            open_count=open_count,
                            base_cost=base_cost,
                            hand_fret=hand_fret,
                            string_center=sum(strings) / len(strings),
                        )
                    )
            return

        note_index = order[depth]
        for string, fret in positions_per_note[note_index]:
            if string in used_strings:
                continue
            strings_for_note[note_index] = string
            frets_for_note[note_index] = fret
            current_frets.append(fret)
            recurse(depth + 1, used_strings | {string}, current_frets)
            current_frets.pop()
        strings_for_note.pop(note_index, None)
        frets_for_note.pop(note_index, None)

    recurse(0, set(), [])
    results.sort(key=lambda candidate: candidate.base_cost)
    return results[:limit]


def _prepare_group(
    notes: list[QuantizedNote],
    tuning: Tuning,
    max_fret: int,
    warnings: list[str],
) -> list[QuantizedNote]:
    """Drop duplicates and limit a chord to the number of available strings."""
    by_pitch: dict[int, QuantizedNote] = {}
    for note in notes:
        previous = by_pitch.get(note.pitch)
        if previous is None or note.duration_ticks > previous.duration_ticks:
            by_pitch[note.pitch] = note

    unique = sorted(by_pitch.values(), key=lambda note: note.pitch)
    if len(unique) > tuning.string_count:
        dropped = len(unique) - tuning.string_count
        warnings.append(
            f"Chord at tick {unique[0].start_tick} had {len(unique)} notes; "
            f"kept the lowest {tuning.string_count} and dropped {dropped}."
        )
        unique = unique[: tuning.string_count]

    playable = [
        note
        for note in unique
        if candidates_for_pitch(note.pitch, tuning, max_fret)
    ]
    dropped_unplayable = len(unique) - len(playable)
    if dropped_unplayable:
        warnings.append(
            f"Dropped {dropped_unplayable} note(s) outside "
            f"{tuning.name} range at tick {unique[0].start_tick}."
        )
    return playable


def _solve_path(
    groups: list[list[QuantizedNote]],
    candidates: list[list[_Candidate]],
    profile: FretboardProfile | None = None,
) -> list[_Candidate] | None:
    """Viterbi pass with back-pointers over the small candidate sets."""
    if not groups or not candidates:
        return None

    first = [
        _PathState(candidate.base_cost, index, -1)
        for index, candidate in enumerate(
            candidates[0][:MAX_CANDIDATES_PER_CHORD]
        )
    ]
    first.sort(key=lambda state: state.cost)
    layers: list[list[_PathState]] = [first[:MAX_STATES]]

    for group_index in range(1, len(groups)):
        current_candidates = candidates[group_index][:MAX_CANDIDATES_PER_CHORD]
        previous_layer = layers[-1]
        next_layer: list[_PathState] = []

        for candidate_index, candidate in enumerate(current_candidates):
            best_cost = float("inf")
            best_previous = -1
            for previous_index, previous_state in enumerate(previous_layer):
                previous_candidate = candidates[group_index - 1][
                    previous_state.candidate_index
                ]
                transition = (
                    abs(candidate.mean_fret - previous_candidate.mean_fret)
                    if profile is None
                    else _profile_transition(previous_candidate, candidate, profile)
                )
                cost = previous_state.cost + candidate.base_cost + transition
                if cost < best_cost:
                    best_cost = cost
                    best_previous = previous_index
            next_layer.append(
                _PathState(best_cost, candidate_index, best_previous)
            )

        next_layer.sort(key=lambda state: state.cost)
        layers.append(next_layer[:MAX_STATES])

    path: list[_Candidate] = []
    state_index = 0
    for layer_index in range(len(layers) - 1, -1, -1):
        state = layers[layer_index][state_index]
        path.append(candidates[layer_index][state.candidate_index])
        if state.previous_index < 0:
            break
        state_index = state.previous_index

    path.reverse()
    return path


def assign_fretboard(
    notes: list[QuantizedNote],
    tuning: Tuning,
    max_fret: int = 24,
    max_span: int = 5,
    profile: str | FretboardProfile | None = None,
) -> tuple[list[TabNote], list[str]]:
    """Assign every note to a string/fret using a small dynamic program.

    The cost prefers staying near the previous hand position, avoids wide
    stretches, and gives a small bonus to open strings. A ``profile`` switches
    to the richer cost function (v1.72); ``None`` keeps the legacy weights.
    """
    warnings: list[str] = []
    resolved = get_profile(profile)
    if max_span < 0:
        raise ValueError("max_span must be >= 0")
    if max_fret < 0:
        raise ValueError("max_fret must be >= 0")

    groups: dict[int, list[QuantizedNote]] = {}
    for note in notes:
        groups.setdefault(note.start_tick, []).append(note)

    prepared: list[list[QuantizedNote]] = []
    candidates: list[list[_Candidate]] = []

    for tick in sorted(groups):
        group = _prepare_group(groups[tick], tuning, max_fret, warnings)
        if not group:
            continue
        group_candidates = _enumerate_candidates(
            group, tuning, max_fret, max_span, MAX_CANDIDATES_PER_CHORD, resolved
        )
        if not group_candidates:
            warnings.append(
                f"No playable fingering at tick {tick}; "
                f"skipped {len(group)} note(s)."
            )
            continue
        prepared.append(group)
        candidates.append(group_candidates)

    if not prepared:
        return [], warnings

    path = _solve_path(prepared, candidates, resolved)
    if path is None:
        return [], warnings
    if len(path) != len(prepared):
        warnings.append("Fingering path was incomplete; some groups were skipped.")

    tab_notes: list[TabNote] = []
    for group, candidate in zip(prepared, path):
        for note, string, fret in zip(group, candidate.strings, candidate.frets):
            tab_notes.append(
                TabNote(
                    pitch=note.pitch,
                    string=string,
                    fret=fret,
                    start_tick=note.start_tick,
                    duration_ticks=note.duration_ticks,
                    velocity=note.velocity,
                    tie=note.tie,
                )
            )

    tab_notes, monophony_warnings = enforce_string_monophony(
        tab_notes, tuning, max_fret=max_fret
    )
    warnings.extend(monophony_warnings)
    return tab_notes, warnings


def enforce_string_monophony(
    notes: list[TabNote],
    tuning: Tuning,
    max_fret: int = 24,
    grid_ticks: int = GRID_TICKS,
) -> tuple[list[TabNote], list[str]]:
    """Ensure a string never carries two overlapping notes.

    A guitar string is monophonic. When a new note would overlap a sustained
    note on the same string, move it to a free string if possible; otherwise
    shorten the sustained note to the new onset.
    """
    ordered = sorted(notes, key=lambda note: (note.start_tick, note.string, note.pitch))
    active: dict[int, TabNote] = {}
    output: list[TabNote] = []
    warnings: list[str] = []

    for original in ordered:
        note = original
        for string in list(active):
            sounding = active[string]
            if sounding.start_tick + sounding.duration_ticks <= note.start_tick:
                del active[string]

        if note.string in active:
            if not note.tie:
                free_positions = [
                    (string, fret)
                    for string, fret in candidates_for_pitch(
                        note.pitch, tuning, max_fret
                    )
                    if string not in active
                ]
                if free_positions:
                    free_positions.sort(
                        key=lambda position: (
                            abs(position[0] - note.string),
                            position[1],
                        )
                    )
                    string, fret = free_positions[0]
                    note = replace(note, string=string, fret=fret)
                else:
                    previous = active[note.string]
                    new_duration = note.start_tick - previous.start_tick
                    if new_duration >= grid_ticks:
                        truncated = replace(
                            previous, duration_ticks=new_duration
                        )
                        for index, existing in enumerate(output):
                            if existing is previous:
                                output[index] = truncated
                                break
                        active[note.string] = truncated
                        warnings.append(
                            f"Shortened sustained note on string {note.string} "
                            f"at tick {previous.start_tick}."
                        )
                    else:
                        output = [item for item in output if item is not previous]
                        active.pop(note.string, None)
                        warnings.append(
                            f"Dropped overlapping note on string {note.string} "
                            f"at tick {previous.start_tick}."
                        )

        if note.string in active and active[note.string].start_tick == note.start_tick:
            warnings.append(
                f"Dropped duplicate string {note.string} at tick {note.start_tick}."
            )
            continue

        output.append(note)
        active[note.string] = note

    output.sort(key=lambda note: (note.start_tick, note.string))
    return output, warnings
