"""GP5/MusicXML link download helpers."""

from __future__ import annotations

import httpx
import pytest

from app import tab_download

GP_BYTES = b"\x18FICHIER GUITAR PRO v5.10\x00\x00"


def test_rejects_non_http_and_private_hosts() -> None:
    for url in (
        "",
        "file:///C:/secret.gp5",
        "http://127.0.0.1/tab.gp5",
        "http://localhost/tab.gp5",
        "http://192.168.1.10/tab.gp5",
        "http://10.0.0.5/tab.gp5",
    ):
        with pytest.raises(tab_download.TabDownloadError):
            tab_download.ensure_public_url(url)


def test_accepts_public_address(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        tab_download,
        "socket",
        type(
            "FakeSocket",
            (),
            {
                "getaddrinfo": staticmethod(
                    lambda *args, **kwargs: [
                        (2, 1, 6, "", ("93.184.216.34", 443))
                    ]
                ),
                "SOCK_STREAM": 1,
            },
        ),
    )
    assert (
        tab_download.ensure_public_url("https://example.com/tabs/song.gp5")
        == "https://example.com/tabs/song.gp5"
    )


def test_download_query_is_added_once() -> None:
    assert (
        tab_download._with_download_query("https://example.com/tabs/song")
        == "https://example.com/tabs/song?download="
    )
    already = "https://example.com/tabs/song?download"
    assert tab_download._with_download_query(already) == already


def test_filename_detection() -> None:
    headers = httpx.Headers({})
    assert (
        tab_download._filename_from_response(
            headers, "https://example.com/en/tabs/wasp/song", GP_BYTES
        )
        == "song.gp5"
    )
    xml = b"<?xml version=\"1.0\"?><score-partwise/>"
    assert (
        tab_download._filename_from_response(
            headers, "https://example.com/song.musicxml", xml
        )
        == "song.musicxml"
    )
    disposition = httpx.Headers(
        {"content-disposition": 'attachment; filename="My Song.gp5"'}
    )
    assert (
        tab_download._filename_from_response(
            disposition, "https://example.com/download", GP_BYTES
        )
        == "My Song.gp5"
    )


def test_download_retries_html_page_with_download_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_fetch(client, url):  # noqa: ANN001 - test double
        calls.append(url)
        if len(calls) == 1:
            return (
                b"<!DOCTYPE html><html></html>",
                httpx.Headers({"content-type": "text/html"}),
                url,
            )
        return (
            GP_BYTES,
            httpx.Headers({"content-type": "application/octet-stream"}),
            url,
        )

    monkeypatch.setattr(tab_download, "_fetch", fake_fetch)
    monkeypatch.setattr(
        tab_download, "ensure_public_url", lambda url: url.strip()
    )
    data, filename = tab_download.download_tab_bytes(
        "https://example.com/en/tabs/metallica/whiplash"
    )
    assert data == GP_BYTES
    assert filename == "whiplash.gp5"
    assert calls[0].endswith("/whiplash")
    assert calls[1].endswith("/whiplash?download=")


def test_download_rejects_html_without_download_parameter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_fetch(client, url):  # noqa: ANN001 - test double
        return (
            b"<html><body>login</body></html>",
            httpx.Headers({"content-type": "text/html"}),
            url,
        )

    monkeypatch.setattr(tab_download, "_fetch", fake_fetch)
    monkeypatch.setattr(
        tab_download, "ensure_public_url", lambda url: url.strip()
    )
    with pytest.raises(tab_download.TabDownloadError):
        tab_download.download_tab_bytes(
            "https://example.com/tabs/song?download"
        )
