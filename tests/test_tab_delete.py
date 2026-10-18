"""Deleting a song removes its tab, audio and stems but keeps the MP3."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import config, db


def _make_tab(
    data_dir: Path,
    *,
    tab_id: str,
    title: str,
    artist: str,
    audio_path: str,
) -> int:
    track_id = db.create_track(
        title=title,
        artist=artist,
        source_type="local" if audio_path else "import",
        source_ref=f"test:{tab_id}",
        fingerprint=f"delete-test:{tab_id}",
        audio_path=audio_path or None,
        duration_seconds=200.0 if audio_path else None,
    )
    db.create_tab(
        tab_id=tab_id,
        track_id=track_id,
        cache_key=f"delete-test:{tab_id}",
        directory=f"tabs/{tab_id}",
        title=title,
        artist=artist,
        bpm=120.0,
        tuning="standard",
        time_signature="4/4",
        measure_count=4,
        note_count=8,
        audio_path=audio_path,
        meta={
            "source_type": "local" if audio_path else "import",
            "audio_path": audio_path,
            "files": {"gp5": "tab.gp5"},
        },
    )
    directory = data_dir / "tabs" / tab_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "tab.gp5").write_bytes(b"GP5")
    return track_id


def _make_audio(data_dir: Path, relative: str) -> Path:
    path = data_dir / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"RIFF-fake")
    return path


def test_delete_keeps_shared_audio_and_mp3(client: TestClient, data_dir: Path) -> None:
    _make_tab(
        data_dir,
        tab_id="tab-a",
        title="Song",
        artist="Band",
        audio_path="audio/song.wav",
    )
    _make_tab(
        data_dir,
        tab_id="tab-b",
        title="Song",
        artist="Band",
        audio_path="audio/song.wav",
    )
    audio = _make_audio(data_dir, "audio/song.wav")
    stems = data_dir / "stems" / "htdemucs_6s" / "song"
    stems.mkdir(parents=True)
    (stems / "guitar.wav").write_bytes(b"RIFF-stem")

    mp3 = config.EXTERNAL_DIR / "audio" / "mp3" / "Band" / "Band - Song.mp3"
    mp3.parent.mkdir(parents=True, exist_ok=True)
    mp3.write_bytes(b"ID3-mp3")

    job = db.create_job(
        job_id="job-a",
        track_id=int(db.get_tab("tab-a")["track_id"]),
        options={},
        status="ready",
        stage="ready",
        progress=1.0,
        tab_id="tab-a",
    )
    assert job["id"] == "job-a"

    response = client.delete("/api/tabs/tab-a")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["tab_id"] == "tab-a"
    assert result["audio_removed"] is False
    assert result["mp3_kept"] is True

    assert client.get("/api/tabs/tab-a").status_code == 404
    assert db.get_job("job-a") is None
    assert not (data_dir / "tabs" / "tab-a").exists()
    assert audio.is_file()
    assert stems.is_dir()
    assert mp3.is_file()

    # The last tab releases the shared audio and its stems too.
    response = client.delete("/api/tabs/tab-b")
    assert response.status_code == 200, response.text
    assert response.json()["audio_removed"] is True
    assert not audio.exists()
    assert not stems.exists()
    assert mp3.is_file()


def test_delete_tab_without_audio(client: TestClient, data_dir: Path) -> None:
    _make_tab(
        data_dir,
        tab_id="imported",
        title="Imported",
        artist="",
        audio_path="",
    )
    response = client.delete("/api/tabs/imported")
    assert response.status_code == 200, response.text
    assert response.json()["audio_removed"] is False
    assert not (data_dir / "tabs" / "imported").exists()
    assert client.get("/api/tabs/imported").status_code == 404


def test_delete_unknown_tab(client: TestClient) -> None:
    assert client.delete("/api/tabs/missing").status_code == 404
