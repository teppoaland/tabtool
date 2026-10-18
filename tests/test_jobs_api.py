"""Job API: queue, worker, cache and export endpoints with a mocked pipeline."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

import pytest

import app.config as config
from app import db, jobs
from app.pipeline.audio_source import AudioSource
from app.pipeline.build import build_document
from app.pipeline.model import STANDARD_TUNING, TabNote

FAKE_GP5 = b"GP5-FAKE"
FAKE_XML = b"<score-partwise/>"
FAKE_MIDI = b"MThd"


def patch_exports(monkeypatch: pytest.MonkeyPatch) -> None:
    def writer(data: bytes) -> Callable[[Any, Path], Path]:
        def _write(document: Any, path: Path) -> Path:
            path.write_bytes(data)
            return path

        return _write

    monkeypatch.setattr("app.pipeline.export_gp5.export_gp5", writer(FAKE_GP5))
    monkeypatch.setattr("app.pipeline.export_musicxml.export_musicxml", writer(FAKE_XML))
    monkeypatch.setattr("app.pipeline.export_midi.export_midi", writer(FAKE_MIDI))


def fake_pipeline(
    calls: list[dict[str, Any]] | None = None,
) -> Callable[..., dict[str, Any]]:
    def run(job: dict[str, Any], options: jobs.JobOptions, report=None):
        if calls is not None:
            calls.append(
                {"source_ref": job["source_ref"], "options": options.as_dict()}
            )
        if report is not None:
            if options.separate:
                report(jobs.STAGE_SEPARATING)
            report(jobs.STAGE_TRANSCRIBING)
            report(jobs.STAGE_BUILDING)

        audio_path = Path(config.DATA_DIR) / "audio" / "fake.wav"
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(b"RIFF-fake")
        audio = AudioSource(
            path=audio_path,
            duration=30.0,
            source_type=job["source_type"],
            source_ref=job["source_ref"],
            title=job["title"],
        )
        notes = [TabNote(pitch=64, string=1, fret=0, start_tick=0, duration_ticks=960)]
        document = build_document(
            title=job["title"],
            artist=job["artist"],
            bpm=120.0,
            time_signature="4/4",
            tuning=STANDARD_TUNING,
            tab_notes=notes,
            measure_count=2,
            source_audio=str(audio_path),
            warnings=["fake warning"],
        )
        return {
            "audio": audio,
            "document": document,
            "warnings": ["fake warning"],
            "bpm": 120.0,
            "raw_bpm": 120.0,
            "stem": "full-mix",
            "detected_notes": 1,
            "tab_notes": 1,
        }

    return run


def wait_for_job(client, job_id: str, timeout: float = 15.0) -> dict[str, Any]:
    deadline = time.time() + timeout
    job: dict[str, Any] | None = None
    while time.time() < deadline:
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()
        if job["status"] in {"ready", "failed"}:
            return job
        time.sleep(0.05)
    raise AssertionError(f"job did not finish: {job}")


def test_upload_job_produces_downloadable_tab(client, monkeypatch) -> None:
    monkeypatch.setattr(jobs, "run_pipeline", fake_pipeline())
    patch_exports(monkeypatch)

    response = client.post(
        "/api/jobs",
        files={"file": ("My Song.mp3", b"ID3audio", "audio/mpeg")},
        data={"options": '{"separate": false}'},
    )
    assert response.status_code == 202
    job = wait_for_job(client, response.json()["id"])
    assert job["status"] == "ready", job
    assert job["stage"] == "ready"
    assert job["progress"] == pytest.approx(1.0)
    assert job["tab_id"]
    assert job["warnings"] == ["fake warning"]

    tab = client.get(f"/api/tabs/{job['tab_id']}").json()
    assert tab["title"] == "My Song"
    assert tab["measure_count"] == 2
    assert tab["note_count"] == 1
    assert tab["meta"]["files"]["gp5"] == "tab.gp5"

    score = client.get(f"/api/tabs/{job['tab_id']}/score/gp5")
    assert score.status_code == 200
    assert score.content == FAKE_GP5
    assert "attachment" not in score.headers.get("content-disposition", "")

    export = client.get(f"/api/tabs/{job['tab_id']}/export/gp5")
    assert export.status_code == 200
    assert "attachment" in export.headers["content-disposition"]
    assert client.get(f"/api/tabs/{job['tab_id']}/export/midi").content == FAKE_MIDI

    audio = client.get(f"/api/tabs/{job['tab_id']}/audio")
    assert audio.status_code == 200
    assert audio.content == b"RIFF-fake"
    assert audio.headers.get("accept-ranges") == "bytes"

    library = client.get("/api/tabs").json()
    assert library[0]["id"] == job["tab_id"]


def test_identical_upload_uses_cache(client, monkeypatch) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(jobs, "run_pipeline", fake_pipeline(calls))
    patch_exports(monkeypatch)

    files = {"file": ("same.mp3", b"same-bytes", "audio/mpeg")}
    first = client.post("/api/jobs", files=files, data={"options": "{}"}).json()
    first = wait_for_job(client, first["id"])
    assert first["status"] == "ready"

    second = client.post("/api/jobs", files=files, data={"options": "{}"}).json()
    assert second["status"] == "ready"
    assert second["cached"] is True
    assert second["tab_id"] == first["tab_id"]
    assert len(calls) == 1

    regenerated = client.post(
        "/api/jobs", files=files, data={"options": "{}", "regenerate": "true"}
    ).json()
    regenerated = wait_for_job(client, regenerated["id"])
    assert regenerated["status"] == "ready"
    assert regenerated["cached"] is False
    assert regenerated["tab_id"] != first["tab_id"]
    assert len(calls) == 2


def test_pipeline_failure_marks_job_failed(client, monkeypatch) -> None:
    def boom(job, options, report=None):
        raise RuntimeError("basic pitch exploded")

    monkeypatch.setattr(jobs, "run_pipeline", boom)

    response = client.post(
        "/api/jobs",
        files={"file": ("broken.mp3", b"ID3broken", "audio/mpeg")},
        data={"options": "{}"},
    )
    job = wait_for_job(client, response.json()["id"])
    assert job["status"] == "failed"
    assert job["stage"] == "failed"
    assert "basic pitch exploded" in job["error"]
    tabs_dir = Path(config.DATA_DIR) / "tabs"
    assert not list(tabs_dir.glob(".pending-*"))


def test_job_source_and_option_validation(client) -> None:
    assert client.post("/api/jobs", data={}).status_code == 422
    assert (
        client.post(
            "/api/jobs", data={"youtube_url": "https://example.com/watch?v=1"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/jobs",
            data={"youtube_url": "https://youtu.be/abc", "options": "{oops"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/jobs",
            files={"file": ("notes.txt", b"x", "text/plain")},
        ).status_code
        == 415
    )
    assert (
        client.post("/api/jobs", data={"local_path": "Z:/nope/none.mp3"}).status_code
        == 404
    )
    assert (
        client.post(
            "/api/jobs", files={"file": ("clip.mp3", b"x", "audio/mpeg")},
            data={"options": '{"grid": 12}'},
        ).status_code
        == 422
    )
    assert client.get("/api/jobs/unknown").status_code == 404
    assert client.get("/api/tabs/unknown").status_code == 404
    assert client.get("/api/tabs/unknown/score/gp5").status_code == 404
    assert client.get("/api/tabs/unknown/audio").status_code == 404


def test_tab_paths_cannot_escape_data_dir(client, data_dir: Path) -> None:
    outside_audio = data_dir.parent / "outside.wav"
    outside_audio.write_bytes(b"secret")

    track_id = db.create_track(
        title="Evil",
        artist="",
        source_type="upload",
        source_ref="audio/uploads/x.mp3",
        fingerprint="upload:evil",
    )
    db.create_tab(
        tab_id="evil",
        track_id=track_id,
        cache_key="evil-key",
        directory="../outside",
        title="Evil",
        artist="",
        bpm=120.0,
        tuning="standard",
        time_signature="4/4",
        measure_count=1,
        note_count=1,
        audio_path="../outside.wav",
        meta={"files": {"gp5": "../../outside.wav"}},
    )

    assert client.get("/api/tabs/evil/score/gp5").status_code == 404
    assert client.get("/api/tabs/evil/export/gp5").status_code == 404
    assert client.get("/api/tabs/evil/audio").status_code == 404


def test_upload_filename_is_sanitized(client, monkeypatch) -> None:
    monkeypatch.setattr(jobs, "run_pipeline", fake_pipeline())
    patch_exports(monkeypatch)

    response = client.post(
        "/api/jobs",
        files={"file": ("../../evil name.MP3", b"ID3evil", "audio/mpeg")},
        data={"options": '{"separate": false}'},
    )
    assert response.status_code == 202
    job = wait_for_job(client, response.json()["id"])
    assert job["title"] == "evil name"

    uploads = list((Path(config.DATA_DIR) / "audio" / "uploads").iterdir())
    assert len(uploads) == 1
    assert uploads[0].parent == (Path(config.DATA_DIR) / "audio" / "uploads")
    assert uploads[0].suffix == ".mp3"
    assert not (Path(config.DATA_DIR).parent / "evil name.mp3").exists()

