"""Finalizing a generated fingering variant (v1.72, backup/restore v2.04)."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import config, db
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


# === Backup and restore (v2.04) ===========================================


def test_finalize_backs_up_the_variants(client: TestClient, data_dir: Path) -> None:
    """The other fingerings are deleted, so the pre-finalize state is kept."""
    _make_variant_tab(data_dir, "variant-backup")
    tab_dir = data_dir / "tabs" / "variant-backup"
    original_gp5 = (tab_dir / "tab.gp5").read_bytes()
    original_xml = (tab_dir / "tab.musicxml").read_bytes()

    response = client.post(
        "/api/tabs/variant-backup/variant", data={"variant": "v0"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["variant_backup"] == "backups/variant-variant-backup"

    backup = data_dir / "backups" / "variant-variant-backup"
    assert (backup / "tab.gp5").read_bytes() == original_gp5
    assert (backup / "tab.musicxml").read_bytes() == original_xml
    assert (backup / "tab.mid").is_file()
    assert sorted(path.name for path in (backup / "variants").iterdir()) == [
        "v0.json",
        "v1.json",
        "v2.json",
    ]
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["tab_id"] == "variant-backup"
    assert len(manifest["variants"]) == 3
    assert manifest["note_count"] == 3

    summary = {item["id"]: item for item in client.get("/api/tabs").json()}
    assert summary["variant-backup"]["variant_backup"] == (
        "backups/variant-variant-backup"
    )


def test_restore_brings_the_variants_back(
    client: TestClient, data_dir: Path
) -> None:
    """The choice can be undone, so an unknown song can be tried by ear."""
    _make_variant_tab(data_dir, "variant-restore")
    tab_dir = data_dir / "tabs" / "variant-restore"
    original_gp5 = (tab_dir / "tab.gp5").read_bytes()
    stored = db.get_tab("variant-restore")
    assert stored is not None
    db.update_tab_finalize("variant-restore", stored["meta"], 99)

    chosen = client.post(
        "/api/tabs/variant-restore/variant", data={"variant": "v2"}
    )
    assert chosen.status_code == 200
    assert db.get_tab("variant-restore")["note_count"] != 99
    assert not (tab_dir / "variants").exists()

    restored = client.post("/api/tabs/variant-restore/variant/restore")
    assert restored.status_code == 200, restored.text
    body = restored.json()
    assert body["variant_finalized"] is False
    assert body["selected_variant"] == ""
    assert len(body["variants"]) == 3
    assert body["note_count"] == 99

    tab = client.get("/api/tabs/variant-restore").json()
    assert tab["meta"]["variant_finalized"] is False
    assert tab["meta"]["default_variant"] == "v0"
    assert sorted(path.name for path in (tab_dir / "variants").iterdir()) == [
        "v0.json",
        "v1.json",
        "v2.json",
    ]
    assert (tab_dir / "tab.gp5").read_bytes() == original_gp5

    import guitarpro

    song = guitarpro.parse(str(tab_dir / "tab.gp5"))
    assert len(song.tracks) == 3

    # The restored tab can be finalized again with another variant.
    again = client.post(
        "/api/tabs/variant-restore/variant", data={"variant": "v1"}
    )
    assert again.status_code == 200
    assert again.json()["selected_variant"] == "v1"


def test_restore_without_a_backup_is_rejected(
    client: TestClient, data_dir: Path
) -> None:
    _make_variant_tab(data_dir, "variant-nobackup")
    response = client.post("/api/tabs/variant-nobackup/variant/restore")
    assert response.status_code == 422
    assert "varmuuskopio" in response.json()["detail"].lower()


def test_restore_requires_unlock(client: TestClient, data_dir: Path) -> None:
    _make_variant_tab(data_dir, "variant-restore-locked")
    client.post("/api/tabs/variant-restore-locked/variant", data={"variant": "v0"})
    client.post("/api/tabs/variant-restore-locked/library", data={"locked": "true"})
    response = client.post("/api/tabs/variant-restore-locked/variant/restore")
    assert response.status_code == 409


def test_variant_choice_asks_before_deleting() -> None:
    """v2.04: the button confirms the choice and offers an undo."""
    html = (config.STATIC_DIR / "index.html").read_text(encoding="utf-8")
    source = (config.STATIC_DIR / "app.js").read_text(encoding="utf-8")
    assert 'id="variant-dialog"' in html
    assert 'id="variant-restore-button"' in html
    assert 'id="variant-confirm"' in html
    assert "openVariantDialog" in source
    assert "restoreVariants" in source
    assert 'variantButton.addEventListener("click", openVariantDialog)' in source
    assert "/variant/restore" in source
    assert "PALAUTA VERSIOT" in html

