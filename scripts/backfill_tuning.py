"""Add tuning labels to tabs imported before v1.68.

Reads the open strings from each stored GP5 file and writes
``tuning_label`` / ``tuning_notes`` / the tuning key, so the library and the
player show e.g. ``D Standard · DGCFAD``. The tab files are not modified.

Usage:
    .venv\\Scripts\\python.exe scripts\\backfill_tuning.py --dry-run
    .venv\\Scripts\\python.exe scripts\\backfill_tuning.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db  # noqa: E402
from app.tuning import describe_pitches, open_strings  # noqa: E402


def _open_strings(path: Path) -> list[int]:
    import guitarpro

    try:
        song = guitarpro.parse(str(path), encoding="utf-8")
    except UnicodeDecodeError:
        song = guitarpro.parse(str(path), encoding="cp1252")
    return open_strings(song)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Only list the tabs")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute tabs that already have a tuning label",
    )
    args = parser.parse_args()

    updated: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []

    for tab in db.list_tabs(200):
        meta = dict(tab.get("meta") or {})
        files = meta.get("files") if isinstance(meta.get("files"), dict) else {}
        name = str(files.get("gp5") or "")
        if not name:
            skipped.append({"tab_id": str(tab["id"]), "reason": "no gp5"})
            continue
        if str(meta.get("tuning_override") or "").strip():
            skipped.append({"tab_id": str(tab["id"]), "reason": "manual override"})
            continue
        if not args.force and str(meta.get("tuning_label") or "").strip():
            skipped.append({"tab_id": str(tab["id"]), "reason": "already set"})
            continue
        try:
            directory = db.resolve_under_data(str(tab.get("directory") or ""))
            path = (directory / name).resolve()
            if path.parent != directory.resolve() or not path.is_file():
                raise FileNotFoundError(name)
            pitches = _open_strings(path)
            if not pitches:
                raise ValueError("no strings in track")
            info = describe_pitches(pitches)
        except Exception as exc:  # noqa: BLE001 - report and continue
            failed.append({"tab_id": str(tab["id"]), "error": str(exc)})
            continue

        entry = {
            "tab_id": str(tab["id"]),
            "title": str(tab.get("title") or ""),
            "label": str(info["text"]),
        }
        if args.dry_run:
            updated.append(entry)
            continue
        meta["tuning_label"] = info["text"]
        meta["tuning_notes"] = info["notes"]
        db.update_tab_meta(str(tab["id"]), meta)
        db.update_tab_tuning(str(tab["id"]), str(info["key"]))
        updated.append(entry)

    print(
        json.dumps(
            {"updated": updated, "skipped": skipped, "failed": failed},
            indent=2,
            ensure_ascii=False,
        )
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
