"""Bulk import/export for the user's own tab files.

Nothing here downloads anything: the user supplies the files (own Guitar Pro
exports, tabs they are allowed to keep). Files live under ``DATA_DIR`` and
``EXTERNAL_DIR``, both private and gitignored, so nothing ends up in the
public repository. Exports are plain GP5/MusicXML/MIDI copies plus a
``manifest.json``.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any, Iterable, Sequence

from app import db, tab_import
from app.external_store import display_name

TAB_SUFFIXES = (".gp3", ".gp4", ".gp5", ".musicxml", ".xml", ".mxl")
EXPORT_SUFFIX = {"gp5": ".gp5", "musicxml": ".musicxml", "midi": ".mid"}
MANIFEST_NAME = ".tabtool-imported.json"


def find_tab_files(root: Path, *, recursive: bool = True) -> list[Path]:
    """List importable tab files under ``root`` (sorted, case-insensitive)."""
    root = Path(root)
    if not root.is_dir():
        raise NotADirectoryError(str(root))
    iterator = root.rglob("*") if recursive else root.glob("*")
    return sorted(
        (
            path
            for path in iterator
            if path.is_file() and path.suffix.lower() in TAB_SUFFIXES
        ),
        key=lambda path: str(path).lower(),
    )


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest_path(folder: Path) -> Path:
    return folder / MANIFEST_NAME


def _load_manifest(folder: Path) -> dict[str, str]:
    path = _manifest_path(folder)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items()}


def _save_manifest(folder: Path, manifest: dict[str, str]) -> None:
    path = _manifest_path(folder)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    temporary.replace(path)


def import_folder(
    folder: Path,
    *,
    recursive: bool = True,
    skip_existing: bool = True,
) -> dict[str, Any]:
    """Import every GP3/GP4/GP5/MusicXML file in ``folder`` into the library.

    Already imported files are recognised by their SHA-256 digest, which is
    stored in ``.tabtool-imported.json`` next to the source files.
    """
    folder = Path(folder)
    files = find_tab_files(folder, recursive=recursive)
    manifest = _load_manifest(folder) if skip_existing else {}
    imported: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    for path in files:
        digest = _digest(path)
        known = manifest.get(digest)
        if skip_existing and known and db.get_tab(known) is not None:
            skipped.append(
                {"file": str(path), "reason": "already imported", "tab_id": known}
            )
            continue
        try:
            tab = tab_import.import_tab_bytes(path.read_bytes(), path.name)
        except (OSError, ValueError) as exc:
            failed.append({"file": str(path), "error": str(exc)})
            continue
        manifest[digest] = str(tab["id"])
        imported.append(
            {
                "file": str(path),
                "tab_id": tab["id"],
                "title": tab.get("title"),
                "artist": tab.get("artist"),
            }
        )
        if skip_existing:
            _save_manifest(folder, manifest)

    if skip_existing:
        _save_manifest(folder, manifest)
    return {
        "folder": str(folder),
        "seen": len(files),
        "imported": imported,
        "skipped": skipped,
        "failed": failed,
    }


def _tab_file(tab: dict[str, Any], fmt: str) -> Path | None:
    meta = tab.get("meta") if isinstance(tab.get("meta"), dict) else {}
    files = meta.get("files") if isinstance(meta.get("files"), dict) else {}
    name = str(files.get(fmt) or "")
    if not name:
        return None
    try:
        directory = db.resolve_under_data(str(tab.get("directory") or ""))
    except ValueError:
        return None
    candidate = (directory / name).resolve()
    directory = directory.resolve()
    if candidate.parent != directory or not candidate.is_file():
        return None
    return candidate


def _export_name(tab: dict[str, Any], suffix: str, used: set[str]) -> str:
    base = display_name(
        str(tab.get("artist") or ""),
        str(tab.get("title") or ""),
        str(tab.get("id") or "tab"),
    )
    name = f"{base}{suffix}"
    counter = 2
    while name.lower() in used:
        name = f"{base} ({counter}){suffix}"
        counter += 1
    used.add(name.lower())
    return name


def export_tabs(
    out_dir: Path,
    *,
    tab_ids: Iterable[str] | None = None,
    formats: Sequence[str] = ("gp5", "musicxml", "midi"),
    make_zip: bool = False,
    limit: int = 200,
) -> dict[str, Any]:
    """Copy tab files to ``out_dir`` with a manifest and optional ZIP."""
    unknown = [fmt for fmt in formats if fmt not in EXPORT_SUFFIX]
    if unknown:
        raise ValueError(f"Unknown export format(s): {', '.join(unknown)}")

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if tab_ids:
        tabs = [tab for tab in (db.get_tab(tab_id) for tab_id in tab_ids) if tab]
    else:
        tabs = db.list_tabs(limit)

    used: set[str] = set()
    exported: list[dict[str, Any]] = []
    missing: list[dict[str, str]] = []
    written: list[Path] = []
    for tab in tabs:
        entry: dict[str, Any] = {
            "tab_id": tab["id"],
            "title": tab.get("title"),
            "artist": tab.get("artist"),
            "bpm": tab.get("bpm"),
            "measure_count": tab.get("measure_count"),
            "note_count": tab.get("note_count"),
            "files": {},
        }
        for fmt in formats:
            source = _tab_file(tab, fmt)
            if source is None:
                missing.append({"tab_id": str(tab["id"]), "format": fmt})
                continue
            name = _export_name(tab, EXPORT_SUFFIX[fmt], used)
            target = out / name
            shutil.copy2(source, target)
            written.append(target)
            entry["files"][fmt] = name
        if entry["files"]:
            exported.append(entry)

    manifest = {
        "exported_at": db.utc_now(),
        "out_dir": str(out),
        "formats": list(formats),
        "tabs": exported,
        "missing": missing,
    }
    manifest_path = out / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    zip_path = ""
    if make_zip:
        archive = out.parent / f"{out.name}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in written:
                bundle.write(path, path.name)
            bundle.write(manifest_path, manifest_path.name)
        zip_path = str(archive)

    return {
        "out_dir": str(out),
        "tabs": len(exported),
        "files": len(written),
        "missing": missing,
        "manifest": str(manifest_path),
        "zip": zip_path,
    }
