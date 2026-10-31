"""v2.25: an own MP3/WAV can be attached to an imported GP tab.

Both import paths are covered: a local GP file + own audio
(``/api/tabs/import`` with ``audio_file``) and a GP link + own audio
(``/api/jobs`` with ``gp5_url``). The tab is imported first and the audio is
attached by the same audio-only job the YouTube path already uses, so the
playback chain is untouched. The last tests guard the UI (clear button) and
that the old "use a YouTube link instead" refusal is gone.
"""

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

STATIC = Path(__file__).resolve().parents[1] / "app" / "static"
APP_JS = STATIC / "app.js"
INDEX_HTML = STATIC / "index.html"
STYLE_CSS = STATIC / "style.css"


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


def fake_own_audio_job(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the ffmpeg normalization with a local fake WAV."""

    def run(job, options, report=None):  # noqa: ANN001
        if report is not None:
            report(jobs.STAGE_DOWNLOADING)
        path = Path(config.DATA_DIR) / "audio" / "fake-own.wav"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"RIFF-own")
        audio = AudioSource(
            path=path,
            duration=200.0,
            source_type="local",
            source_ref=str(job["source_ref"]),
            title="Own audio",
        )
        return audio, "Own audio", ""

    monkeypatch.setattr(jobs, "run_audio_job", run)



def test_import_file_with_own_audio_attaches_the_audio(
    client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A local GP file and an own MP3 are one operation (v2.25)."""
    data = _gp5_bytes(tmp_path)
    fake_own_audio_job(monkeypatch)

    response = client.post(
        "/api/tabs/import",
        files={
            "file": ("oma-tabi.gp5", data, "application/octet-stream"),
            "audio_file": ("oma-biisi.mp3", b"ID3-own-audio", "audio/mpeg"),
        },
        data={"options": '{"archive_mp3": false}'},
    )
    assert response.status_code == 200, response.text
    queued = response.json()
    assert queued["tab_id"] == queued["tab"]["id"]
    assert queued["tab"]["title"] == "Imported Song"
    assert queued["options"]["audio_only"] is True
    assert queued["options"]["attach_tab_id"] == queued["tab_id"]

    job = wait_for_job(client, queued["id"])
    assert job["status"] == "ready", job.get("error")
    assert job["tab_id"] == queued["tab_id"]

    tab = client.get(f"/api/tabs/{queued['tab_id']}").json()
    assert tab["title"] == "Imported Song"
    assert tab["audio_path"] == "audio/fake-own.wav"
    assert tab["meta"]["duration_seconds"] == 200.0
    assert tab["meta"]["audio_source_type"] == "upload"
    assert "audio_source_url" not in tab["meta"]
    assert tab["meta"]["mp3_created"] is False
    assert tab["meta"]["tab_source_file"] == "oma-tabi.gp5"

    audio = client.get(f"/api/tabs/{queued['tab_id']}/audio")
    assert audio.status_code == 200
    assert audio.content == b"RIFF-own"



def test_gp_link_with_own_audio_attaches_the_audio(
    client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A GP link + an uploaded own audio file instead of a YouTube link."""
    data = _gp5_bytes(tmp_path)
    monkeypatch.setattr(
        "app.main.tab_download.download_tab_bytes",
        lambda url: (data, "imported.gp5"),
    )
    fake_own_audio_job(monkeypatch)

    response = client.post(
        "/api/jobs",
        files={"file": ("oma-biisi.mp3", b"ID3", "audio/mpeg")},
        data={"gp5_url": "https://example.com/tabs/song.gp5"},
    )
    assert response.status_code == 202, response.text
    queued = response.json()
    assert queued["tab_id"]
    assert queued["options"]["audio_only"] is True

    job = wait_for_job(client, queued["id"])
    assert job["status"] == "ready", job.get("error")

    tab = client.get(f"/api/tabs/{queued['tab_id']}").json()
    assert tab["audio_path"] == "audio/fake-own.wav"
    assert tab["meta"]["audio_source_type"] == "upload"


def test_audio_job_resolves_the_stored_upload_path(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An uploaded file lives under data/, so the job resolves it there."""
    seen: dict[str, str] = {}

    def fake_prepare(
        source, dest_dir, clip_seconds=None, start_seconds=None, title=None
    ):  # noqa: ANN001
        seen["source"] = str(source)
        path = Path(config.DATA_DIR) / "audio" / "normalized-own.wav"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"RIFF")
        return AudioSource(
            path=path,
            duration=10.0,
            source_type="local",
            source_ref=str(source),
            title="Own",
        )

    monkeypatch.setattr("app.pipeline.audio_source.prepare_audio", fake_prepare)
    job = {
        "source_type": "upload",
        "source_ref": "audio/uploads/abc123.mp3",
        "title": "Own",
        "artist": "",
        "track_id": None,
    }
    audio, _title, _artist = jobs.run_audio_job(job, jobs.JobOptions(), None)
    assert seen["source"] == str(
        Path(config.DATA_DIR).resolve() / "audio" / "uploads" / "abc123.mp3"
    )
    assert audio.path.name == "normalized-own.wav"


def test_non_audio_upload_is_rejected_before_the_tab_is_imported(
    client, tmp_path: Path
) -> None:
    data = _gp5_bytes(tmp_path)
    before = client.get("/api/tabs").json()
    response = client.post(
        "/api/tabs/import",
        files={
            "file": ("oma-tabi.gp5", data, "application/octet-stream"),
            "audio_file": ("muistiinpanot.txt", b"muistiinpano", "text/plain"),
        },
    )
    assert response.status_code == 415
    assert client.get("/api/tabs").json() == before


def test_audio_and_youtube_are_not_accepted_together(
    client, tmp_path: Path
) -> None:
    data = _gp5_bytes(tmp_path)
    response = client.post(
        "/api/tabs/import",
        files={
            "file": ("oma-tabi.gp5", data, "application/octet-stream"),
            "audio_file": ("oma-biisi.mp3", b"ID3", "audio/mpeg"),
        },
        data={"youtube_url": "https://youtu.be/Wh-btSHnblQ"},
    )
    assert response.status_code == 422


# === UI (v2.25) ===========================================================


def test_own_audio_field_has_a_clear_button() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    start = html.index('<span class="file-pick">')
    wrapper = html[start:]
    wrapper = wrapper[: wrapper.index("</span>")]
    assert 'id="file-input"' in wrapper
    assert 'id="file-clear"' in wrapper

    css = STYLE_CSS.read_text(encoding="utf-8")
    block = css[css.index(".file-pick {"):]
    block = block[: block.index("}")]
    assert "display: flex" in block


def test_clear_button_empties_the_file_selection() -> None:
    source = APP_JS.read_text(encoding="utf-8")
    assert (
        'fileClearButton.addEventListener("click", clearAudioFile);' in source
    )
    body = source[source.index("function clearAudioFile()"):]
    body = body[: body.index("\n  }")]
    assert 'fileInput.value = ""' in body
    for forbidden in ("audio.", "api.", "playbackRate", "fetch("):
        assert forbidden not in body


def test_gp_file_and_own_audio_are_one_operation() -> None:
    source = APP_JS.read_text(encoding="utf-8")
    # The old refusal is gone: the audio may be an own file now.
    assert "GP5-lähteen kanssa" not in source
    assert 'data.append("audio_file", audioFile);' in source
    assert "await importTabFile(gp5File, url, file);" in source
