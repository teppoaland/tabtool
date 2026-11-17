"""Latest GitHub release check for PianoCapture (notify only, no auto-update).

The Windows launcher has its own check for the tray balloon; the web UI uses
this module through ``GET /api/piano/update``. Results are cached for an hour
so a page reload does not hit the GitHub API every time, and any failure
(offline, rate limit) means "no notice" rather than an error.
"""

from __future__ import annotations

import json
import time
import urllib.request

from piano import __version__

RELEASES_API = "https://api.github.com/repos/teppoaland/tabtool/releases?per_page=100"
ASSET_PREFIX = "PianoCapture-Setup"
RELEASE_URL = "https://github.com/teppoaland/tabtool/releases/tag/"
CACHE_SECONDS = 3600.0
TIMEOUT_SECONDS = 5.0

_cache: dict[str, object] = {"at": 0.0, "value": None, "checked": False}


def _version_tuple(text: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in str(text or "").strip().lstrip("vV").split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        if digits:
            parts.append(int(digits))
    return tuple(parts)


def _is_newer(candidate: str, current: str) -> bool:
    left = _version_tuple(candidate)
    right = _version_tuple(current)
    length = max(len(left), len(right))
    return left + (0,) * (length - len(left)) > right + (0,) * (length - len(right))


def _fetch_latest() -> dict[str, str] | None:
    request = urllib.request.Request(
        RELEASES_API,
        headers={
            "User-Agent": "PianoCapture",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        releases = json.loads(response.read().decode("utf-8"))
    if not isinstance(releases, list):
        return None
    for release in releases:
        if not isinstance(release, dict):
            continue
        assets = release.get("assets") or []
        if not any(
            str(asset.get("name", "")).startswith(ASSET_PREFIX)
            for asset in assets
            if isinstance(asset, dict)
        ):
            continue
        tag = str(release.get("tag_name", "")).strip()
        if tag:
            return {"tag": tag, "url": RELEASE_URL + tag}
    return None


def _result(latest: dict[str, str] | None) -> dict[str, object]:
    tag = (latest or {}).get("tag")
    return {
        "current": __version__,
        "latest": tag,
        "url": (latest or {}).get("url"),
        "available": bool(tag) and _is_newer(str(tag), __version__),
    }


def status(force: bool = False) -> dict[str, object]:
    """Return the cached update state, refreshing it at most once an hour."""
    now = time.monotonic()
    if not force and _cache["checked"] and now - float(_cache["at"]) < CACHE_SECONDS:
        return _result(_cache["value"])  # type: ignore[arg-type]

    latest: dict[str, str] | None
    try:
        latest = _fetch_latest()
    except Exception:  # noqa: BLE001 - offline or rate limited: no notice
        latest = None
    _cache.update(at=now, value=latest, checked=True)
    return _result(latest)
