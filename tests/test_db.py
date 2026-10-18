"""SQLite layer: schema, cache keys, uploads and path guards."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from app import db, jobs


def test_schema_tables_exist(data_dir: Path) -> None:
    db.init_db()
    with db.connection() as conn:
        names = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {"tracks", "jobs", "tabs", "oauth_tokens", "settings"} <= names


def test_track_and_job_lifecycle(data_dir: Path) -> None:
    track_id = db.create_track(
        title="Song",
        artist="Band",
        source_type="upload",
        source_ref="audio/uploads/x.mp3",
        fingerprint="upload:abc",
    )
    job = db.create_job(
        job_id="job1", track_id=track_id, options={"grid": 16}, cache_key="key1"
    )
    assert job["status"] == "queued"
    assert job["stage"] == "queued"
    assert job["options"] == {"grid": 16}
    assert job["cached"] is False
    assert job["title"] == "Song"

    updated = db.update_job(
        "job1", status="running", stage="transcribing", progress=0.55, warnings=["w"]
    )
    assert updated is not None
    assert updated["stage"] == "transcribing"
    assert updated["progress"] == pytest.approx(0.55)
    assert updated["warnings"] == ["w"]

    assert db.get_job("missing") is None
    assert db.get_track(track_id) is not None


def test_cache_key_is_stable_and_sensitive() -> None:
    options = jobs.JobOptions(separate=False, grid=8).as_dict()
    assert jobs.cache_key("upload:abc", options) == jobs.cache_key(
        "upload:abc", jobs.JobOptions(separate=False, grid=8).as_dict()
    )
    assert jobs.cache_key("upload:abc", options) != jobs.cache_key(
        "upload:abc", jobs.JobOptions(separate=False, grid=16).as_dict()
    )
    assert jobs.cache_key("upload:abc", options) != jobs.cache_key(
        "upload:def", options
    )


def test_resolve_under_data_rejects_traversal(data_dir: Path) -> None:
    inside = db.resolve_under_data("tabs/abc/tab.gp5")
    assert data_dir.resolve() in inside.parents
    with pytest.raises(ValueError):
        db.resolve_under_data("../escape.txt")
    with pytest.raises(ValueError):
        db.to_data_relative(data_dir.parent / "outside.mp3")


def test_save_upload_validates_format_size_and_content(data_dir: Path) -> None:
    path, digest, size = jobs.save_upload(io.BytesIO(b"audio-bytes"), "My Song.MP3")
    assert path.exists()
    assert path.parent.name == "uploads"
    assert path.suffix == ".mp3"
    assert size == len(b"audio-bytes")
    assert len(digest) == 64

    with pytest.raises(ValueError):
        jobs.save_upload(io.BytesIO(b"x"), "notes.txt")
    with pytest.raises(ValueError):
        jobs.save_upload(io.BytesIO(b"x" * 10), "clip.mp3", max_bytes=5)
    with pytest.raises(ValueError):
        jobs.save_upload(io.BytesIO(b""), "empty.mp3")


def test_job_options_validation() -> None:
    options = jobs.JobOptions.from_mapping(
        {"grid": "8", "separate": "false", "tuning": "Drop D"}
    )
    assert options.grid == 8
    assert options.separate is False
    assert options.tuning == "drop_d"

    with pytest.raises(ValueError):
        jobs.JobOptions.from_mapping({"grid": 12})
    with pytest.raises(ValueError):
        jobs.JobOptions.from_mapping({"bpm": 5})
    with pytest.raises(ValueError):
        jobs.JobOptions.from_mapping({"model": "nope"})
    with pytest.raises(ValueError):
        jobs.JobOptions.from_mapping({"time_signature": "4/4/x"})


def test_clean_title_strips_paths_and_extension() -> None:
    assert jobs.clean_title("../../etc/My_Song.mp3") == "My Song"
    assert jobs.clean_title("", "YouTube audio") == "YouTube audio"


def test_settings_roundtrip(data_dir: Path) -> None:
    assert db.get_setting("theme") is None
    db.set_setting("theme", "dark")
    db.set_setting("theme", "darker")
    assert db.get_setting("theme") == "darker"


def test_import_tabs_from_disk(client, data_dir: Path) -> None:
    directory = data_dir / "tabs" / "old-song"
    directory.mkdir(parents=True)
    (directory / "tab.gp5").write_bytes(b"GP5")
    (directory / "tab.musicxml").write_bytes(b"<score/>")
    (directory / "tab.mid").write_bytes(b"MThd")
    audio = data_dir / "audio" / "old.wav"
    audio.parent.mkdir(parents=True, exist_ok=True)
    audio.write_bytes(b"RIFF")
    meta = {
        "title": "Old Song",
        "artist": "Someone",
        "source_type": "local",
        "source": "C:/Music/old.mp3",
        "audio_path": str(audio),
        "duration_seconds": 120.0,
        "bpm": 128.0,
        "tuning": "drop_d",
        "time_signature": [4, 4],
        "measures": 40,
        "tab_notes": 300,
        "files": {
            "gp5": "tab.gp5",
            "musicxml": "tab.musicxml",
            "midi": "tab.mid",
        },
    }
    (directory / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    library = client.get("/api/tabs").json()
    assert [entry["id"] for entry in library] == ["old-song"]
    assert library[0]["title"] == "Old Song"
    assert library[0]["bpm"] == pytest.approx(128.0)
    assert library[0]["measure_count"] == 40
    assert client.get("/api/tabs/old-song/score/gp5").content == b"GP5"
    assert client.get("/api/tabs/old-song/audio").status_code == 200

    # Import must be idempotent.
    assert len(client.get("/api/tabs").json()) == 1
