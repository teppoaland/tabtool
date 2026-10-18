"""Download a ready-made GP5/MusicXML tab from a public URL.

The browser only sends the link; the server fetches the file so the tab can
be imported without saving it to the user's Downloads folder first. Only
public http(s) hosts are allowed (no loopback/private addresses) and the
download is size limited.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from pathlib import Path
from urllib.parse import (
    parse_qsl,
    unquote,
    urlencode,
    urljoin,
    urlparse,
    urlunparse,
)

import httpx

MAX_TAB_BYTES = 20 * 1024 * 1024
TIMEOUT_SECONDS = 30.0
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AI-TabTool"

HTML_CONTENT_TYPES = ("text/html", "application/xhtml+xml")
GP_MAGIC = b"\x18FICHIER GUITAR PRO"


class TabDownloadError(ValueError):
    """The tab could not be downloaded from the given URL."""


class TabDownloadTooLarge(TabDownloadError):
    """The downloaded file exceeds the import size limit."""


def _is_private_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    )


def ensure_public_url(url: str) -> str:
    """Validate that ``url`` points to a public http(s) host."""
    text = str(url or "").strip()
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise TabDownloadError("Anna GP5- tai MusicXML-linkki (http/https).")
    host = (parsed.hostname or "").strip()
    if not host:
        raise TabDownloadError("Linkistä puuttuu palvelin.")
    lowered = host.lower()
    if lowered == "localhost" or lowered.endswith(".localhost"):
        raise TabDownloadError("Paikallisia osoitteita ei sallita.")
    if _is_private_address(host):
        raise TabDownloadError("Paikallisia osoitteita ei sallita.")
    if ":" not in host:
        try:
            infos = socket.getaddrinfo(
                host,
                parsed.port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        except OSError as exc:
            raise TabDownloadError(f"Palvelinta {host} ei tavoitettu.") from exc
        for info in infos:
            address = str(info[4][0]).split("%")[0]
            if _is_private_address(address):
                raise TabDownloadError("Paikallisia osoitteita ei sallita.")
    return text


def _with_download_query(url: str) -> str:
    """Append ``?download`` to a tab page that returned HTML."""
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if "download" in query:
        return url
    query["download"] = ""
    return urlunparse(parsed._replace(query=urlencode(query)))


def _looks_like_html(data: bytes, content_type: str) -> bool:
    if any(value in content_type.lower() for value in HTML_CONTENT_TYPES):
        return True
    head = data.lstrip()[:32].lower()
    return head.startswith(b"<!doctype") or head.startswith(b"<html")


def _filename_from_response(
    headers: httpx.Headers,
    url: str,
    data: bytes,
) -> str:
    candidate = ""
    disposition = headers.get("content-disposition", "")
    if disposition:
        match = re.search(
            r"filename\*?=(?:UTF-8''|\")?([^\";]+)", disposition, re.IGNORECASE
        )
        if match:
            candidate = unquote(match.group(1)).strip().strip('"')
    if not candidate:
        candidate = unquote(Path(urlparse(url).path).name)
    candidate = Path(candidate).name if candidate else ""
    suffix = Path(candidate).suffix.lower()
    stem = Path(candidate).stem if candidate else "downloaded-tab"
    if suffix in {".gp5", ".gp4", ".gp3", ".gpx"} or data.startswith(GP_MAGIC):
        return f"{stem or 'tab'}.gp5"
    if suffix in {".musicxml", ".xml"}:
        return f"{stem or 'tab'}.musicxml"
    if data.lstrip().startswith(b"<"):
        return f"{stem or 'tab'}.musicxml"
    return f"{stem or 'tab'}.gp5"


def _fetch(client: httpx.Client, url: str) -> tuple[bytes, httpx.Headers, str]:
    current = url
    for _hop in range(6):
        try:
            with client.stream("GET", current) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise TabDownloadError(
                            "Lataus ohjasi eteenpäin ilman osoitetta."
                        )
                    # Redirect targets are validated too, so a public link
                    # cannot bounce the server into the local network.
                    current = ensure_public_url(urljoin(current, location))
                    continue
                if response.status_code >= 400:
                    raise TabDownloadError(
                        f"Lataus epäonnistui (HTTP {response.status_code})."
                    )
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > MAX_TAB_BYTES:
                        raise TabDownloadTooLarge(
                            "Tablatuuritiedosto on liian suuri "
                            f"(max {MAX_TAB_BYTES // (1024 * 1024)} MB)."
                        )
                    chunks.append(chunk)
                return b"".join(chunks), response.headers, str(response.url)
        except httpx.HTTPError as exc:
            raise TabDownloadError(f"Lataus epäonnistui: {exc}") from exc
    raise TabDownloadError("Liian monta uudelleenohjausta.")


def download_tab_bytes(url: str) -> tuple[bytes, str]:
    """Fetch a tab file and return ``(data, filename)``.

    gprotab.net (and similar sites) serve an HTML tab page; the actual file
    is behind a ``?download`` parameter, so an HTML response is retried once
    with that parameter added.
    """
    target = ensure_public_url(url)
    with httpx.Client(
        follow_redirects=False,
        timeout=TIMEOUT_SECONDS,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
    ) as client:
        data, headers, final_url = _fetch(client, target)
        content_type = headers.get("content-type", "")
        if _looks_like_html(data, content_type):
            retry_url = _with_download_query(target)
            if retry_url != target:
                data, headers, final_url = _fetch(client, retry_url)
                content_type = headers.get("content-type", "")
        if not data:
            raise TabDownloadError("Ladattu tiedosto on tyhjä.")
        if _looks_like_html(data, content_type):
            raise TabDownloadError(
                "Linkki palautti HTML-sivun. Käytä suoraa GP5/MusicXML-"
                "latauslinkkiä."
            )
        return data, _filename_from_response(headers, final_url, data)
