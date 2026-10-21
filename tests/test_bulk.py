"""Bulk import/export of user-owned tab files (v1.66)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import bulk
from app.pipeline.build import build_document
from app.pipeline.export_gp5 import export_gp5
from app.pipeline.model import STANDARD_TUNING, TabNote


def _gp5(path: Path, title: str = "Bulk Song") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = build_document(
        title=title,
        artist="Test Band",
        bpm=100,
        time_signature="4/4",
        tuning=STANDARD_TUNING,
        tab_notes=[TabNote(40, 6, 0, 0, 960)],
        measure_count=1,
    )
    export_gp5(document, path)
    return path


def test_find_tab_files_recursive(data_dir: Path, tmp_path: Path) -> None:
    _gp5(tmp_path / "a.gp5")
    _gp5(tmp_path / "nested" / "b.gp5", "Nested Song")
    (tmp_path / "notes.txt").write_text("x", encoding="utf-8")

    assert [path.name for path in bulk.find_tab_files(tmp_path)] == ["a.gp5", "b.gp5"]
    assert [
        path.name for path in bulk.find_tab_files(tmp_path, recursive=False)
    ] == ["a.gp5"]
    with pytest.raises(NotADirectoryError):
        bulk.find_tab_files(tmp_path / "missing")


def test_import_folder_skips_already_imported(
    data_dir: Path, tmp_path: Path
) -> None:
    source = tmp_path / "source"
    _gp5(source / "song.gp5", "Seek & Destroy")

    first = bulk.import_folder(source)
    assert first["seen"] == 1
    assert len(first["imported"]) == 1
    assert first["skipped"] == []
    tab = first["imported"][0]
    assert tab["title"] == "Seek & Destroy"
    assert tab["artist"] == "Test Band"

    # The digest manifest makes a second run a no-op.
    second = bulk.import_folder(source)
    assert second["imported"] == []
    assert len(second["skipped"]) == 1
    assert second["skipped"][0]["tab_id"] == tab["tab_id"]

    # --force imports it again.
    forced = bulk.import_folder(source, skip_existing=False)
    assert len(forced["imported"]) == 1
    assert forced["imported"][0]["tab_id"] != tab["tab_id"]


def test_import_folder_reports_bad_files(data_dir: Path, tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "broken.gp5").write_bytes(b"not a guitar pro file")

    result = bulk.import_folder(source)
    assert result["imported"] == []
    assert len(result["failed"]) == 1
    assert "broken.gp5" in result["failed"][0]["file"]


def test_export_tabs_writes_files_manifest_and_zip(
    data_dir: Path, tmp_path: Path
) -> None:
    source = tmp_path / "source"
    _gp5(source / "song.gp5", "Seek & Destroy")
    imported = bulk.import_folder(source)["imported"][0]

    out = tmp_path / "exports"
    summary = bulk.export_tabs(out, formats=("gp5",), make_zip=True)

    assert summary["tabs"] == 1
    assert summary["files"] == 1
    assert summary["missing"] == []
    exported = out / "Test Band - Seek & Destroy.gp5"
    assert exported.is_file()
    assert exported.stat().st_size > 0

    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["tabs"][0]["tab_id"] == imported["tab_id"]
    assert manifest["tabs"][0]["files"]["gp5"] == exported.name
    assert Path(summary["zip"]).is_file()


def test_export_tabs_validates_formats(data_dir: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        bulk.export_tabs(tmp_path / "out", formats=("pdf",))
