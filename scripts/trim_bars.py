"""Remove extra bars from a tab so the score ends where the audio ends.

The viewer's clock follows the *notated* timeline, so a tab whose tail runs
past the recording keeps the cursor past the music. `--bars` takes 1-based bar
numbers ("137,138" or "136-138") and drops them from every track, then the rest
is renumbered and the bar starts recomputed.

The original GP5 is copied to `data/backups/<id>-<timestamp>/` first and the
written file is validated by reading it back.

Usage:
    .venv\\\\Scripts\\\\python.exe scripts\\\\trim_bars.py --tab <id> --bars 137,138 --dry-run
    .venv\\\\Scripts\\\\python.exe scripts\\\\trim_bars.py --tab <id> --bars 137,138 --reset-sync
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db, tab_edit  # noqa: E402


def _parse_bars(text: str) -> list[int]:
    """Parse "137,138" or "136-138" into a list of 1-based bar numbers."""
    bars: list[int] = []
    for part in str(text or "").replace(" ", "").split(","):
        if not part:
            continue
        start, separator, end = part.partition("-")
        if separator:
            bars.extend(range(int(start), int(end) + 1))
        else:
            bars.append(int(part))
    return bars


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--tab", help="Tab id in the library")
    source.add_argument("--file", help="GP5 file path")
    parser.add_argument(
        "--bars", required=True, help='1-based bars, e.g. "137,138" or "136-138"'
    )
    parser.add_argument(
        "--reset-sync",
        action="store_true",
        help="Set SYNC and SIIRTO back to 0 after the edit (tab id only)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only report")
    args = parser.parse_args()

    try:
        path = (
            tab_edit.resolve_tab_gp5(args.tab)
            if args.tab
            else Path(args.file).expanduser()
        )
    except tab_edit.TabEditError as exc:
        raise SystemExit(f"Ei voitu avata: {exc}") from exc
    if not path.is_file():
        raise SystemExit(f"Tiedostoa ei löytynyt: {path}")

    song = tab_edit.read_song(path)
    try:
        stats = tab_edit.remove_bars(song, _parse_bars(args.bars))
    except tab_edit.TabEditError as exc:
        raise SystemExit(f"Ei voitu poistaa: {exc}") from exc

    summary = {
        "file": str(path),
        "tab_id": args.tab or None,
        **stats,
        "dry_run": bool(args.dry_run),
    }

    if args.dry_run:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    backup = tab_edit.backup_file(path, args.tab or path.stem)
    summary["backup"] = str(backup)
    try:
        tab_edit.save_song(path, song, stats["bars_after"])
    except Exception as exc:  # noqa: BLE001 - restore and report
        shutil.copy2(backup, path)
        raise SystemExit(
            f"Kirjoitus epäonnistui, alkuperäinen palautettu: {exc}"
        ) from exc

    if args.tab:
        notes_after = tab_edit.count_notes(tab_edit.read_song(path))
        with db.connection() as conn:
            conn.execute(
                "UPDATE tabs SET measure_count = ?, note_count = ? WHERE id = ?",
                (stats["bars_after"], notes_after, args.tab),
            )
        summary["notes_after"] = notes_after
        if args.reset_sync:
            meta = dict((db.get_tab(args.tab) or {}).get("meta") or {})
            meta["sync_offset_bars"] = 0.0
            db.update_tab_sync(args.tab, 0.0, meta)
            summary["sync_reset"] = True

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
