from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import db, jobs


def _make_tab(
    data_dir: Path,
    *,
    tab_id: str,
    audio_path: str,
    options: dict | None = None,
) -> None:
    if audio_path:
        audio_file = data_dir / audio_path
        audio_file.parent.mkdir(parents=True, exist_ok=True)
        audio_file.write_bytes(b"RIFF-fake")
    track_id = db.create_track(
        title="Section Song",
        artist="Section Band",
        source_type="local",
        source_ref=str(data_dir / audio_path) if audio_path else "local:test",
        fingerprint=f"section:{tab_id}",
        audio_path=audio_path or None,
    )
    db.create_tab(
        tab_id=tab_id,
        track_id=track_id,
        cache_key=f"section:{tab_id}",
        directory=f"tabs/{tab_id}",
        title="Section Song",
        artist="Section Band",
        bpm=120.0,
        tuning="standard",
        time_signature="4/4",
        measure_count=1,
        note_count=1,
        audio_path=audio_path,
        meta={"options": options or {"grid": 16, "separate": False}},
    )


def test_section_job_uses_tab_audio_and_options(
    client: TestClient,
    data_dir: Path,
    monkeypatch,
) -> None:
    tab_id = db.new_id()
    _make_tab(
        data_dir,
        tab_id=tab_id,
        audio_path="audio/section.wav",
        options={"grid": 16, "separate": False},
    )
    captured: dict = {}

    def fake_submit_job(**kwargs):
        captured.update(kwargs)
        return {"id": "job-section", "status": "queued"}

    monkeypatch.setattr(jobs, "submit_job", fake_submit_job)
    response = client.post(
        f"/api/tabs/{tab_id}/section",
        data={"start_seconds": "10", "clip_seconds": "30"},
    )
    assert response.status_code == 200, response.text
    assert captured["source_type"] == "local"
    assert Path(captured["source_ref"]).name == "section.wav"
    assert captured["options"].start_seconds == 10.0
    assert captured["options"].clip_seconds == 30.0
    assert "[0:10 +30s]" in captured["title"]
    assert captured["artist"] == "Section Band"
    assert captured["fingerprint"].startswith("local:")


def test_section_job_requires_audio(
    client: TestClient,
    data_dir: Path,
    monkeypatch,
) -> None:
    tab_id = db.new_id()
    _make_tab(data_dir, tab_id=tab_id, audio_path="")
    monkeypatch.setattr(
        jobs,
        "submit_job",
        lambda **kwargs: {"id": "unused", "status": "queued"},
    )
    response = client.post(
        f"/api/tabs/{tab_id}/section",
        data={"start_seconds": "0", "clip_seconds": "30"},
    )
    assert response.status_code == 422


def test_section_job_unknown_tab(client: TestClient) -> None:
    response = client.post(
        "/api/tabs/unknown/section",
        data={"start_seconds": "0", "clip_seconds": "30"},
    )
    assert response.status_code == 404
