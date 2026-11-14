"""Piano transcription with Basic Pitch, tuned for the whole 88-key range.

TabTool's transcriber is guitar-shaped: it starts at 80 Hz, stops at 1200 Hz and
enforces a single melody. For a piano that would drop A0-E2 and C6-C8 and flatten
every chord, so this module passes piano parameters instead. The model itself is
the same; only the contract differs.
"""

from __future__ import annotations

from pathlib import Path

# A0 = 27.5 Hz, C8 = 4186 Hz: the physical range of an 88-key piano.
PIANO_MIN_FREQUENCY = 27.5
PIANO_MAX_FREQUENCY = 4186.0
PIANO_LOWEST_MIDI = 21
PIANO_HIGHEST_MIDI = 108


def parameters() -> dict[str, object]:
    """Basic Pitch settings for solo piano.

    ``melodia_trick`` is off on purpose: it forces a single melody line, which
    destroys chords, octaves and the left hand.
    """
    return {
        "onset_threshold": 0.5,
        "frame_threshold": 0.3,
        "minimum_note_length": 80.0,
        "minimum_frequency": PIANO_MIN_FREQUENCY,
        "maximum_frequency": PIANO_MAX_FREQUENCY,
        "multiple_pitch_bends": False,
        "melodia_trick": False,
    }


def _predict(audio_path: Path, params: dict[str, object]):
    """Run the model; imported here so the web app boots without TensorFlow."""
    from basic_pitch import ICASSP_2022_MODEL_PATH
    from basic_pitch.inference import predict

    _, midi_data, _ = predict(
        audio_path,
        ICASSP_2022_MODEL_PATH,
        onset_threshold=params["onset_threshold"],
        frame_threshold=params["frame_threshold"],
        minimum_note_length=params["minimum_note_length"],
        minimum_frequency=params["minimum_frequency"],
        maximum_frequency=params["maximum_frequency"],
        multiple_pitch_bends=params["multiple_pitch_bends"],
        melodia_trick=params["melodia_trick"],
    )
    return midi_data


def notes_from_midi(midi_data, limit: float | None = None) -> list[dict]:
    """Flatten a pretty_midi object into JSON-friendly piano notes."""
    notes: list[dict] = []
    for instrument in midi_data.instruments:
        for note in instrument.notes:
            pitch = int(note.pitch)
            if not PIANO_LOWEST_MIDI <= pitch <= PIANO_HIGHEST_MIDI:
                continue
            start = max(0.0, float(note.start))
            end = float(note.end)
            if limit is not None:
                end = min(end, float(limit))
            if end - start <= 0.02:
                continue
            notes.append(
                {
                    "pitch": pitch,
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "velocity": int(note.velocity),
                }
            )
    notes.sort(key=lambda item: (item["start"], item["pitch"]))
    return notes


def transcribe_window(
    audio_path: str | Path,
    midi_path: str | Path | None = None,
    limit: float | None = None,
) -> list[dict]:
    """Transcribe one audio window and optionally write a MIDI reference."""
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(path)
    midi_data = _predict(path, parameters())
    if midi_path is not None:
        target = Path(midi_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        midi_data.write(str(target))
    return notes_from_midi(midi_data, limit=limit)
