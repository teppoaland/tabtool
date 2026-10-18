"""Basic Pitch audio-to-MIDI transcription."""

from __future__ import annotations

from pathlib import Path

from app.pipeline.model import NoteEvent


def transcribe_audio(
    audio_path: str | Path,
    onset_threshold: float = 0.5,
    frame_threshold: float = 0.3,
    min_note_length_ms: float = 58.0,
    min_frequency: float = 80.0,
    max_frequency: float = 1200.0,
    multiple_pitch_bends: bool = False,
    melodia_trick: bool = True,
) -> list[NoteEvent]:
    """Transcribe a guitar stem to note events.

    The heavy TensorFlow import happens here so the web app can boot without
    loading the model. Basic Pitch expects one instrument per audio file.
    """
    from basic_pitch import ICASSP_2022_MODEL_PATH
    from basic_pitch.inference import predict

    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(path)

    _, midi_data, _ = predict(
        path,
        ICASSP_2022_MODEL_PATH,
        onset_threshold=float(onset_threshold),
        frame_threshold=float(frame_threshold),
        minimum_note_length=float(min_note_length_ms),
        minimum_frequency=float(min_frequency),
        maximum_frequency=float(max_frequency),
        multiple_pitch_bends=bool(multiple_pitch_bends),
        melodia_trick=bool(melodia_trick),
    )

    notes: list[NoteEvent] = []
    for instrument in midi_data.instruments:
        for note in instrument.notes:
            if note.end <= note.start:
                continue
            notes.append(
                NoteEvent(
                    pitch=int(note.pitch),
                    start=float(note.start),
                    end=float(note.end),
                    velocity=int(note.velocity),
                )
            )

    notes.sort(key=lambda note: (note.start, note.pitch))
    return notes
