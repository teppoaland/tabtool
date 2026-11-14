"""PianoCapture pipeline: source -> probe analysis / window -> notes.

No stem separation by design: the tool assumes the source already is piano (or
that the user accepts the result). The intro/window choice is the only gate.
"""

from __future__ import annotations

from pathlib import Path

from piano import analyze, audio, config, pattern, store, transcribe


def _cleanup(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass


def analyze_source(
    source: str,
    probe_seconds: float | None = None,
    progress=None,
) -> dict:
    report = progress or (lambda *_args, **_kwargs: None)
    report("Ladataan ääntä…", 0.05)
    meta = audio.prepare_source(source)

    report("Leikataan alku analyysia varten…", 0.35)
    probe = min(
        float(meta["duration"]),
        float(probe_seconds or config.PROBE_SECONDS),
    )
    probe_path = audio.probe_window(audio.source_wav(meta), probe)

    try:
        report("Etsitään pianon alkua ja bändin sisääntuloa…", 0.6)
        suggestion = analyze.suggest_window(probe_path, probe)
    finally:
        _cleanup(probe_path)

    report("Valmis", 1.0)
    return {
        "source": meta,
        "probe_seconds": round(probe, 2),
        "suggestion": suggestion.as_dict(),
    }


def _validate_window(meta: dict, start: float, end: float) -> tuple[float, float]:
    duration = float(meta["duration"])
    begin = max(0.0, float(start))
    finish = min(float(end), duration)
    if finish <= begin:
        raise ValueError("Pätkän loppu on ennen alkua.")
    length = finish - begin
    if length < config.MIN_WINDOW_SECONDS:
        raise ValueError(
            f"Pätkä on liian lyhyt ({length:.1f} s); vähintään "
            f"{config.MIN_WINDOW_SECONDS:.0f} s."
        )
    if length > config.MAX_WINDOW_SECONDS:
        raise ValueError(
            f"Pätkä on liian pitkä ({length:.0f} s); enintään "
            f"{config.MAX_WINDOW_SECONDS:.0f} s."
        )
    return begin, finish


def process_window(
    source: str,
    start: float,
    end: float,
    progress=None,
) -> dict:
    report = progress or (lambda *_args, **_kwargs: None)
    report("Ladataan ääntä…", 0.05)
    meta = audio.prepare_source(source)
    begin, finish = _validate_window(meta, start, end)
    length = finish - begin

    piece_id = store.new_piece_id()
    directory = config.PIECES_DIR / piece_id
    directory.mkdir(parents=True, exist_ok=True)

    report("Leikataan pätkä…", 0.25)
    duration = audio.slice_wav(
        audio.source_wav(meta), directory / "audio.wav", begin, length
    )

    report("Transkriboidaan pianoa (tämä kestää hetken)…", 0.5)
    notes = transcribe.transcribe_window(
        directory / "audio.wav",
        midi_path=directory / "notes.mid",
        limit=duration,
    )

    report("Tallennetaan…", 0.9)
    # A short fixed figure usually repeats; learning one cycle is enough.
    cycle = pattern.find_cycle(directory / "audio.wav", duration)
    piece = {
        "id": piece_id,
        "created": store.created_stamp(),
        "source": {
            "type": meta.get("source_type"),
            "url": meta.get("url"),
            "title": meta.get("title"),
            "artist": meta.get("artist"),
            "channel": meta.get("channel"),
        },
        "window": {
            "start": round(begin, 3),
            "end": round(finish, 3),
            "duration": round(duration, 3),
        },
        "notes": notes,
        "note_count": len(notes),
        "cycle": cycle,
        "has_midi": True,
    }
    store.save_piece(piece)
    report("Valmis", 1.0)
    return {"piece_id": piece_id, "note_count": len(notes), "duration": round(duration, 3)}
