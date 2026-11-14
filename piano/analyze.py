"""Find the solo piano intro and the moment the band comes in.

Piano is not identified by a frequency band (its 27.5-4186 Hz range overlaps
almost everything). What separates a piano is its shape in time: a struck
attack that decays, a harmonic stack, sustained polyphony. This module uses
that shape only as a *suggestion generator*: the user always sees and can move
the window, so a wrong guess never becomes a wrong transcription.

The reliable cue for the end of the intro is not "piano stops" but "the band
enters": percussion energy, low-end energy and onset density jump together.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import librosa
import numpy as np
from scipy.ndimage import median_filter

from piano import config

HOP = 512
N_FFT = 2048
ANALYSIS_SR = 22050
SMOOTH_SIZE = 21  # ~0.5 s at 22.05 kHz / 512 hop
ROLL_FRAMES = 31  # ~0.7 s


@dataclass(frozen=True)
class Suggestion:
    """A candidate piano window. ``end`` never exceeds the analysed probe."""

    start: float
    end: float
    music_start: float
    band_entry: float | None
    confidence: float
    reason: str

    def as_dict(self) -> dict:
        return asdict(self)


def _smooth(values: np.ndarray, size: int = SMOOTH_SIZE) -> np.ndarray:
    return median_filter(
        np.asarray(values, dtype=float), size=size, mode="nearest"
    )


def _rolling(values: np.ndarray, size: int = ROLL_FRAMES) -> np.ndarray:
    kernel = np.ones(size, dtype=float) / float(size)
    return np.convolve(np.asarray(values, dtype=float), kernel, mode="same")


def _features(y: np.ndarray, sr: int) -> dict[str, np.ndarray]:
    magnitude = np.abs(librosa.stft(y, n_fft=N_FFT, hop_length=HOP))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=N_FFT)
    rms = librosa.feature.rms(S=magnitude)[0]
    flatness = librosa.feature.spectral_flatness(S=magnitude)[0]
    low_band = magnitude[(freqs >= 30.0) & (freqs <= 120.0)].sum(axis=0)
    total = magnitude.sum(axis=0) + 1e-9
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)

    # A piano note is harmonic and decays; water, cymbals and noise are mostly
    # transient/residual. HPSS therefore separates "instrument" from "ambience".
    harmonic, percussive = librosa.effects.hpss(y)
    rms_harmonic = librosa.feature.rms(y=harmonic, hop_length=HOP)[0]
    rms_percussive = librosa.feature.rms(y=percussive, hop_length=HOP)[0]

    length = min(
        rms.shape[0],
        flatness.shape[0],
        low_band.shape[0],
        onset.shape[0],
        rms_harmonic.shape[0],
        rms_percussive.shape[0],
    )
    return {
        "rms": rms[:length],
        "flatness": flatness[:length],
        "low_ratio": (low_band / total)[:length],
        "onset": onset[:length],
        "rms_harmonic": rms_harmonic[:length],
        "perc_ratio": (rms_percussive / (rms_harmonic + rms_percussive + 1e-9))[
            :length
        ],
    }


def _music_start(features: dict[str, np.ndarray], times: np.ndarray) -> float:
    harmonic = _smooth(features["rms_harmonic"])
    floor = float(np.percentile(harmonic, 10))
    ceiling = float(np.percentile(harmonic, 95))
    threshold = max(floor * 3.0, ceiling * 0.05)
    active = harmonic > threshold

    # Require ~0.4 s of sustained harmonic sound: one water splash is not piano.
    need = max(2, int(round(0.4 / (times[1] - times[0] if len(times) > 1 else 0.023))))
    run = 0
    for index, is_active in enumerate(active):
        run = run + 1 if is_active else 0
        if run >= need:
            first = index - run + 1
            return max(0.0, float(times[first]) - 0.20)
    return 0.0


def _band_entry(
    features: dict[str, np.ndarray],
    times: np.ndarray,
    music_start: float,
    duration: float,
) -> tuple[float | None, float]:
    """Return the first sustained "band" moment and how strong the jump was."""
    if duration - music_start < 4.0:
        return None, 0.0

    rms = _rolling(features["rms"])
    perc = _rolling(features["perc_ratio"])
    low = _rolling(features["low_ratio"])
    onset = _rolling(features["onset"])

    base_end = int(np.searchsorted(times, music_start + 2.0))
    base_start = int(np.searchsorted(times, music_start))
    if base_end <= base_start:
        return None, 0.0
    rms_base = float(np.median(rms[base_start:base_end])) + 1e-6
    perc_base = float(np.median(perc[base_start:base_end])) + 1e-4
    low_base = float(np.median(low[base_start:base_end])) + 1e-4
    onset_base = float(np.median(onset[base_start:base_end])) + 1e-4

    search_from = int(np.searchsorted(times, music_start + 2.0))
    need = max(4, int(round(0.5 / float(times[1] - times[0]))))
    run = 0
    for index in range(search_from, len(times)):
        # A new instrument section is audible as a sustained jump in the
        # percussive share *and* in loudness. The low band and onset density
        # are optional extra evidence: a pad or strings may enter without
        # drums, and in this song the low band actually drops at the entry.
        strong = (
            perc[index] > perc_base * 1.6 and rms[index] > rms_base * 1.7
        ) or (
            perc[index] > perc_base * 2.5
            and (low[index] > low_base * 1.8 or onset[index] > onset_base * 2.2)
        )
        run = run + 1 if strong else 0
        if run >= need:
            first = index - run + 1
            jump = min(
                1.0,
                max(
                    perc[index] / perc_base - 1.0,
                    rms[index] / rms_base - 1.0,
                    low[index] / low_base - 1.0,
                    onset[index] / onset_base - 1.0,
                )
                / 2.0,
            )
            return float(times[first]), jump
    return None, 0.0


def _format_seconds(value: float) -> str:
    total = max(0.0, float(value))
    minutes = int(total // 60)
    seconds = total - minutes * 60
    return f"{minutes}:{seconds:04.1f}"


def suggest_window(
    audio_path: str | Path, probe_seconds: float | None = None
) -> Suggestion:
    """Analyse the beginning of a source and suggest a piano-only window."""
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(path)

    # Only the beginning is analysed, even if the caller passes the full
    # source: the intro is the question, not the whole song.
    limit = float(probe_seconds or config.PROBE_SECONDS)
    y, sr = librosa.load(
        str(path), sr=ANALYSIS_SR, mono=True, duration=limit
    )
    duration = float(len(y)) / float(sr) if sr else 0.0
    probe = duration

    if duration < 1.5:
        return Suggestion(
            start=0.0,
            end=max(config.MIN_WINDOW_SECONDS, duration),
            music_start=0.0,
            band_entry=None,
            confidence=0.0,
            reason="Ääni on liian lyhyt analysoitavaksi.",
        )

    features = _features(y, sr)
    times = librosa.frames_to_time(
        np.arange(features["rms"].shape[0]), sr=sr, hop_length=HOP
    )

    music_start = _music_start(features, times)
    band_entry, jump = _band_entry(features, times, music_start, duration)

    start = max(0.0, music_start)
    if band_entry is not None:
        end = band_entry
    else:
        end = min(duration, start + 30.0)
    # Keep the window usable even when the cues disagree.
    end = min(end, start + config.MAX_WINDOW_SECONDS)
    if end - start < config.MIN_WINDOW_SECONDS:
        end = min(duration, start + config.MIN_WINDOW_SECONDS)

    confidence = 0.35
    if music_start > 0.05:
        confidence += 0.15
    if band_entry is not None:
        confidence += 0.25 + 0.25 * jump
    confidence = round(min(1.0, max(0.0, confidence)), 2)

    if band_entry is not None:
        reason = (
            f"Piano alkaa noin {_format_seconds(music_start)}. "
            f"Rummut/basso tulevat mukaan noin {_format_seconds(band_entry)}, "
            "joten pätkä rajataan siihen."
        )
    else:
        confidence = min(confidence, 0.35)
        reason = (
            f"Piano alkaa noin {_format_seconds(music_start)}. "
            "Bändin sisääntuloa ei tunnistettu tässä otoksessa; "
            "tarkista loppu itse."
        )

    return Suggestion(
        start=round(start, 2),
        end=round(end, 2),
        music_start=round(music_start, 2),
        band_entry=None if band_entry is None else round(band_entry, 2),
        confidence=confidence,
        reason=reason,
    )
