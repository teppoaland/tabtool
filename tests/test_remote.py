"""LAN remote control, QR pairing and the optional LAN-PIN gate (v1.82)."""

from __future__ import annotations

import sys
import time
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from app import config, remote
from app.main import app


@pytest.fixture()
def hub() -> Iterator[remote.RemoteHub]:
    instance = app.state.remote_hub
    instance.reset()
    yield instance
    instance.reset()


@pytest.fixture()
def api_client(data_dir, hub) -> TestClient:  # noqa: ANN001 - pytest fixture
    return TestClient(app)


def test_remote_command_roundtrip(api_client: TestClient, hub: remote.RemoteHub) -> None:
    first = api_client.post("/api/remote/command", json={"action": "toggle"})
    assert first.status_code == 202
    seq = first.json()["seq"]
    second = api_client.post(
        "/api/remote/command", json={"action": "seek", "value": 12.5}
    )
    assert second.json()["seq"] == seq + 1

    payload = api_client.get(f"/api/remote/commands?since={seq}").json()
    assert payload["seq"] == seq + 1
    assert payload["reset"] is False
    assert [entry["action"] for entry in payload["commands"]] == ["seek"]
    assert payload["commands"][0]["value"] == 12.5

    empty = api_client.get(f"/api/remote/commands?since={seq + 1}").json()
    assert empty["commands"] == []


def test_commands_signal_reset_after_restart(
    api_client: TestClient, hub: remote.RemoteHub
) -> None:
    api_client.post("/api/remote/command", json={"action": "play"})
    payload = api_client.get("/api/remote/commands?since=999").json()
    assert payload["reset"] is True
    assert payload["commands"] == []


def test_commands_can_be_primed_without_replay(
    api_client: TestClient, hub: remote.RemoteHub
) -> None:
    api_client.post("/api/remote/command", json={"action": "seek", "value": 30})
    payload = api_client.get(
        "/api/remote/commands?since=9007199254740991"
    ).json()
    assert payload["reset"] is True
    assert payload["commands"] == []
    assert payload["seq"] >= 1


def test_remote_bridge_does_not_replay_old_commands() -> None:
    source = (config.STATIC_DIR / "remote-bridge.js").read_text(encoding="utf-8")
    assert "primeSequence" in source
    assert "9007199254740991" in source


@pytest.mark.parametrize(
    "payload",
    [
        {"action": "rewind"},
        {"action": "rate", "value": 2.0},
        {"action": "seek", "value": -1},
        {"action": "select_tab", "value": "../etc/passwd"},
        {"action": "select_tab", "value": ""},
        {"action": "seek", "value": "not-a-number"},
    ],
)
def test_invalid_commands_are_rejected(api_client: TestClient, payload: dict) -> None:
    response = api_client.post("/api/remote/command", json=payload)
    assert response.status_code == 422


def test_command_must_be_an_object(api_client: TestClient) -> None:
    response = api_client.post("/api/remote/command", json=[1, 2, 3])
    assert response.status_code == 422


def test_state_roundtrip(api_client: TestClient, hub: remote.RemoteHub) -> None:
    response = api_client.post(
        "/api/remote/state",
        json={
            "tab_id": "abc-123",
            "title": "Seek & Destroy",
            "playing": True,
            "position": 12.3,
            "duration": 414.7,
            "bar": 7,
            "rate": 1.25,
            "bpm": 142,
            "visible": True,
        },
    )
    assert response.status_code == 204

    state = api_client.get("/api/remote/state").json()
    assert state["tv_online"] is True
    assert state["state"]["tab_id"] == "abc-123"
    assert state["state"]["playing"] is True
    assert state["state"]["bar"] == 7
    assert state["state"]["rate"] == 1.25
    assert state["state"]["bpm"] == 142


def test_tv_offline_without_report(api_client: TestClient, hub: remote.RemoteHub) -> None:
    state = api_client.get("/api/remote/state").json()
    assert state["tv_online"] is False
    assert state["state"] == {}


