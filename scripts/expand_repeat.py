"""Write a repeated block out as real bars so the tab matches the recording.

Why: the viewer's clock is the *notated* timeline (`scoreEndTimeMs()` is
computed from the master bars). alphaTab expands repeats only at playback
time, so a GP5 that says "bar 2 ×17" made the score end 15 bars early and no
SIIRTO could align it. This script materialises the repeat: the block is
written `--times` times in total, the repeat marks are removed and the
following bars are renumbered, so the tab and the audio run 1:1.

The original GP5 is copied to `data/backups/<id>-<timestamp>/` first and the
written file is validated by reading it back.

Usage:
    .venv\\\\Scripts\\\\python.exe scripts\\\\expand_repeat.py --tab <id> --bar 2 --times 17 --dry-run
    .venv\\\\Scripts\\\\python.exe scripts\\\\expand_repeat.py --tab <id> --bar 2 --times 17 --reset-sync
    .venv\\\\Scripts\\\\python.exe scripts\\\\expand_repeat.py --file song.gp5 --bar 2 --times 17
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config, db, tab_edit  # noqa: E402


def _read_song(path: Path):
    """Read a GP5 file: UTF-8 first, cp1252 for older exports."""
    import guitarpro

    try:
        return guitarpro.parse(str(path), encoding="utf-8")
    except UnicodeDecodeError:
        return guitarpro.parse(str(path), encoding="cp1252")


def _resolve(args: argparse.Namespace) -> tuple[Path, str]:
    if args.file:
        path = Path(args.file).expanduser()
        if not path.is_file():
            raise SystemExit(f"Tiedostoa ei löytynyt: {path}")
        return path, path.stem

    tab = db.get_tab(args.tab)
    if tab is None:
        raise SystemExit(f"Tabia ei löytynyt: {args.tab}")
    meta = dict(tab.get("meta") or {})
    files = meta.get("files") if isinstance(meta.get("files"), dict) else {}
    name = str(files.get("gp5") or "")
    if not name:
        raise SystemExit(f"Tabilla {args.tab} ei ole GP5-tiedostoa.")
    directory = db.resolve_under_data(str(tab.get("directory") or ""))
    path = (directory / name).resolve()
    if path.parent != directory.resolve() or not path.is_file():
        raise SystemExit(f"GP5-tiedostoa ei löytynyt: {name}")
    return path, args.tab


def _backup(path: Path, key: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = Path(config.DATA_DIR) / "backups" / f"{key}-{stamp}"
    target.mkdir(parents=True, exist_ok=True)
    destination = target / path.name
    shutil.copy2(path, destination)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--tab", help="Tab id in the library")
    source.add_argument("--file", help="GP5 file path")
    parser.add_argument("--bar", type=int, required=True, help="1-based bar to repeat")
    parser.add_argument(
        "--times", type=int, required=True, help="How many times the bar is played"
    )
    parser.add_argument(
        "--close-bar",
        type=int,
        default=None,
        help="1-based end of the repeated block (default: the repeat mark)",
    )
    parser.add_argument(
        "--keep-text",
        action="store_true",
        help="Keep the beat texts in the copied bars too",
    )
    parser.add_argument(
        "--reset-sync",
        action="store_true",
        help="Set SYNC and SIIRTO back to 0 after the edit (tab id only)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only report")
    args = parser.parse_args()

    path, key = _resolve(args)
    song = _read_song(path)
    notes_before = tab_edit.count_notes(song)

    try:
        stats = tab_edit.expand_repeat(
            song,
            bar=args.bar,
            times=args.times,
            close_bar=args.close_bar,
            keep_text=args.keep_text,
        )
    except tab_edit.TabEditError as exc:
        raise SystemExit(f"Ei voitu laajentaa: {exc}") from exc

    summary = {
        "file": str(path),
        "tab_id": args.tab or None,
        "bars_before": stats["bars_before"],
        "bars_after": stats["bars_after"],
        "plays": stats["plays"],
        "notes_before": notes_before,
        "notes_after": notes_before + stats["notes_added"],
        "dry_run": bool(args.dry_run),
    }

    if args.dry_run:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    backup = _backup(path, key)
    summary["backup"] = str(backup)

    import guitarpro

    temporary = path.with_name(path.name + ".tmp")
    try:
        guitarpro.write(song, str(temporary), encoding="utf-8")
        os.replace(temporary, path)
        check = _read_song(path)
        if len(check.measureHeaders) != stats["bars_after"]:
            raise ValueError("tahtimäärä ei täsmää kirjoituksen jälkeen")
        if any(
            header.isRepeatOpen or (header.repeatClose or -1) >= 0
            for header in check.measureHeaders
        ):
            raise ValueError("toistomerkintöjä jäi tiedostoon")
    except Exception as exc:  # noqa: BLE001 - restore and report
        temporary.unlink(missing_ok=True)
        shutil.copy2(backup, path)
        raise SystemExit(
            f"Kirjoitus epäonnistui, alkuperäinen palautettu: {exc}"
        ) from exc

    if args.tab:
        notes_after = tab_edit.count_notes(check)
        with db.connection() as conn:
            conn.execute(
                "UPDATE tabs SET measure_count = ?, note_count = ? WHERE id = ?",
                (len(check.measureHeaders), notes_after, args.tab),
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
