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


def filter_notes(notes: list[dict], hand: str, split: int = 60) -> list[dict]:
    """Keep one hand of the transcription (``right`` = pitch >= split)."""
    if hand not in ("left", "right"):
        return list(notes)
    boundary = int(split)
    if hand == "right":
        return [n for n in notes if int(n.get("pitch", 0)) >= boundary]
    return [n for n in notes if int(n.get("pitch", 0)) < boundary]


def render_midi(notes: list[dict], target: str | Path) -> Path:
    """Write the (filtered) notes as a standard MIDI file."""
    import pretty_midi

    midi = pretty_midi.PrettyMIDI()
    instrument = pretty_midi.Instrument(program=0, name="PianoCapture")
    for note in notes:
        end = float(note.get("end", 0.0))
        start = float(note.get("start", 0.0))
        if end <= start:
            continue
        instrument.notes.append(
            pretty_midi.Note(
                velocity=max(1, min(127, int(note.get("velocity", 90)))),
                pitch=int(note.get("pitch", 60)),
                start=start,
                end=end,
            )
        )
    midi.instruments.append(instrument)
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.write(str(path))
    return path


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
