"""Tempo and beat estimation with librosa."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TempoInfo:
    bpm: float
    raw_bpm: float
    beat_times: tuple[float, ...]
    duration: float


def normalize_bpm(
    bpm: float, preferred_min: float = 70.0, preferred_max: float = 180.0
) -> float:
    """Fold half/double-time estimates into a readable range.

    Beat trackers often report 68 BPM for a 136 BPM rock song. For a tab
    draft it is usually more readable to notate the faster pulse.
    """
    if bpm <= 0:
        return bpm
    value = bpm
    while value < preferred_min:
        value *= 2.0
    while value > preferred_max:
        value /= 2.0
    return value


def detect_tempo(audio_path: str | Path, start_bpm: float = 120.0) -> TempoInfo:
    """Estimate BPM and beat positions.

    The first beat is not used to shift the tick grid in v1.0. The returned
    beat times are kept for diagnostics and future tempo-map support.
    """
    import librosa
    import numpy as np

    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(path)

    y, sr = librosa.load(str(path), sr=22050, mono=True)
    duration = float(librosa.get_duration(y=y, sr=sr))

    if y.size == 0:
        return TempoInfo(
            bpm=float(start_bpm),
            raw_bpm=float(start_bpm),
            beat_times=(),
            duration=duration,
        )

    tempo, beats = librosa.beat.beat_track(
        y=y,
        sr=sr,
        start_bpm=float(start_bpm),
        trim=True,
        units="frames",
    )
    bpm_values = np.atleast_1d(tempo)
    raw_bpm = float(bpm_values[0]) if bpm_values.size else float(start_bpm)
    if not np.isfinite(raw_bpm) or raw_bpm <= 0:
        raw_bpm = float(start_bpm)
    bpm = normalize_bpm(raw_bpm)

    beat_times = tuple(float(t) for t in librosa.frames_to_time(beats, sr=sr))
    return TempoInfo(
        bpm=bpm,
        raw_bpm=raw_bpm,
        beat_times=beat_times,
        duration=duration,
    )
