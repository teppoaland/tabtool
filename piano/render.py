"""Render the transcribed notes as a piano-like WAV ("guide audio").

The point is verification: a beginner who cannot play the figure yet can listen
to exactly the notes the guide shows and hear whether they match the record.
This is a plain additive synth (harmonics + decay), no samples and no model.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

SAMPLE_RATE = 44100


def render_guide(
    notes: list[dict],
    duration: float,
    target: str | Path,
    sample_rate: int = SAMPLE_RATE,
) -> Path:
    """Write ``notes`` as one WAV file of ``duration`` seconds."""
    total = max(0.1, float(duration or 0.0))
    samples = int(total * sample_rate) + 1
    buffer = np.zeros(samples, dtype=np.float32)

    for note in notes:
        try:
            pitch = int(note.get("pitch", 0))
            start = float(note.get("start", 0.0))
            end = float(note.get("end", start + 0.1))
            velocity = float(note.get("velocity", 90))
        except (TypeError, ValueError):
            continue
        first = max(0, int(start * sample_rate))
        last = min(samples, int(end * sample_rate))
        if last - first < 2:
            continue
        time = np.arange(last - first, dtype=np.float32) / sample_rate
        frequency = 440.0 * 2.0 ** ((pitch - 69) / 12.0)
        # Harmonic stack: upper partials fade faster, like a struck string.
        wave = (
            np.sin(2.0 * np.pi * frequency * time)
            + 0.45 * np.sin(4.0 * np.pi * frequency * time)
            + 0.18 * np.sin(6.0 * np.pi * frequency * time)
            + 0.08 * np.sin(8.0 * np.pi * frequency * time)
        )
        envelope = np.exp(-time * 0.9)
        attack = min(len(time), int(0.006 * sample_rate))
        if attack > 1:
            envelope[:attack] *= np.linspace(0.0, 1.0, attack, dtype=np.float32)
        release = min(len(time), int(0.06 * sample_rate))
        if release > 1:
            envelope[-release:] *= np.linspace(
                1.0, 0.0, release, dtype=np.float32
            )
        gain = min(1.0, max(0.15, velocity / 127.0)) * 0.06
        buffer[first:last] += (wave * envelope * gain).astype(np.float32)

    peak = float(np.max(np.abs(buffer))) if buffer.size else 0.0
    if peak > 0:
        buffer = np.tanh(buffer / peak * 1.2) * 0.85

    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), buffer, sample_rate)
    return path