def test_state_rejects_bad_values(api_client: TestClient) -> None:
    negative = api_client.post(
        "/api/remote/state", json={"position": -5, "duration": 10}
    )
    assert negative.status_code == 422
    bad_tab = api_client.post("/api/remote/state", json={"tab_id": "a b"})
    assert bad_tab.status_code == 422


def test_lan_info_is_loopback_by_default(api_client: TestClient) -> None:
    info = api_client.get("/api/lan/info").json()
    assert info["lan"] is False
    assert info["remote_url"] is None
    assert info["pin_required"] is False


def test_qr_requires_lan_mode(api_client: TestClient) -> None:
    assert api_client.get("/api/lan/qr.svg").status_code == 404


def test_qr_uses_current_lan_address(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config, "HOST", "0.0.0.0")
    monkeypatch.setattr(remote, "lan_ip", lambda: "192.168.1.50")

    response = api_client.get("/api/lan/qr.svg")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert "<svg" in response.text
    # Standalone SVG needs the namespace; without it <img> shows a broken icon.
    assert 'xmlns="http://www.w3.org/2000/svg"' in response.text

    info = api_client.get("/api/lan/info").json()
    base = f"http://192.168.1.50:{config.PORT}"
    assert info["lan"] is True
    assert info["remote_url"] == f"{base}/remote"
    assert info["pair_url"] == f"{base}/remote"
    assert "127.0.0.1" not in info["pair_url"]


def test_pair_url_carries_session_token_with_pin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "HOST", "0.0.0.0")
    monkeypatch.setattr(config, "LAN_PIN", "1234")
    monkeypatch.setattr(remote, "lan_ip", lambda: "192.168.1.50")

    url = remote.pair_url()
    assert url is not None
    assert url.endswith(f"/lan?t={remote.PAIR_TOKEN}")
    assert "1234" not in url


def test_pin_token_is_hashed() -> None:
    token = remote.pin_token("1234")
    assert token != "1234"
    assert token == remote.pin_token("1234")
    assert token != remote.pin_token("4321")


def test_pin_gate_blocks_lan_clients(
    data_dir, monkeypatch: pytest.MonkeyPatch
) -> None:  # noqa: ANN001 - pytest fixture
    monkeypatch.setattr(config, "LAN_PIN", "1234")
    gate = TestClient(app, client=("192.168.1.50", 50000))

    assert gate.get("/api/remote/state").status_code == 401
    assert gate.get("/api/health").status_code == 200
    assert gate.get("/static/style.css").status_code == 200

    wrong = gate.post("/lan", data={"pin": "0000"}, follow_redirects=False)
    assert wrong.status_code == 401
    assert "Väärä PIN." in wrong.text

    login = gate.post("/lan", data={"pin": "1234"}, follow_redirects=False)
    assert login.status_code == 303
    assert login.headers["location"] == "/remote"
    assert gate.get("/api/remote/state").status_code == 200


