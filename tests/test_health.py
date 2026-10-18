"""Phase 0 smoke tests for the FastAPI shell."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import __version__
from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["app"] == "AI TabTool"
    assert payload["version"] == __version__


def test_version() -> None:
    response = client.get("/api/version")
    assert response.status_code == 200
    assert response.json() == {"version": __version__}


def test_public_config_has_no_secrets() -> None:
    response = client.get("/api/config")
    assert response.status_code == 200
    payload = response.json()
    assert payload["app"] == "AI TabTool"
    assert payload["version"] == __version__
    assert isinstance(payload["spotify_configured"], bool)
    assert isinstance(payload["max_upload_mb"], int)
    assert isinstance(payload["pipeline_version"], str)
    assert "spotify_client_id" not in payload
    assert "spotify_redirect_uri" not in payload


def test_display_shell() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "AI TABTOOL" in response.text
    assert f"v{__version__}" in response.text


def test_display_alias() -> None:
    response = client.get("/display")
    assert response.status_code == 200
    assert "AI TABTOOL" in response.text


def test_remote_shell() -> None:
    response = client.get("/remote")
    assert response.status_code == 200
    assert "Remote" in response.text
    assert f"v{__version__}" in response.text


def test_static_assets() -> None:
    css = client.get("/static/style.css")
    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]

    js = client.get("/static/app.js")
    assert js.status_code == 200
    assert "javascript" in js.headers["content-type"]

    icon = client.get("/favicon.ico")
    assert icon.status_code == 200
    assert "image/svg+xml" in icon.headers["content-type"]
