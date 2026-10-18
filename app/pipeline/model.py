"""Shared data model for the AI TabTool pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field

TICKS_PER_QUARTER = 960
DEFAULT_GRID_DIVISION = 16  # 1/16 notes
GRID_TICKS = TICKS_PER_QUARTER * 4 // DEFAULT_GRID_DIVISION  # 240


@dataclass(frozen=True)
class NoteEvent:
    """A note detected from audio, in seconds."""

    pitch: int
    start: float
    end: float
    velocity: int = 95


@dataclass(frozen=True)
class Tuning:
    """Guitar tuning. Strings are (string number, open MIDI pitch)."""

    key: str
    name: str
    strings: tuple[tuple[int, int], ...]

    @property
    def string_count(self) -> int:
        return len(self.strings)

    @property
    def lowest_pitch(self) -> int:
        return min(pitch for _, pitch in self.strings)

    @property
    def highest_pitch(self) -> int:
        return max(pitch for _, pitch in self.strings)

    def open_pitch(self, string: int) -> int:
        for number, pitch in self.strings:
            if number == string:
                return pitch
        raise KeyError(f"Unknown string {string}")

    def ordered_strings(self) -> tuple[tuple[int, int], ...]:
        return tuple(sorted(self.strings, key=lambda item: item[0]))


STANDARD_TUNING = Tuning(
    "standard",
    "Standard E",
    ((1, 64), (2, 59), (3, 55), (4, 50), (5, 45), (6, 40)),
)
DROP_D_TUNING = Tuning(
    "drop_d",
    "Drop D",
    ((1, 64), (2, 59), (3, 55), (4, 50), (5, 45), (6, 38)),
)
EB_STANDARD_TUNING = Tuning(
    "eb_standard",
    "Eb Standard",
    ((1, 63), (2, 58), (3, 54), (4, 49), (5, 44), (6, 39)),
)
D_STANDARD_TUNING = Tuning(
    "d_standard",
    "D Standard",
    ((1, 62), (2, 57), (3, 53), (4, 48), (5, 43), (6, 38)),
)
OPEN_G_TUNING = Tuning(
    "open_g",
    "Open G",
    ((1, 62), (2, 59), (3, 55), (4, 50), (5, 43), (6, 38)),
)
BASS_4_TUNING = Tuning(
    "bass_4",
    "Bass 4-string",
    ((1, 43), (2, 38), (3, 33), (4, 28)),
)

TUNINGS: dict[str, Tuning] = {
    tuning.key: tuning
    for tuning in (
        STANDARD_TUNING,
        DROP_D_TUNING,
        EB_STANDARD_TUNING,
        D_STANDARD_TUNING,
        OPEN_G_TUNING,
        BASS_4_TUNING,
    )
}


def get_tuning(value: str | Tuning) -> Tuning:
    if isinstance(value, Tuning):
        return value
    key = value.strip().lower().replace("-", "_").replace(" ", "_")
    if key in TUNINGS:
        return TUNINGS[key]
    for tuning in TUNINGS.values():
        if tuning.name.lower() == value.strip().lower():
            return tuning
    raise ValueError(f"Unknown tuning: {value!r}. Known: {', '.join(TUNINGS)}")


@dataclass(frozen=True)
class QuantizedNote:
    """A note snapped to the tick grid. Ticks use 960 per quarter note."""

    pitch: int
    start_tick: int
    duration_ticks: int
    velocity: int = 95
    tie: bool = False  # continuation from the previous measure


@dataclass(frozen=True)
class TabNote:
    pitch: int
    string: int
    fret: int
    start_tick: int
    duration_ticks: int
    velocity: int = 95
    tie: bool = False


@dataclass
class TabMeasure:
    number: int
    start_tick: int
    length_ticks: int
    notes: list[TabNote] = field(default_factory=list)

    @property
    def end_tick(self) -> int:
        return self.start_tick + self.length_ticks


@dataclass
class TabDocument:
    title: str
    artist: str
    bpm: float
    time_signature: tuple[int, int]
    tuning: Tuning
    measures: list[TabMeasure]
    max_fret: int = 24
    grid_division: int = DEFAULT_GRID_DIVISION
    source_audio: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def note_count(self) -> int:
        return sum(len(measure.notes) for measure in self.measures)

    @property
    def total_ticks(self) -> int:
        if not self.measures:
            return 0
        return self.measures[-1].end_tick


def measure_length_ticks(numerator: int, denominator: int) -> int:
    """Return the length of one measure in ticks."""
    return int(round(numerator * (4.0 / denominator) * TICKS_PER_QUARTER))


def parse_time_signature(value: str | tuple[int, int]) -> tuple[int, int]:
    if isinstance(value, tuple):
        numerator, denominator = value
    else:
        raw = value.strip()
        if "/" not in raw:
            raise ValueError(f"Time signature must look like 4/4, got {value!r}")
        numerator_text, denominator_text = raw.split("/", 1)
        numerator = int(numerator_text)
        denominator = int(denominator_text)
    if numerator <= 0 or denominator <= 0:
        raise ValueError("Time signature values must be positive")
    return numerator, denominator


def beats_from_seconds(seconds: float, bpm: float) -> float:
    return seconds * bpm / 60.0


def seconds_from_ticks(ticks: int, bpm: float) -> float:
    return (ticks / TICKS_PER_QUARTER) * (60.0 / bpm)
