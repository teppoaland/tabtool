from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import db
from app.pipeline.build import build_document
from app.pipeline.export_gp5 import export_gp5
from app.pipeline.model import STANDARD_TUNING, TabNote


def _make_tab(data_dir: Path, tab_id: str = "tempo-tab") -> None:
    document = build_document(
        title="Tempo Song",
        artist="Tempo Band",
        bpm=100,
        time_signature="4/4",
        tuning=STANDARD_TUNING,
        tab_notes=[TabNote(40, 6, 0, 0, 960)],
        measure_count=1,
    )
    tab_dir = data_dir / "tabs" / tab_id
    tab_dir.mkdir(parents=True)
    export_gp5(document, tab_dir / "tab.gp5")
    track_id = db.create_track(
        title="Tempo Song",
        artist="Tempo Band",
        source_type="import",
        source_ref=f"import:{tab_id}",
        fingerprint=f"tempo:{tab_id}",
    )
    db.create_tab(
        tab_id=tab_id,
        track_id=track_id,
        cache_key=f"tempo:{tab_id}",
        directory=f"tabs/{tab_id}",
        title="Tempo Song",
        artist="Tempo Band",
        bpm=100.0,
        tuning="standard",
        time_signature="4/4",
        measure_count=1,
        note_count=1,
        audio_path="",
        meta={
            "source_type": "import",
            "files": {"gp5": "tab.gp5"},
            "bpm": 100.0,
        },
    )


def test_set_tab_tempo_rewrites_gp5_and_db(
    client: TestClient,
    data_dir: Path,
) -> None:
    _make_tab(data_dir, "tempo-tab")
    response = client.post("/api/tabs/tempo-tab/tempo", data={"bpm": "144"})
    assert response.status_code == 200, response.text
    assert response.json()["bpm"] == 144.0

    tab = client.get("/api/tabs/tempo-tab").json()
    assert tab["bpm"] == 144.0
    assert tab["meta"]["bpm"] == 144.0
    assert tab["meta"]["tempo_override"] == 144.0

    import guitarpro

    song = guitarpro.parse(str(data_dir / "tabs" / "tempo-tab" / "tab.gp5"))
    assert song.tempo == 144


def test_set_tab_tempo_accepts_fraction(
    client: TestClient,
    data_dir: Path,
) -> None:
    tab_dir = data_dir / "tabs" / "tempo-fraction"
    _make_tab(data_dir, "tempo-fraction")
    response = client.post(
        "/api/tabs/tempo-fraction/tempo",
        data={"bpm": "143.5"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["bpm"] == 143.5

    tab = client.get("/api/tabs/tempo-fraction").json()
    assert tab["meta"]["bpm"] == 143.5
    assert tab["meta"]["gp5_tempo"] == 144

    import guitarpro

    song = guitarpro.parse(str(tab_dir / "tab.gp5"))
    assert song.tempo == 144


def test_set_tab_tempo_rejects_invalid_bpm(
    client: TestClient,
    data_dir: Path,
) -> None:
    _make_tab(data_dir, "tempo-invalid")
    response = client.post(
        "/api/tabs/tempo-invalid/tempo",
        data={"bpm": "999"},
    )
    assert response.status_code == 422


def test_set_tab_tempo_handles_cp1252_gp5(
    client: TestClient,
    data_dir: Path,
) -> None:
    """v1.75: an imported GP5 may be cp1252 ("Mötley Crüe" = byte 0xf6).

    A UTF-8-only read raised "'utf-8' codec can't decode byte 0xf6 in position
    1", so the tempo save failed. The route now falls back to cp1252 and writes
    the song back as UTF-8.
    """
    import os

    import guitarpro
    import pytest

    _make_tab(data_dir, "tempo-cp1252")
    path = data_dir / "tabs" / "tempo-cp1252" / "tab.gp5"
    song = guitarpro.parse(str(path), encoding="utf-8")
    song.title = "Mötley Crüe"
    song.artist = "Mötley Crüe"
    temporary = path.with_name(path.name + ".cp1252")
    guitarpro.write(song, str(temporary), encoding="cp1252")
    os.replace(temporary, path)

    with pytest.raises(UnicodeDecodeError):
        guitarpro.parse(str(path), encoding="utf-8")

    response = client.post(
        "/api/tabs/tempo-cp1252/tempo",
        data={"bpm": "113"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["bpm"] == 113.0

    rewritten = guitarpro.parse(str(path), encoding="utf-8")
    assert rewritten.tempo == 113
    assert rewritten.title == "Mötley Crüe"
