from __future__ import annotations

import os
from pathlib import Path

from app import config, external_store


def test_display_name_strips_illegal_characters() -> None:
    assert external_store.display_name("AC/DC", "Back: in Black?") == (
        "ACDC - Back in Black"
    )
    assert external_store.display_name("", "  Song  ") == "Song"
    assert external_store.display_name("", "", "track") == "track"


def test_archive_external_creates_readable_copy(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(config, "EXTERNAL_DIR", tmp_path / "external")
    source = tmp_path / "source.wav"
    source.write_bytes(b"RIFF-data")

    target = external_store.archive_external(
        source, "audio", "Metallica", "Seek & Destroy"
    )

    assert target == (
        tmp_path / "external" / "audio" / "Metallica - Seek & Destroy.wav"
    )
    assert target is not None and target.is_file()
    assert target.read_bytes() == b"RIFF-data"


def test_archive_external_replaces_existing_target(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(config, "EXTERNAL_DIR", tmp_path / "external")
    source = tmp_path / "source.gp5"
    source.write_bytes(b"first")
    target = external_store.archive_external(
        source, "tabs", "Band", "Song"
    )
    assert target is not None

    source.write_bytes(b"second-version")
    again = external_store.archive_external(source, "tabs", "Band", "Song")

    assert again == target
    assert again is not None and again.read_bytes() == b"second-version"


def test_archive_external_skips_unknown_content(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(config, "EXTERNAL_DIR", tmp_path / "external")
    source = tmp_path / "source.wav"
    source.write_bytes(b"data")

    assert external_store.archive_external(source, "other", "A", "B") is None
    assert (
        external_store.archive_external(tmp_path / "missing.wav", "audio", "A", "B")
        is None
    )


def test_archive_external_keeps_data_root_untouched(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(config, "EXTERNAL_DIR", tmp_path / "external")
    source = tmp_path / "tab.gp5"
    source.write_bytes(b"gp5")
    external_store.archive_external(source, "tabs", "Band", "Song")
    assert source.exists()
    assert os.path.samefile(source, tmp_path / "external" / "tabs" / "Band - Song.gp5")
