"""Export the library tabs as GP5/MusicXML/MIDI with a manifest.

Usage:
    .venv\\Scripts\\python.exe scripts\\export_tabs.py "D:\\tabtool_files\\exports"
    .venv\\Scripts\\python.exe scripts\\export_tabs.py <out> --formats gp5 --zip
    .venv\\Scripts\\python.exe scripts\\export_tabs.py <out> --ids <tab_id> [--ids ...]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import bulk  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path, help="Output folder for the exported files")
    parser.add_argument(
        "--formats",
        default="gp5,musicxml,midi",
        help="Comma separated: gp5,musicxml,midi (default: all)",
    )
    parser.add_argument(
        "--ids",
        action="append",
        default=None,
        help="Export only these tab ids (repeatable). Default: whole library.",
    )
    parser.add_argument(
        "--zip",
        action="store_true",
        help="Also write <out>.zip next to the folder",
    )
    args = parser.parse_args()

    formats = tuple(
        part.strip().lower() for part in args.formats.split(",") if part.strip()
    )
    try:
        result = bulk.export_tabs(
            args.out,
            tab_ids=args.ids,
            formats=formats,
            make_zip=args.zip,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
