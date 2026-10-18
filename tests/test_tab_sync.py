from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import db
from app.pipeline.build import build_document
from app.pipeline.export_gp5 import export_gp5
from app.pipeline.model import STANDARD_TUNING, TabNote


def _make_tab(data_dir: Path, tab_id: str = "sync-tab") -> Path:
    document = build_document(
        title="Sync Song",
        artist="Sync Band",
        bpm=140,
        time_signature="4/4",
        tuning=STANDARD_TUNING,
        tab_notes=[TabNote(40, 6, 0, 0, 960)],
        measure_count=1,
    )
    tab_dir = data_dir / "tabs" / tab_id
    tab_dir.mkdir(parents=True)
    export_gp5(document, tab_dir / "tab.gp5")
    meta = {
        "source_type": "import",
        "files": {"gp5": "tab.gp5"},
        "bpm": 140.0,
    }
    (tab_dir / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    track_id = db.create_track(
        title="Sync Song",
        artist="Sync Band",
        source_type="import",
        source_ref=f"import:{tab_id}",
        fingerprint=f"sync:{tab_id}",
    )
    db.create_tab(
        tab_id=tab_id,
        track_id=track_id,
        cache_key=f"sync:{tab_id}",
        directory=f"tabs/{tab_id}",
        title="Sync Song",
        artist="Sync Band",
        bpm=140.0,
        tuning="standard",
        time_signature="4/4",
        measure_count=1,
        note_count=1,
        audio_path="",
        meta=meta,
    )
    return tab_dir


def test_set_tab_sync_persists_drift(
    client: TestClient,
    data_dir: Path,
) -> None:
    tab_dir = _make_tab(data_dir, "sync-tab")
    response = client.post("/api/tabs/sync-tab/sync", data={"drift": "0.005"})
    assert response.status_code == 200, response.text
    assert response.json()["meta"]["sync_drift"] == 0.005

    tab = client.get("/api/tabs/sync-tab").json()
    assert tab["meta"]["sync_drift"] == 0.005

    stored = json.loads((tab_dir / "meta.json").read_text(encoding="utf-8"))
    assert stored["sync_drift"] == 0.005


def test_set_tab_sync_accepts_limits(
    client: TestClient,
    data_dir: Path,
) -> None:
    _make_tab(data_dir, "sync-limits")
    for value in ("0.1", "-0.1"):
        response = client.post(
            "/api/tabs/sync-limits/sync", data={"drift": value}
        )
        assert response.status_code == 200, response.text
        assert response.json()["meta"]["sync_drift"] == float(value)


def test_set_tab_sync_rejects_out_of_range(
    client: TestClient,
    data_dir: Path,
) -> None:
    _make_tab(data_dir, "sync-invalid")
    response = client.post(
        "/api/tabs/sync-invalid/sync", data={"drift": "0.25"}
    )
    assert response.status_code == 422


def test_set_tab_sync_persists_bar_shift(
    client: TestClient,
    data_dir: Path,
) -> None:
    tab_dir = _make_tab(data_dir, "sync-shift")
    response = client.post(
        "/api/tabs/sync-shift/sync",
        data={"drift": "0.002", "offset_bars": "-8"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["meta"]["sync_offset_bars"] == -8.0

    tab = client.get("/api/tabs/sync-shift").json()
    assert tab["meta"]["sync_drift"] == 0.002
    assert tab["meta"]["sync_offset_bars"] == -8.0

    stored = json.loads((tab_dir / "meta.json").read_text(encoding="utf-8"))
    assert stored["sync_offset_bars"] == -8.0


def test_set_tab_sync_rejects_large_bar_shift(
    client: TestClient,
    data_dir: Path,
) -> None:
    _make_tab(data_dir, "sync-shift-invalid")
    response = client.post(
        "/api/tabs/sync-shift-invalid/sync",
        data={"drift": "0", "offset_bars": "100"},
    )
    assert response.status_code == 422


def test_set_tab_sync_unknown_tab(client: TestClient) -> None:
    response = client.post("/api/tabs/does-not-exist/sync", data={"drift": "0"})
    assert response.status_code == 404
