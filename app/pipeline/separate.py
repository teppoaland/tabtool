"""Run Demucs stem separation as a subprocess."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

KNOWN_STEMS = {"drums", "bass", "other", "vocals", "guitar", "piano"}


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").strip().splitlines()[-12:]
        raise RuntimeError(
            f"Demucs failed ({result.returncode}).\n" + "\n".join(tail)
        )
    return result


def separate_stems(
    audio_path: str | Path,
    out_dir: str | Path,
    model: str = "htdemucs_6s",
    device: str = "cpu",
    segment: int | None = None,
) -> dict[str, Path]:
    """Separate a WAV into stems and return {stem_name: path}."""
    input_path = Path(audio_path)
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "demucs",
        "-n",
        model,
        "-o",
        str(directory),
        "--device",
        device,
    ]
    if segment is not None and segment > 0:
        command += ["--segment", str(segment)]
    command.append(str(input_path))

    _run(command)

    expected_dir = directory / model / input_path.stem
    stems: dict[str, Path] = {}
    if expected_dir.exists():
        for path in expected_dir.glob("*.wav"):
            if path.stem in KNOWN_STEMS:
                stems[path.stem] = path

    if not stems:
        # Fall back to the newest matching stem files if Demucs changed its
        # output directory layout.
        candidates = [
            path
            for path in directory.rglob("*.wav")
            if path.stem in KNOWN_STEMS
        ]
        candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        for path in candidates:
            stems.setdefault(path.stem, path)

    if not stems:
        raise RuntimeError(
            f"Demucs produced no known stems under {directory}. "
            f"Expected a folder like {expected_dir}."
        )
    return stems
