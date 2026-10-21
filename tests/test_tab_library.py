"""Library metadata: rename, lock and archive a tab (v1.63)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app import db


def _make_tab(tab_id: str, *, title: str, artist: str = "Artist") -> None:
    track_id = db.create_track(
        title=title,
        artist=artist,
        source_type="import",
        source_ref=f"library-test:{tab_id}",
        fingerprint=f"library-test:{tab_id}",
        audio_path=None,
        duration_seconds=None,
    )
    db.create_tab(
        tab_id=tab_id,
        track_id=track_id,
        cache_key=f"library-test:{tab_id}",
        directory=f"tabs/{tab_id}",
        title=title,
        artist=artist,
        bpm=120.0,
        tuning="standard",
        time_signature="4/4",
        measure_count=4,
        note_count=8,
        audio_path="",
        meta={"source_type": "import", "files": {"gp5": "tab.gp5"}},
    )


def test_rename_keeps_original_title(client: TestClient, data_dir: Path) -> None:
    _make_tab("tab-one", title="Seek & Destroy")

    response = client.post(
        "/api/tabs/tab-one/library",
        data={"title": "Seek & Destroy (oma sormitus)"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Seek & Destroy (oma sormitus)"
    assert body["title_override"] == "Seek & Destroy (oma sormitus)"
    assert body["original_title"] == "Seek & Destroy"
    assert client.get("/api/tabs/tab-one").json()["title"] == (
        "Seek & Destroy (oma sormitus)"
    )

    # A blank name clears the override and falls back to the generated name.
    cleared = client.post("/api/tabs/tab-one/library", data={"title": "  "})
    assert cleared.json()["title"] == "Seek & Destroy"
    assert cleared.json()["title_override"] == ""


def test_locked_tab_cannot_be_deleted(client: TestClient, data_dir: Path) -> None:
    _make_tab("tab-locked", title="Locked Song")

    locked = client.post("/api/tabs/tab-locked/library", data={"locked": "true"})
    assert locked.status_code == 200
    assert locked.json()["locked"] is True
    assert client.delete("/api/tabs/tab-locked").status_code == 409

    unlocked = client.post("/api/tabs/tab-locked/library", data={"locked": "false"})
    assert unlocked.json()["locked"] is False
    assert client.delete("/api/tabs/tab-locked").status_code == 200


def test_archive_flag_roundtrip(client: TestClient, data_dir: Path) -> None:
    _make_tab("tab-archive", title="Archived Song")

    archived = client.post(
        "/api/tabs/tab-archive/library", data={"archived": "true"}
    )
    assert archived.json()["archived"] is True
    library = {entry["id"]: entry for entry in client.get("/api/tabs").json()}
    assert library["tab-archive"]["archived"] is True

    restored = client.post(
        "/api/tabs/tab-archive/library", data={"archived": "false"}
    )
    assert restored.json()["archived"] is False
    library = {entry["id"]: entry for entry in client.get("/api/tabs").json()}
    assert library["tab-archive"]["archived"] is False


def test_library_is_sorted_by_artist_and_name(
    client: TestClient, data_dir: Path
) -> None:
    _make_tab("tab-b", title="Zebra", artist="Alpha")
    _make_tab("tab-a", title="Apple", artist="Zulu")
    _make_tab("tab-c", title="beta", artist="Alpha")
    client.post("/api/tabs/tab-b/library", data={"title": "Aardvark"})

    order = [entry["id"] for entry in client.get("/api/tabs").json()]
    assert order == ["tab-b", "tab-c", "tab-a"]


def test_tab_summary_exposes_youtube_channel(
    client: TestClient, data_dir: Path
) -> None:
    track_id = db.create_track(
        title="Animal",
        artist="W.A.S.P.",
        source_type="youtube",
        source_ref="https://youtu.be/7COTI8k-rgo",
        fingerprint="channel-test",
        audio_path=None,
        duration_seconds=None,
    )
    db.create_tab(
        tab_id="tab-channel",
        track_id=track_id,
        cache_key="channel-test",
        directory="tabs/tab-channel",
        title="Animal",
        artist="W.A.S.P.",
        bpm=120.0,
        tuning="standard",
        time_signature="4/4",
        measure_count=4,
        note_count=8,
        audio_path="",
        meta={
            "source_type": "youtube",
            "youtube_channel": "James Sly",
            "files": {"gp5": "tab.gp5"},
        },
    )

    library = client.get("/api/tabs").json()
    assert library[0]["channel"] == "James Sly"
    full = client.get("/api/tabs/tab-channel").json()
    assert full["meta"]["youtube_channel"] == "James Sly"


def test_tuning_override_roundtrip(client: TestClient, data_dir: Path) -> None:
    _make_tab("tab-tuning", title="Animal", artist="W.A.S.P.")
    db.update_tab_meta(
        "tab-tuning",
        {
            "source_type": "import",
            "tuning_label": "D Standard · DGCFAD",
            "files": {"gp5": "tab.gp5"},
        },
    )

    library = {entry["id"]: entry for entry in client.get("/api/tabs").json()}
    assert library["tab-tuning"]["tuning_label"] == "D Standard · DGCFAD"

    override = client.post(
        "/api/tabs/tab-tuning/library", data={"tuning": "Drop D · DADGBE"}
    )
    assert override.status_code == 200
    assert override.json()["tuning_label"] == "Drop D · DADGBE"
    assert override.json()["tuning_override"] == "Drop D · DADGBE"

    cleared = client.post(
        "/api/tabs/tab-tuning/library", data={"tuning_clear": "true"}
    )
    assert cleared.json()["tuning_override"] == ""
    assert cleared.json()["tuning_label"] == "D Standard · DGCFAD"


def test_migration_adds_library_columns(data_dir: Path) -> None:
    """A database from before v1.63 gains the library columns on init."""
    path = data_dir / "tabtool.sqlite3"
    with sqlite3.connect(str(path)) as conn:
        conn.executescript(
            """
            CREATE TABLE tabs (
                id TEXT PRIMARY KEY,
                track_id INTEGER NOT NULL,
                cache_key TEXT NOT NULL UNIQUE,
                directory TEXT NOT NULL,
                title TEXT NOT NULL,
                artist TEXT NOT NULL DEFAULT '',
                bpm REAL NOT NULL DEFAULT 0,
                tuning TEXT NOT NULL DEFAULT 'standard',
                time_signature TEXT NOT NULL DEFAULT '4/4',
                measure_count INTEGER NOT NULL DEFAULT 0,
                note_count INTEGER NOT NULL DEFAULT 0,
                audio_path TEXT NOT NULL DEFAULT '',
                meta_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            INSERT INTO tabs (id, track_id, cache_key, directory, title, created_at)
            VALUES ('legacy', 1, 'legacy', 'tabs/legacy', 'Legacy Song', '2026-01-01');
            """
        )

    db.init_db()
    tab = db.get_tab("legacy")
    assert tab is not None
    assert tab["title"] == "Legacy Song"
    assert tab["title_override"] == ""
    assert tab["locked"] is False
    assert tab["archived"] is False
