"""Import a folder of GP3/GP4/GP5/MusicXML tabs into the local library.

Usage:
    .venv\\Scripts\\python.exe scripts\\import_folder.py "D:\\tabtool_files\\imports"
    .venv\\Scripts\\python.exe scripts\\import_folder.py <folder> --no-recursive --force
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
    parser.add_argument("folder", type=Path, help="Folder with GP3/GP4/GP5/MusicXML files")
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Only look at the top level of the folder",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Import again even if the file was imported before",
    )
    args = parser.parse_args()

    try:
        result = bulk.import_folder(
            args.folder,
            recursive=not args.no_recursive,
            skip_existing=not args.force,
        )
    except NotADirectoryError:
        print(f"Not a folder: {args.folder}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
