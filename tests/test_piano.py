"""Tests for PianoCapture: the intro suggestion, the piano contract, the API.

The heavy model is never called here: the tests use synthetic audio and a
monkeypatched transcriber, so the suite stays fast and offline.
"""

from __future__ import annotations

import math
import shutil
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from piano import analyze, config, pattern, pipeline, store, transcribe
from piano.main import app

SR = 22050
CLIENT = TestClient(app)


def _write_synthetic(path, *, ambience=3.0, piano=6.0, band=5.0) -> None:
    """Ambience -> solo piano -> band (kick + snare) in one WAV."""
    rng = np.random.default_rng(7)
    total = ambience + piano + band
    samples = int(total * SR)
    audio = np.zeros(samples, dtype=np.float32)
    t = np.arange(samples) / SR

    # 1) water-like ambience: broadband noise, no harmonic stack
    ambience_mask = t < ambience
    audio[ambience_mask] += (
        rng.standard_normal(int(ambience_mask.sum())).astype(np.float32) * 0.012
    )

    # 2) solo piano: struck harmonics that decay, one note per second
    piano_mask = (t >= ambience) & (t < ambience + piano)
    piano_time = t[piano_mask] - ambience
    note_len = 1.6
    phase = piano_time % 1.0
    decay = np.exp(-phase / 0.45).astype(np.float32)
    tone = (
        np.sin(2 * math.pi * 220 * piano_time)
        + 0.5 * np.sin(2 * math.pi * 440 * piano_time)
        + 0.25 * np.sin(2 * math.pi * 660 * piano_time)
    ).astype(np.float32)
    struck = np.where(phase < note_len, decay, 0.0).astype(np.float32)
    audio[piano_mask] += tone * struck * 0.14

    # 3) band: the piano continues, kick and snare enter
    band_mask = t >= ambience + piano
    band_time = t[band_mask] - (ambience + piano)
    global_time = t[band_mask]
    tone_band = (
        np.sin(2 * math.pi * 220 * global_time)
        + 0.5 * np.sin(2 * math.pi * 440 * global_time)
        + 0.25 * np.sin(2 * math.pi * 660 * global_time)
    ).astype(np.float32) * 0.10
    kick_phase = band_time % 0.5
    kick = (
        np.sin(2 * math.pi * 60 * band_time) * np.exp(-kick_phase / 0.09)
    ).astype(np.float32)
    snare = rng.standard_normal(int(band_mask.sum())).astype(np.float32)
    snare *= (np.exp(-((band_time + 0.25) % 0.5) / 0.06)).astype(np.float32) * 0.12
    audio[band_mask] += tone_band + kick * 0.35 + snare

    peak = float(np.max(np.abs(audio))) or 1.0
    audio = (audio / peak * 0.85).astype(np.float32)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), audio, SR)
    assert path.exists()


def test_piano_contract_is_the_full_88_key_range() -> None:
    """v0.1: TabTool's guitar limits (80-1200 Hz, one melody) must not leak in."""
    params = transcribe.parameters()
    assert params["minimum_frequency"] == pytest.approx(27.5)
    assert params["maximum_frequency"] == pytest.approx(4186.0)
    assert params["melodia_trick"] is False
    assert params["multiple_pitch_bends"] is False
    assert transcribe.PIANO_LOWEST_MIDI == 21  # A0
    assert transcribe.PIANO_HIGHEST_MIDI == 108  # C8


def test_notes_from_midi_are_json_safe_and_clipped() -> None:
    midi = SimpleNamespace(
        instruments=[
            SimpleNamespace(
                notes=[
                    SimpleNamespace(pitch=60, start=0.0, end=1.0, velocity=90),
                    SimpleNamespace(pitch=20, start=0.2, end=0.4, velocity=90),  # below A0
                    SimpleNamespace(pitch=109, start=0.2, end=0.4, velocity=90),  # above C8
                    SimpleNamespace(pitch=64, start=1.5, end=9.0, velocity=80),
                    SimpleNamespace(pitch=65, start=2.0, end=2.01, velocity=80),
                ]
            )
        ]
    )
    notes = transcribe.notes_from_midi(midi, limit=3.0)
    assert [(n["pitch"], n["start"], n["end"]) for n in notes] == [
        (60, 0.0, 1.0),
        (64, 1.5, 3.0),
    ]
    assert all(isinstance(n["velocity"], int) for n in notes)


