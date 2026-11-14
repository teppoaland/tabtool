"""Find the repeating piano loop inside a transcribed fragment.

A piano intro is often a short fixed figure played two or more times. Learning
one cycle is enough to play the whole intro, so the tool tries to find it and
the player can loop just that cycle.

The measurement is deliberately on the *audio* (onset strength autocorrelation),
not on the transcription: a note-level comparison drowns in Basic Pitch's
harmonics and octave duplicates, while the onsets of a repeated figure are
strong and stable. The result is a suggestion with a confidence - the user can
always set the cycle by hand.
"""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np

ANALYSIS_SR = 22050
HOP = 512
MIN_CYCLE = 1.5
MAX_CYCLE = 12.0
# A real loop peaks clearly above the noise floor of a metrical but through-
# composed intro. The Gathering's 2:08 intro peaks at 0.06; a genuine loop at
# 0.39. Keeping the floor high means "no cycle" is shown instead of a lie.
PEAK_FLOOR = 0.15


def _onset_autocorrelation(audio_path: str | Path) -> tuple[np.ndarray, float]:
    y, sr = librosa.load(str(audio_path), sr=ANALYSIS_SR, mono=True)
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
    onset = np.asarray(onset, dtype=float)
    if onset.size < 8:
        return np.zeros(1), 0.0
    onset = onset - float(onset.mean())
    autocorr = np.correlate(onset, onset, mode="full")[onset.size - 1 :]
    if autocorr[0] <= 0:
        return np.zeros(1), 0.0
    autocorr = autocorr / autocorr[0]
    fps = float(sr) / float(HOP)
    return autocorr, fps


def _refine(autocorr: np.ndarray, index: int) -> float:
    """Parabolic interpolation around a peak (in frames)."""
    if index <= 0 or index >= autocorr.size - 1:
        return float(index)
    left, middle, right = autocorr[index - 1], autocorr[index], autocorr[index + 1]
    denominator = left - 2 * middle + right
    if abs(denominator) < 1e-9:
        return float(index)
    return float(index) + 0.5 * (left - right) / denominator


def find_cycle(
    audio_path: str | Path,
    duration: float | None = None,
    min_cycle: float = MIN_CYCLE,
    max_cycle: float = MAX_CYCLE,
) -> dict | None:
    """Return ``{length, repeats, confidence}`` for the strongest loop, or None.

    A cycle must fit at least twice into the fragment; otherwise "repeating"
    is not something the fragment can show.
    """
    path = Path(audio_path)
    if not path.exists():
        return None
    autocorr, fps = _onset_autocorrelation(path)
    if fps <= 0:
        return None

    total = float(duration) if duration else (autocorr.size - 1) / fps
    upper = min(max_cycle, total / 2.0)
    if upper <= min_cycle:
        return None

    low_index = int(np.ceil(min_cycle * fps))
    high_index = int(np.floor(upper * fps))
    if high_index <= low_index + 1:
        return None

    window = autocorr[low_index : high_index + 1]
    peak_offset = int(np.argmax(window))
    peak_index = low_index + peak_offset
    peak = float(autocorr[peak_index])
    if peak < PEAK_FLOOR:
        return None

    length = _refine(autocorr, peak_index) / fps
    if length <= 0:
        return None
    repeats = total / length
    if repeats < 1.8:
        return None

    # A clean peak is a confident suggestion; a flat envelope is not.
    confidence = float(min(1.0, 0.35 + 1.5 * peak))
    return {
        "length": round(length, 2),
        "repeats": round(repeats, 2),
        "confidence": round(confidence, 2),
        "peak": round(peak, 3),
    }
