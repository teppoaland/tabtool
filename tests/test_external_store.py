from __future__ import annotations

import math
import os
import shutil
import struct
import wave
from pathlib import Path

import pytest

from app import config, external_store


def _write_wav(path: Path, seconds: float = 0.4) -> None:
    rate = 8000
    frames = int(rate * seconds)
    data = b"".join(
        struct.pack("<h", int(2000 * math.sin(2 * math.pi * 440 * i / rate)))
        for i in range(frames)
    )
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(data)


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


def test_archive_mp3_creates_artist_folder(
    tmp_path: Path,
    monkeypatch,
) -> None:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not available")
    monkeypatch.setattr(config, "EXTERNAL_DIR", tmp_path / "external")
    wav = tmp_path / "song.wav"
    _write_wav(wav)

    target = external_store.archive_mp3(wav, "Test Band", "Test Song")

    expected = (
        tmp_path
        / "external"
        / "audio"
        / "mp3"
        / "Test Band"
        / "Test Band - Test Song.mp3"
    )
    assert target == expected
    assert expected.is_file()
    assert expected.stat().st_size > 0


def test_archive_mp3_uses_unknown_artist_folder(
    tmp_path: Path,
    monkeypatch,
) -> None:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not available")
    monkeypatch.setattr(config, "EXTERNAL_DIR", tmp_path / "external")
    wav = tmp_path / "unknown.wav"
    _write_wav(wav)

    target = external_store.archive_mp3(wav, "", "No Artist Song")

    assert target is not None
    assert target.parent.name == "Unknown Artist"
    assert target.name == "No Artist Song.mp3"


def test_archive_mp3_skips_non_wav(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(config, "EXTERNAL_DIR", tmp_path / "external")
    source = tmp_path / "song.mp3"
    source.write_bytes(b"ID3")

    assert external_store.archive_mp3(source, "Band", "Song") is None
    assert (
        external_store.archive_mp3(tmp_path / "missing.wav", "Band", "Song") is None
    )