def test_suggestion_finds_the_solo_piano_and_the_band_entry(tmp_path) -> None:
    """Ambience 0-3 s, piano alone 3-9 s, band from 9 s on."""
    source = tmp_path / "synthetic.wav"
    _write_synthetic(source, ambience=3.0, piano=6.0, band=5.0)

    suggestion = analyze.suggest_window(source)
    assert suggestion.music_start == pytest.approx(3.0, abs=1.2)
    assert suggestion.band_entry is not None
    assert suggestion.band_entry == pytest.approx(9.0, abs=1.8)
    assert suggestion.end == pytest.approx(suggestion.band_entry, abs=0.01)
    assert 0.0 <= suggestion.confidence <= 1.0
    assert "Piano alkaa" in suggestion.reason

    data = suggestion.as_dict()
    assert set(data) == {
        "start",
        "end",
        "music_start",
        "band_entry",
        "confidence",
        "reason",
    }


def test_window_validation_rejects_empty_and_huge_windows() -> None:
    meta = {"duration": 1000.0}
    with pytest.raises(ValueError):
        pipeline._validate_window(meta, 10.0, 10.0)
    with pytest.raises(ValueError):
        pipeline._validate_window(meta, 10.0, 12.0)
    with pytest.raises(ValueError):
        pipeline._validate_window(meta, 0.0, config.MAX_WINDOW_SECONDS + 1.0)
    begin, finish = pipeline._validate_window(meta, -5.0, 200.0)
    assert begin == 0.0
    assert finish == 200.0


@pytest.fixture()
def piano_data(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "SOURCES_DIR", tmp_path / "sources")
    monkeypatch.setattr(config, "PIECES_DIR", tmp_path / "pieces")
    monkeypatch.setattr(config, "TMP_DIR", tmp_path / "tmp")
    monkeypatch.setattr(store, "config", config)
    config.ensure_data_dirs()
    return tmp_path


def _wait_job(job_id: str, timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = CLIENT.get(f"/api/piano/jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()
        if job["status"] in {"ready", "failed"}:
            return job
        time.sleep(0.1)
    raise AssertionError("job did not finish")


def _write_accented_figure(path, *, period=2.0, repeats=3) -> None:
    """A 2 s accented figure repeated three times: the loop is exactly 2 s."""
    sr = 22050
    total = period * repeats
    timeline = np.arange(int(total * sr)) / sr
    audio = np.zeros_like(timeline, dtype=np.float32)
    offsets = [0.0, 0.5, 1.0, 1.5]
    pitches = [69, 72, 76, 74]
    accents = {0.0: 0.5, 0.5: 0.18, 1.0: 0.22, 1.5: 0.15}
    for repetition in range(repeats):
        for offset, pitch in zip(offsets, pitches):
            start = repetition * period + offset
            index = int(start * sr)
            length = int(0.4 * sr)
            local = np.arange(length) / sr
            frequency = 440 * 2 ** ((pitch - 69) / 12)
            tone = np.sin(2 * math.pi * frequency * local) * np.exp(-local / 0.25)
            audio[index : index + length] += (
                tone * accents[offset] * (1.0 if repetition == 0 else 0.9)
            ).astype(np.float32)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), audio / float(np.max(np.abs(audio))) * 0.8, sr)


def test_find_cycle_detects_the_repeating_figure(tmp_path) -> None:
    """v0.2: KIERTO needs the loop length, and a wrong guess must be visible."""
    source = tmp_path / "figure.wav"
    _write_accented_figure(source, period=2.0, repeats=3)
    cycle = pattern.find_cycle(source, duration=6.0)
    assert cycle is not None
    assert cycle["length"] == pytest.approx(2.0, abs=0.15)
    assert cycle["repeats"] == pytest.approx(3.0, abs=0.3)
    assert 0.0 < cycle["confidence"] <= 1.0

    # A cycle that cannot fit twice is not a loop.
    single = tmp_path / "single.wav"
    _write_accented_figure(single, period=2.0, repeats=1)
    assert pattern.find_cycle(single, duration=2.0) is None


