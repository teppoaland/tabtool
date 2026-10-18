from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import db


def _make_tab(
    data_dir: Path,
    *,
    tab_id: str,
    title: str,
    artist: str,
    audio_path: str,
    duration: float | None = None,
) -> None:
    if audio_path:
        audio_file = data_dir / audio_path
        audio_file.parent.mkdir(parents=True, exist_ok=True)
        audio_file.write_bytes(b"RIFF-fake")
    track_id = db.create_track(
        title=title,
        artist=artist,
        source_type="local" if audio_path else "import",
        source_ref=str(data_dir / audio_path) if audio_path else f"import:{tab_id}",
        fingerprint=f"audio-test:{tab_id}",
        audio_path=audio_path or None,
        duration_seconds=duration,
    )
    db.create_tab(
        tab_id=tab_id,
        track_id=track_id,
        cache_key=f"audio-test:{tab_id}",
        directory=f"tabs/{tab_id}",
        title=title,
        artist=artist,
        bpm=140.0,
        tuning="standard",
        time_signature="4/4",
        measure_count=1,
        note_count=1,
        audio_path=audio_path,
        meta={
            "source_type": "local" if audio_path else "import",
            "duration_seconds": duration,
            "options": {},
        },
    )


def test_attach_audio_from_same_named_tab(
    client: TestClient,
    data_dir: Path,
) -> None:
    _make_tab(
        data_dir,
        tab_id="source-tab",
        title="Song",
        artist="Band",
        audio_path="audio/source.wav",
        duration=123.0,
    )
    _make_tab(
        data_dir,
        tab_id="target-tab",
        title="Song",
        artist="Band",
        audio_path="",
    )
    response = client.post("/api/tabs/target-tab/attach-audio")
    assert response.status_code == 200, response.text
    summary = response.json()
    assert summary["id"] == "target-tab"
    assert summary["source_id"] == "source-tab"
    assert summary["source_bpm"] == 140.0

    target = client.get("/api/tabs/target-tab").json()
    assert target["audio_path"] == "audio/source.wav"
    assert target["meta"]["audio_path"] == "audio/source.wav"
    assert target["meta"]["audio_source_tab"] == "source-tab"
    assert target["meta"]["duration_seconds"] == 123.0

    audio = client.get("/api/tabs/target-tab/audio")
    assert audio.status_code == 200
    assert audio.content == b"RIFF-fake"


def test_attach_audio_without_matching_source(
    client: TestClient,
    data_dir: Path,
) -> None:
    _make_tab(
        data_dir,
        tab_id="lonely-tab",
        title="No Audio Anywhere",
        artist="Nobody",
        audio_path="",
    )
    response = client.post("/api/tabs/lonely-tab/attach-audio")
    assert response.status_code == 404
