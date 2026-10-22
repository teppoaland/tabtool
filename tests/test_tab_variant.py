"""Finalizing a generated fingering variant (v1.72)."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import db
from app.pipeline.build import build_document
from app.pipeline.export_gp5 import export_gp5_variants
from app.pipeline.export_midi import export_midi
from app.pipeline.export_musicxml import export_musicxml
from app.pipeline.model import STANDARD_TUNING, TabNote
from app.pipeline.variant_store import snapshot_document

LABELS = ["V1 · Avoimet kielet", "V2 · Boksi", "V3 · Vähän liikettä"]


def _make_variant_tab(data_dir: Path, tab_id: str = "variant-tab") -> None:
    tab_dir = data_dir / "tabs" / tab_id
    tab_dir.mkdir(parents=True)

    documents = []
    for index, label in enumerate(LABELS):
        notes = [
            TabNote(45, 5, 0, 0, 960),
            TabNote(52, 4, index, 0, 960),
            TabNote(67, 1, 3, 960, 1920),
        ]
        documents.append(
            build_document(
                title="Variant Song",
                artist="TabTool",
                bpm=120,
                time_signature="4/4",
                tuning=STANDARD_TUNING,
                tab_notes=notes,
                measure_count=2,
            )
        )

    export_gp5_variants(
        [(document, label) for document, label in zip(documents, LABELS)],
        tab_dir / "tab.gp5",
    )
    export_musicxml(documents[0], tab_dir / "tab.musicxml")
    export_midi(documents[0], tab_dir / "tab.mid")

    variants_dir = tab_dir / "variants"
    variants_dir.mkdir()
    variant_meta = []
    for index, (document, label) in enumerate(zip(documents, LABELS)):
        variant_id = f"v{index}"
        (variants_dir / f"{variant_id}.json").write_text(
            json.dumps(snapshot_document(document), ensure_ascii=False),
            encoding="utf-8",
        )
        variant_meta.append(
            {
                "id": variant_id,
                "label": label,
                "track": index,
                "source": f"variants/{variant_id}.json",
                "playability": {"score": 8.0 - index},
            }
        )

    meta = {
        "title": "Variant Song",
        "artist": "TabTool",
        "source_type": "import",
        "bpm": 120.0,
        "time_signature": [4, 4],
        "tuning": "standard",
        "files": {
            "gp5": "tab.gp5",
            "musicxml": "tab.musicxml",
            "midi": "tab.mid",
        },
        "variants": variant_meta,
        "default_variant": "v0",
        "selected_variant": "",
        "variant_finalized": False,
    }
    (tab_dir / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    track_id = db.create_track(
        title="Variant Song",
        artist="TabTool",
        source_type="import",
        source_ref=f"variant-test:{tab_id}",
        fingerprint=f"variant-test:{tab_id}",
    )
    db.create_tab(
        tab_id=tab_id,
        track_id=track_id,
        cache_key=f"variant-test:{tab_id}",
        directory=f"tabs/{tab_id}",
        title="Variant Song",
        artist="TabTool",
        bpm=120.0,
        tuning="standard",
        time_signature="4/4",
        measure_count=2,
        note_count=documents[0].note_count,
        audio_path="",
        meta=meta,
    )


def test_finalize_rewrites_files_and_meta(
    client: TestClient, data_dir: Path
) -> None:
    _make_variant_tab(data_dir)

    tab = client.get("/api/tabs/variant-tab").json()
    assert len(tab["meta"]["variants"]) == 3
    assert tab["meta"]["variant_finalized"] is False

    response = client.post(
        "/api/tabs/variant-tab/variant", data={"variant": "v1"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["selected_variant"] == "v1"
    assert body["variant_finalized"] is True

    tab = client.get("/api/tabs/variant-tab").json()
    assert tab["meta"]["variant_finalized"] is True
    assert tab["meta"]["selected_variant"] == "v1"

    import guitarpro

    song = guitarpro.parse(str(data_dir / "tabs" / "variant-tab" / "tab.gp5"))
    assert len(song.tracks) == 1
    assert not (data_dir / "tabs" / "variant-tab" / "variants").exists()

    # Re-requesting the already chosen variant is idempotent.
    again = client.post(
        "/api/tabs/variant-tab/variant", data={"variant": "v1"}
    )
    assert again.status_code == 200


def test_finalize_requires_unlock(client: TestClient, data_dir: Path) -> None:
    _make_variant_tab(data_dir, "variant-locked")
    client.post("/api/tabs/variant-locked/library", data={"locked": "true"})
    response = client.post(
        "/api/tabs/variant-locked/variant", data={"variant": "v1"}
    )
    assert response.status_code == 409


def test_finalize_unknown_variant(client: TestClient, data_dir: Path) -> None:
    _make_variant_tab(data_dir, "variant-unknown")
    response = client.post(
        "/api/tabs/variant-unknown/variant", data={"variant": "nope"}
    )
    assert response.status_code == 422