def test_find_cycle_returns_none_for_a_flat_signal(tmp_path) -> None:
    source = tmp_path / "silence.wav"
    sf.write(str(source), np.zeros(22050 * 4, dtype=np.float32), 22050)
    assert pattern.find_cycle(source, duration=4.0) is None


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")
def test_api_processes_a_local_file_and_serves_the_piece(
    piano_data, monkeypatch, tmp_path
) -> None:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg required")
    source = tmp_path / "input.wav"
    _write_synthetic(source, ambience=1.0, piano=4.0, band=3.0)

    calls: dict[str, object] = {}

    def fake_transcribe(audio_path, midi_path=None, limit=None):
        calls["audio"] = str(audio_path)
        calls["midi"] = str(midi_path) if midi_path else None
        calls["limit"] = limit
        return [
            {"pitch": 60, "start": 0.0, "end": 0.8, "velocity": 90},
            {"pitch": 67, "start": 0.5, "end": 1.2, "velocity": 80},
        ]

    monkeypatch.setattr(transcribe, "transcribe_window", fake_transcribe)
    monkeypatch.setattr(
        pattern,
        "find_cycle",
        lambda *args, **kwargs: {
            "length": 2.0,
            "repeats": 2.5,
            "confidence": 0.9,
            "peak": 0.5,
        },
    )

    response = CLIENT.post(
        "/api/piano/process",
        json={"url": str(source), "start": 0.0, "end": 5.0},
    )
    assert response.status_code == 200, response.text
    job = _wait_job(response.json()["id"])
    assert job["status"] == "ready", job.get("error")
    piece_id = job["result"]["piece_id"]

    piece = CLIENT.get(f"/api/piano/pieces/{piece_id}").json()
    assert piece["note_count"] == 2
    assert piece["cycle"]["length"] == 2.0
    assert piece["window"]["start"] == pytest.approx(0.0)
    assert piece["window"]["end"] == pytest.approx(5.0)
    assert piece["window"]["duration"] == pytest.approx(5.0, abs=0.15)
    assert calls["limit"] == pytest.approx(piece["window"]["duration"], abs=0.15)

    audio = CLIENT.get(f"/api/piano/pieces/{piece_id}/audio")
    assert audio.status_code == 200
    assert audio.headers["content-type"].startswith("audio/")

    listed = CLIENT.get("/api/piano/pieces").json()
    assert any(item["id"] == piece_id for item in listed)


def test_api_rejects_a_missing_source() -> None:
    response = CLIENT.post("/api/piano/analyze", json={"url": ""})
    assert response.status_code == 422


def test_api_404_for_unknown_piece() -> None:
    assert CLIENT.get("/api/piano/pieces/does-not-exist").status_code == 404


def test_keyboard_ui_covers_88_keys_and_hides_the_empty_overlay() -> None:
    """v0.1 UI contract: full keyboard, empty state only when there are no notes."""
    root = Path(__file__).resolve().parents[1] / "piano" / "static"
    script = (root / "piano.js").read_text(encoding="utf-8")
    assert "const FIRST_MIDI = 21;" in script
    assert "const LAST_MIDI = 108;" in script
    assert "emptyEl.hidden = state.notes.length > 0;" in script
    assert "state.notes" in script and "pixelsPerSecond" in script

    css = (root / "piano.css").read_text(encoding="utf-8")
    assert ".empty[hidden]" in css
    assert "#keys" in css

    html = (root / "index.html").read_text(encoding="utf-8")
    assert 'id="keys"' in html
    assert 'id="play"' in html
    assert 'id="seek"' in html
    assert 'id="speed"' in html
    assert 'id="loop"' in html
    assert 'id="synth"' in html
    assert 'id="cycle"' in html
    assert 'id="cycle-length"' in html
    assert 'id="cycle-half"' in html
    assert 'id="cycle-double"' in html

