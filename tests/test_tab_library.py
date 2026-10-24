"""Library metadata: rename, lock and archive a tab (v1.63)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app import config, db


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


def test_library_rows_are_sorted_by_artist() -> None:
    source = (config.STATIC_DIR / "app.js").read_text(encoding="utf-8")
    assert "function librarySortKey" in source
    assert '${String(tab.artist || "")} ${String(tab.title' in source
    assert "librarySortKey(left).localeCompare" in source


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


def test_locked_tab_settings_are_read_only(
    client: TestClient, data_dir: Path
) -> None:
    """v1.70: the lock protects every stored setting, not only deletion."""
    _make_tab("tab-readonly", title="Read Only")
    assert (
        client.post(
            "/api/tabs/tab-readonly/library", data={"locked": "true"}
        ).status_code
        == 200
    )

    blocked = (
        ("/api/tabs/tab-readonly/library", {"title": "Uusi nimi"}),
        ("/api/tabs/tab-readonly/library", {"artist": "Uusi esittäjä"}),
        ("/api/tabs/tab-readonly/library", {"archived": "true"}),
        ("/api/tabs/tab-readonly/library", {"tuning": "Drop D · DADGBE"}),
        ("/api/tabs/tab-readonly/library", {"locked": "true"}),
        ("/api/tabs/tab-readonly/sync", {"drift": "0.01"}),
        ("/api/tabs/tab-readonly/sync", {"drift": "0", "offset_bars": "0.25"}),
        ("/api/tabs/tab-readonly/tempo", {"bpm": "150"}),
    )
    for url, data in blocked:
        response = client.post(url, data=data)
        assert response.status_code == 409, (url, data, response.text)
        assert "locked" in response.json()["detail"].lower()

    assert client.post("/api/tabs/tab-readonly/attach-audio").status_code == 409
    assert client.delete("/api/tabs/tab-readonly").status_code == 409

    unchanged = client.get("/api/tabs/tab-readonly").json()
    assert unchanged["title"] == "Read Only"
    assert unchanged["locked"] is True
    assert unchanged["archived"] is False
    assert unchanged["meta"].get("sync_drift") is None
    assert unchanged["meta"].get("sync_offset_bars") is None

    unlocked = client.post(
        "/api/tabs/tab-readonly/library", data={"locked": "false"}
    )
    assert unlocked.status_code == 200
    assert unlocked.json()["locked"] is False

    # After unlocking the same settings save normally again.
    saved = client.post("/api/tabs/tab-readonly/sync", data={"drift": "0.01"})
    assert saved.status_code == 200
    assert saved.json()["meta"]["sync_drift"] == 0.01


def test_unlock_and_edit_in_one_save(client: TestClient, data_dir: Path) -> None:
    _make_tab("tab-unlock", title="Locked Name")
    client.post("/api/tabs/tab-unlock/library", data={"locked": "true"})

    response = client.post(
        "/api/tabs/tab-unlock/library",
        data={"locked": "false", "title": "New Name"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["locked"] is False
    assert response.json()["title"] == "New Name"


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
    assert tab["artist_override"] == ""
    assert tab["locked"] is False
    assert tab["archived"] is False


def test_artist_override_roundtrip(client: TestClient, data_dir: Path) -> None:
    """v2.03: a YouTube uploader is not necessarily the artist."""
    _make_tab("tab-artist", title="Xsuaalisuuteen (Official audio)", artist="Knight Rydazz")

    saved = client.post(
        "/api/tabs/tab-artist/library", data={"artist": "Reino Nordin"}
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["artist"] == "Reino Nordin"
    assert body["artist_override"] == "Reino Nordin"
    assert body["original_artist"] == "Knight Rydazz"

    library = {entry["id"]: entry for entry in client.get("/api/tabs").json()}
    assert library["tab-artist"]["artist"] == "Reino Nordin"

    # A blank artist clears the override and restores the generated one.
    cleared = client.post("/api/tabs/tab-artist/library", data={"artist": "  "})
    assert cleared.json()["artist"] == "Knight Rydazz"
    assert cleared.json()["artist_override"] == ""


def test_artist_override_sorts_the_library(client: TestClient, data_dir: Path) -> None:
    _make_tab("tab-a", title="Song A", artist="Zeta Uploader")
    _make_tab("tab-b", title="Song B", artist="Alpha Band")

    client.post("/api/tabs/tab-a/library", data={"artist": "Aalto"})
    order = [entry["id"] for entry in client.get("/api/tabs").json()]
    assert order == ["tab-a", "tab-b"]


def test_summary_exposes_source_links(client: TestClient, data_dir: Path) -> None:
    """The library can tell where the audio and the tab file came from."""
    _make_tab("tab-source", title="Imported Song", artist="Imported Band")
    db.update_tab_meta(
        "tab-source",
        {
            "source_type": "import",
            "youtube_channel": "Knight Rydazz",
            "tab_source_url": "https://example.com/tabs/song.gp5",
            "tab_source_file": "song.gp3",
            "files": {"gp5": "tab.gp5"},
        },
    )
    entry = client.get("/api/tabs/tab-source").json()
    assert entry["meta"]["tab_source_url"] == "https://example.com/tabs/song.gp5"

    summary = {item["id"]: item for item in client.get("/api/tabs").json()}["tab-source"]
    assert summary["tab_source_url"] == "https://example.com/tabs/song.gp5"
    assert summary["tab_source_file"] == "song.gp3"
    assert summary["source_url"] == ""
    assert summary["channel"] == "Knight Rydazz"


def test_summary_falls_back_to_the_legacy_youtube_source(
    client: TestClient, data_dir: Path
) -> None:
    """AI tabs from before v2.03 kept the link in meta.source."""
    _make_tab("tab-legacy-source", title="Animal", artist="W.A.S.P.")
    db.update_tab_meta(
        "tab-legacy-source",
        {
            "source_type": "youtube",
            "source": "https://youtu.be/7COTI8k-rgo",
            "files": {"gp5": "tab.gp5"},
        },
    )
    summary = {
        item["id"]: item for item in client.get("/api/tabs").json()
    }["tab-legacy-source"]
    assert summary["source_url"] == "https://youtu.be/7COTI8k-rgo"


def test_summary_never_links_a_local_path(client: TestClient, data_dir: Path) -> None:
    _make_tab("tab-local", title="Local Song")
    db.update_tab_meta(
        "tab-local",
        {
            "source_type": "upload",
            "source": "audio/local-song.wav",
            "tab_source_url": "file:///C:/secret.gp5",
            "files": {"gp5": "tab.gp5"},
        },
    )
    summary = {item["id"]: item for item in client.get("/api/tabs").json()}["tab-local"]
    assert summary["source_url"] == ""
    assert summary["tab_source_url"] == ""


def test_library_editor_is_a_details_dialog() -> None:
    """v2.03: NIMEÄ became Tiedot and opens a modal with every editable field."""
    html = (config.STATIC_DIR / "index.html").read_text(encoding="utf-8")
    source = (config.STATIC_DIR / "app.js").read_text(encoding="utf-8")
    remote_html = (config.STATIC_DIR / "remote.html").read_text(encoding="utf-8")

    assert '"NIMEÄ"' not in source
    assert '"Tiedot"' in source
    assert 'id="detail-dialog"' in html
    for field in ('id="detail-artist"', 'id="detail-name"', 'id="detail-tuning"'):
        assert field in html
    assert "openDetailDialog" in source
    assert "artist_override" in source or "artist" in source
    # The phone offers the same artist correction.
    assert 'id="adjust-artist"' in remote_html


def test_youtube_uploader_can_be_replaced_by_the_real_artist(
    client: TestClient, data_dir: Path
) -> None:
    """The Reino Nordin case: the uploader was stored as the artist.

    The channel stays visible as the YouTube upload, but the artist can be
    corrected without losing where the audio came from.
    """
    _make_tab(
        "tab-reino",
        title="Xsuaalisuuteen (Official audio)",
        artist="Knight Rydazz",
    )
    db.update_tab_meta(
        "tab-reino",
        {
            "source_type": "youtube",
            "source": "https://youtu.be/xyz",
            "youtube_channel": "Knight Rydazz",
            "files": {"gp5": "tab.gp5"},
        },
    )

    fixed = client.post(
        "/api/tabs/tab-reino/library",
        data={
            "artist": "Reino Nordin",
            "title": "Xsuaalisuuteen (Official audio)",
        },
    )
    assert fixed.status_code == 200, fixed.text
    body = fixed.json()
    assert body["artist"] == "Reino Nordin"
    assert body["artist_override"] == "Reino Nordin"
    assert body["original_artist"] == "Knight Rydazz"
    assert body["channel"] == "Knight Rydazz"
    assert body["source_url"] == "https://youtu.be/xyz"

    row = {item["id"]: item for item in client.get("/api/tabs").json()}["tab-reino"]
    assert row["artist"] == "Reino Nordin"
    assert row["title"] == "Xsuaalisuuteen (Official audio)"