def test_pair_token_logs_in(
    data_dir, monkeypatch: pytest.MonkeyPatch
) -> None:  # noqa: ANN001 - pytest fixture
    monkeypatch.setattr(config, "LAN_PIN", "1234")
    gate = TestClient(app, client=("192.168.1.50", 50001))

    response = gate.get(f"/lan?t={remote.PAIR_TOKEN}", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/remote"
    assert gate.get("/api/remote/state").status_code == 200


def test_loopback_skips_pin(data_dir, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(config, "LAN_PIN", "1234")
    loop = TestClient(app)
    assert loop.get("/api/remote/state").status_code == 200


def test_connect_page_is_gone(api_client: TestClient) -> None:
    assert api_client.get("/connect").status_code == 404


def test_remote_page_has_pairing_block(api_client: TestClient) -> None:
    response = api_client.get("/remote")
    assert response.status_code == 200
    assert 'id="remote-qr"' in response.text
    assert 'width="150"' in response.text
    assert 'height="150"' in response.text


def test_tv_stays_online_between_background_reports(
    api_client: TestClient, hub: remote.RemoteHub
) -> None:
    hub.report({"playing": False})
    hub._state_ts = time.monotonic() - 20  # type: ignore[attr-defined]
    payload = api_client.get("/api/remote/state").json()
    assert payload["tv_online"] is True


def test_remote_js_does_not_disable_play_when_tv_is_offline() -> None:
    source = (config.STATIC_DIR / "remote.js").read_text(encoding="utf-8")
    assert "playButton.disabled = !tvOnline" not in source
    assert "playButton.disabled = jobActive" in source
    assert '"Offline-TV"' in source


def test_remote_library_is_sorted_by_artist() -> None:
    js = (config.STATIC_DIR / "remote.js").read_text(encoding="utf-8")
    assert "function sortTabs" in js
    assert '${String(tab.artist || "")} ${String(tab.title' in js
    assert "tabs = sortTabs(" in js


def test_remote_library_uses_the_page_scrollbar() -> None:
    css = (config.STATIC_DIR / "style.css").read_text(encoding="utf-8")
    block = css[css.index(".remote-library {"):]
    block = block[: block.index("}")]
    assert "max-height" not in block
    assert "overflow-y" not in block


def test_remote_js_does_not_reference_removed_forward_button() -> None:
    """v1.98: the +5 s button is gone; render() must not name it.

    A leftover `if (forwardButton)` inside the strict-mode IIFE threw a
    ReferenceError on every render, so the Toisto slider never updated and
    stayed at the left edge.
    """
    html = (config.STATIC_DIR / "remote.html").read_text(encoding="utf-8")
    js = (config.STATIC_DIR / "remote.js").read_text(encoding="utf-8")
    assert 'id="remote-forward"' not in html
    assert "forwardButton" not in js


def test_remote_play_button_turns_red_while_playing() -> None:
    js = (config.STATIC_DIR / "remote.js").read_text(encoding="utf-8")
    css = (config.STATIC_DIR / "style.css").read_text(encoding="utf-8")
    assert 'classList.toggle("is-playing", playing)' in js
    assert "#remote-play.is-playing" in css


def test_remote_page_has_one_state_aware_connection_indicator(
    api_client: TestClient,
) -> None:
    response = api_client.get("/remote")
    assert response.status_code == 200
    assert 'id="api-status"' in response.text
    # v1.97: the verbose TV hint and the second TV label are gone. The one
    # pill shows Online / Offline / Offline-TV by state, so a brief API
    # failure cannot claim that the TV view is closed.
    assert 'id="tv-hint"' not in response.text
    assert 'id="tv-status"' not in response.text
    js = (config.STATIC_DIR / "remote.js").read_text(encoding="utf-8")
    assert '"Offline-TV"' in js
    assert '"Offline"' in js


def test_remote_page_has_modes_and_forms(api_client: TestClient) -> None:
    response = api_client.get("/remote")
    assert response.status_code == 200
    for token in (
        'id="mode-play"',
        'id="mode-add"',
        'id="mode-adjust"',
        'id="panel-play"',
        'id="panel-add"',
        'id="panel-adjust"',
        'id="add-form"',
        'id="add-youtube"',
        'id="add-gp5-url"',
        'id="add-gp5-file"',
        'id="adjust-form"',
    ):
        assert token in response.text


def test_remote_state_reports_job_active(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(remote, "jobs_running", lambda: True)
    payload = api_client.get("/api/remote/state").json()
    assert payload["job_active"] is True


def test_job_creation_blocked_while_playing(
    api_client: TestClient, hub: remote.RemoteHub
) -> None:
    hub.report({"playing": True})
    response = api_client.post(
        "/api/jobs", data={"youtube_url": "https://youtu.be/abc"}
    )
    assert response.status_code == 409
    assert "Pysäytä soitto" in response.json()["detail"]


def test_job_creation_blocked_while_job_running(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(remote, "jobs_running", lambda: True)
    response = api_client.post(
        "/api/tabs/import",
        files={"file": ("tab.gp5", b"data", "application/octet-stream")},
    )
    assert response.status_code == 409
    assert "Tabia luodaan jo" in response.json()["detail"]


def test_play_command_blocked_while_job_running(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(remote, "jobs_running", lambda: True)
    blocked = api_client.post("/api/remote/command", json={"action": "toggle"})
    assert blocked.status_code == 409
    # Seeking is harmless and stays allowed.
    allowed = api_client.post("/api/remote/command", json={"action": "seek", "value": 5})
    assert allowed.status_code == 202


def test_remote_js_enforces_one_operation_at_a_time() -> None:
    source = (config.STATIC_DIR / "remote.js").read_text(encoding="utf-8")
    assert "Pysäytä soitto ennen lisäystä." in source
    assert "Tabia luodaan jo" in source
    assert "job_active" in source


def test_lan_enabled_reads_uvicorn_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "HOST", "127.0.0.1")
    monkeypatch.setattr(
        sys, "argv", ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0"]
    )
    assert remote.lan_enabled() is True


def test_lan_disabled_for_loopback_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "HOST", "127.0.0.1")
    monkeypatch.setattr(
        sys, "argv", ["python", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1"]
    )
    assert remote.lan_enabled() is False


# === Track selection (v2.02) =============================================


def test_track_command_roundtrip(
    api_client: TestClient, hub: remote.RemoteHub
) -> None:
    response = api_client.post(
        "/api/remote/command", json={"action": "track", "value": 2}
    )
    assert response.status_code == 202
    seq = response.json()["seq"]
    payload = api_client.get(f"/api/remote/commands?since={seq - 1}").json()
    assert payload["commands"] == [{"seq": seq, "action": "track", "value": 2}]


@pytest.mark.parametrize("value", [-1, 32, 1.5, "two", None, True])
def test_track_command_rejects_a_bad_index(
    api_client: TestClient, value: object
) -> None:
    response = api_client.post(
        "/api/remote/command", json={"action": "track", "value": value}
    )
    assert response.status_code == 422


def test_state_reports_the_track_list(
    api_client: TestClient, hub: remote.RemoteHub
) -> None:
    response = api_client.post(
        "/api/remote/state",
        json={
            "tab_id": "abc-123",
            "tracks": [
                {"index": 0, "name": "Guitar", "visible": True},
                {"index": 3, "name": "Bass", "visible": False},
                {"index": -1, "name": "Bad", "visible": True},
                {"index": 99, "name": "Bad", "visible": True},
                {"index": 2, "name": "x" * 80, "visible": True},
                {"index": "1", "name": "Bad", "visible": True},
                "nonsense",
            ],
        },
    )
    assert response.status_code == 204
    state = api_client.get("/api/remote/state").json()["state"]
    tracks = state["tracks"]
    assert [track["index"] for track in tracks] == [0, 3, 2]
    assert tracks[0]["visible"] is True
    assert tracks[1]["visible"] is False
    assert len(tracks[2]["name"]) == remote.MAX_TRACK_NAME


def test_state_without_tracks_stays_quiet(api_client: TestClient) -> None:
    response = api_client.post("/api/remote/state", json={"tab_id": "abc-123"})
    assert response.status_code == 204
    state = api_client.get("/api/remote/state").json()["state"]
    assert "tracks" not in state


def test_track_command_is_not_a_playback_gate() -> None:
    """Only play/toggle are refused while a job runs; track selection is not."""
    source = (config.STATIC_DIR / "remote-bridge.js").read_text(encoding="utf-8")
    assert 'action === "track"' in source
    assert "toggleTrack" in (
        config.STATIC_DIR / "remote.js"
    ).read_text(encoding="utf-8")

