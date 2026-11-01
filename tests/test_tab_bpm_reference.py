"""v2.28: the tab's own BPM stays a reference when TAB BPM is adjusted.

The viewer metadata line and the Tiedot dialog show the BPM the tab was
created with next to the adjusted value, so the user can always compare
against where the tab started. Only metadata is kept; the GP5 tempo write,
the /tempo route's behaviour and the playback chain stay as they were.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import db
from app.pipeline.build import build_document
from app.pipeline.export_gp5 import export_gp5
from app.pipeline.model import STANDARD_TUNING, TabNote

STATIC = Path(__file__).resolve().parents[1] / "app" / "static"
APP_JS = STATIC / "app.js"


def _gp5(tmp_path: Path, bpm: int = 100) -> Path:
    document = build_document(
        title="Reference Song",
        artist="Reference Band",
        bpm=bpm,
        time_signature="4/4",
        tuning=STANDARD_TUNING,
        tab_notes=[TabNote(40, 6, 0, 0, 960)],
        measure_count=1,
    )
    path = tmp_path / "reference.gp5"
    export_gp5(document, path)
    return path


def _import_tab(client: TestClient, tmp_path: Path) -> dict[str, object]:
    path = _gp5(tmp_path)
    response = client.post(
        "/api/tabs/import",
        files={"file": ("reference.gp5", path.read_bytes(), "application/octet-stream")},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _legacy_tab(
    data_dir: Path,
    tab_id: str,
    *,
    bpm: float = 100.0,
    meta_extra: dict[str, object] | None = None,
) -> None:
    """A tab row as generated before v2.28: no original_bpm in the meta."""
    document = build_document(
        title="Legacy Song",
        artist="Legacy Band",
        bpm=int(bpm),
        time_signature="4/4",
        tuning=STANDARD_TUNING,
        tab_notes=[TabNote(40, 6, 0, 0, 960)],
        measure_count=1,
    )
    tab_dir = data_dir / "tabs" / tab_id
    tab_dir.mkdir(parents=True)
    export_gp5(document, tab_dir / "tab.gp5")
    track_id = db.create_track(
        title="Legacy Song",
        artist="Legacy Band",
        source_type="import",
        source_ref=f"import:{tab_id}",
        fingerprint=f"legacy:{tab_id}",
    )
    meta: dict[str, object] = {
        "source_type": "import",
        "files": {"gp5": "tab.gp5"},
        "bpm": float(bpm),
    }
    meta.update(meta_extra or {})
    db.create_tab(
        tab_id=tab_id,
        track_id=track_id,
        cache_key=f"legacy:{tab_id}",
        directory=f"tabs/{tab_id}",
        title="Legacy Song",
        artist="Legacy Band",
        bpm=float(bpm),
        tuning="standard",
        time_signature="4/4",
        measure_count=1,
        note_count=1,
        audio_path="",
        meta=meta,
    )


def test_import_records_the_file_bpm_as_reference(
    client: TestClient,
    tmp_path: Path,
) -> None:
    summary = _import_tab(client, tmp_path)
    assert summary["bpm"] == 100.0
    assert summary["original_bpm"] == 100.0

    tab = client.get(f"/api/tabs/{summary['id']}").json()
    assert tab["meta"]["original_bpm"] == 100.0


def test_tempo_edit_keeps_the_reference(
    client: TestClient,
    tmp_path: Path,
) -> None:
    summary = _import_tab(client, tmp_path)
    tab_id = str(summary["id"])

    first = client.post(f"/api/tabs/{tab_id}/tempo", data={"bpm": "144"})
    assert first.status_code == 200, first.text
    assert first.json()["bpm"] == 144.0
    assert first.json()["original_bpm"] == 100.0

    # A second edit keeps the same reference instead of following the value.
    second = client.post(f"/api/tabs/{tab_id}/tempo", data={"bpm": "120"})
    assert second.status_code == 200, second.text
    assert second.json()["bpm"] == 120.0
    assert second.json()["original_bpm"] == 100.0

    tab = client.get(f"/api/tabs/{tab_id}").json()
    assert tab["meta"]["original_bpm"] == 100.0
    assert tab["meta"]["bpm"] == 120.0
    assert tab["meta"]["tempo_override"] == 120.0


def test_legacy_tab_gets_its_pre_edit_bpm_as_reference(
    client: TestClient,
    data_dir: Path,
) -> None:
    """A tab made before v2.28 has no original_bpm; its first save captures
    the value it had, which is the value it was created with."""
    _legacy_tab(data_dir, "legacy-tab")
    response = client.post("/api/tabs/legacy-tab/tempo", data={"bpm": "144"})
    assert response.status_code == 200, response.text
    assert response.json()["original_bpm"] == 100.0
    assert response.json()["bpm"] == 144.0


def test_legacy_adjusted_tab_captures_its_current_bpm_as_the_start(
    client: TestClient,
    data_dir: Path,
) -> None:
    """A tab adjusted before v2.28 has no stored original. Its first save in
    v2.28 records the value it has now, so later adjustments still have a
    comparison point (the earlier history cannot be recovered)."""
    _legacy_tab(
        data_dir,
        "legacy-edited",
        bpm=120.0,
        meta_extra={"tempo_override": 120.0},
    )
    response = client.post("/api/tabs/legacy-edited/tempo", data={"bpm": "130"})
    assert response.status_code == 200, response.text
    assert response.json()["original_bpm"] == 120.0
    assert response.json()["bpm"] == 130.0

    tab = client.get("/api/tabs/legacy-edited").json()
    assert tab["meta"]["original_bpm"] == 120.0


def _source() -> str:
    return APP_JS.read_text(encoding="utf-8")


def test_metadata_line_shows_the_reference_beside_the_current_bpm() -> None:
    source = _source()
    helper = source[source.index("function tabReferenceBpm"):]
    helper = helper[: helper.index("\n  }\n")]
    # The viewer loads the raw tab row, so the reference comes from meta.
    assert "meta.original_bpm" in helper
    assert "tab.original_bpm" in helper

    line = source[source.index("function bpmMetaText"):]
    line = line[: line.index("\n  }\n")]
    assert "tabReferenceBpm(tab)" in line
    assert "nyt" in line

    render = source[source.index("function renderTabMeta"):]
    render = render[: render.index("\n  }\n")]
    assert "bpmMetaText(tab)" in render

    detail = source[source.index("function renderDetailMeta"):]
    detail = detail[: detail.index("\n  }\n")]
    assert "tabReferenceBpm(tab)" in detail


def test_playback_rate_never_writes_the_metadata() -> None:
    """Nopeus is a practice speed: it must not touch the tab's reference."""
    source = _source()
    snippet = source[source.index("function setPlaybackRate"):]
    snippet = snippet[: snippet.index("\n  }\n")]
    for forbidden in ("meta", "original_bpm", "fetch", "api."):
        assert forbidden not in snippet
