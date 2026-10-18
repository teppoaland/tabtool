"""GP5 link import and the GP5 + YouTube audio job."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

import app.config as config
from app import jobs
from app.pipeline.audio_source import AudioSource
from app.pipeline.build import build_document
from app.pipeline.export_gp5 import export_gp5
from app.pipeline.model import STANDARD_TUNING, TabNote


def _gp5_bytes(tmp_path: Path) -> bytes:
    document = build_document(
        title="Imported Song",
        artist="Imported Band",
        bpm=100,
        time_signature="4/4",
        tuning=STANDARD_TUNING,
        tab_notes=[TabNote(40, 6, 0, 0, 960)],
        measure_count=1,
    )
    path = tmp_path / "import.gp5"
    export_gp5(document, path)
    return path.read_bytes()


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


def fake_audio_job(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the YouTube download with a local fake WAV."""

    def run(job, options, report=None):  # noqa: ANN001
        if report is not None:
            report(jobs.STAGE_DOWNLOADING)
        path = Path(config.DATA_DIR) / "audio" / "fake-youtube.wav"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"RIFF-fake")
        audio = AudioSource(
            path=path,
            duration=200.0,
            source_type="youtube",
            source_ref=job["source_ref"],
            title="YouTube title",
            artist="YouTube artist",
        )
        return audio, "YouTube title", "YouTube artist"

    monkeypatch.setattr(jobs, "run_audio_job", run)


def test_import_tab_from_url(
    client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = _gp5_bytes(tmp_path)
    monkeypatch.setattr(
        "app.main.tab_download.download_tab_bytes",
        lambda url: (data, "imported.gp5"),
    )
    response = client.post(
        "/api/tabs/import-url",
        data={"url": "https://example.com/tabs/imported"},
    )
    assert response.status_code == 200, response.text
    summary = response.json()
    assert summary["title"] == "Imported Song"
    assert summary["artist"] == "Imported Band"
    assert summary["source_type"] == "import"

    tab = client.get(f"/api/tabs/{summary['id']}").json()
    assert tab["audio_path"] == ""
    assert tab["meta"]["files"]["gp5"] == "tab.gp5"


def test_job_with_gp5_imports_tab_and_attaches_audio(
    client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = _gp5_bytes(tmp_path)
    monkeypatch.setattr(
        "app.main.tab_download.download_tab_bytes",
        lambda url: (data, "imported.gp5"),
    )

    fake_audio_job(monkeypatch)

    response = client.post(
        "/api/jobs",
        data={
            "youtube_url": "https://youtu.be/Wh-btSHnblQ",
            "gp5_url": "https://example.com/tabs/wasp/animal?download",
            "options": '{"archive_mp3": false}',
        },
    )
    assert response.status_code == 202, response.text
    queued = response.json()
    assert queued["tab_id"]
    assert queued["tab"]["title"] == "Imported Song"
    assert queued["options"]["audio_only"] is True

    job = wait_for_job(client, queued["id"])
    assert job["status"] == "ready", job.get("error")
    assert job["tab_id"] == queued["tab_id"]

    tab = client.get(f"/api/tabs/{queued['tab_id']}").json()
    assert tab["title"] == "Imported Song"
    assert tab["artist"] == "Imported Band"
    assert tab["audio_path"] == "audio/fake-youtube.wav"
    assert tab["meta"]["duration_seconds"] == 200.0
    assert tab["meta"]["mp3_created"] is False

    audio = client.get(f"/api/tabs/{queued['tab_id']}/audio")
    assert audio.status_code == 200
    assert audio.content == b"RIFF-fake"


def test_import_file_with_youtube_attaches_audio(
    client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Local GP5 file + YouTube link is one operation, like GP5 link + YT."""
    data = _gp5_bytes(tmp_path)
    fake_audio_job(monkeypatch)

    response = client.post(
        "/api/tabs/import",
        files={"file": ("imported.gp5", data, "application/octet-stream")},
        data={
            "youtube_url": "https://youtu.be/beWvPkYHaic",
            "options": '{"archive_mp3": false}',
        },
    )
    assert response.status_code == 200, response.text
    queued = response.json()
    assert queued["tab_id"] == queued["tab"]["id"]
    assert queued["tab"]["title"] == "Imported Song"
    assert queued["options"]["audio_only"] is True

    job = wait_for_job(client, queued["id"])
    assert job["status"] == "ready", job.get("error")
    assert job["tab_id"] == queued["tab_id"]

    tab = client.get(f"/api/tabs/{queued['tab_id']}").json()
    assert tab["title"] == "Imported Song"
    assert tab["audio_path"] == "audio/fake-youtube.wav"
    assert tab["meta"]["duration_seconds"] == 200.0
    assert tab["meta"]["mp3_created"] is False


def test_import_file_rejects_non_youtube_url(
    client, tmp_path: Path
) -> None:
    data = _gp5_bytes(tmp_path)
    response = client.post(
        "/api/tabs/import",
        files={"file": ("imported.gp5", data, "application/octet-stream")},
        data={"youtube_url": "https://example.com/watch?v=1"},
    )
    assert response.status_code == 422


def test_gp5_job_requires_youtube_link(client) -> None:
    response = client.post(
        "/api/jobs",
        data={"gp5_url": "https://example.com/tabs/song.gp5"},
    )
    assert response.status_code == 422

    response = client.post(
        "/api/jobs",
        files={"file": ("song.mp3", b"ID3", "audio/mpeg")},
        data={"gp5_url": "https://example.com/tabs/song.gp5"},
    )
    assert response.status_code == 422


def test_client_cannot_route_an_audio_only_job() -> None:
    options = jobs.JobOptions.from_mapping(
        {"audio_only": True, "attach_tab_id": "attacker"}
    )
    assert options.audio_only is False
    assert options.attach_tab_id == ""
    assert options.archive_mp3 is True

    stored = jobs.JobOptions.from_mapping(
        {
            "audio_only": True,
            "attach_tab_id": "abc123",
            "archive_mp3": False,
        },
        allow_internal=True,
    )
    assert stored.audio_only is True
    assert stored.attach_tab_id == "abc123"
    assert stored.archive_mp3 is False


def test_mp3_flag_does_not_change_the_cache_key() -> None:
    with_mp3 = jobs.JobOptions.from_mapping({"archive_mp3": True})
    without_mp3 = jobs.JobOptions.from_mapping({"archive_mp3": False})
    assert with_mp3.as_cache_dict() == without_mp3.as_cache_dict()
    assert "archive_mp3" not in with_mp3.as_cache_dict()
