"""Settings view, /api/settings and the show/hide switches (v2.02).

The Settings view is a static page and the values live in the SQLite
``settings`` table, so these tests cover three things:
  1. the API contract (defaults, saving, bounds),
  2. that the viewer reads the same numbers the server serves,
  3. that the switches stay outside the playback chain (rule 07).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import __version__, settings
from app.main import app

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "app" / "static" / "app.js"
INDEX_HTML = ROOT / "app" / "static" / "index.html"
REMOTE_HTML = ROOT / "app" / "static" / "remote.html"
REMOTE_JS = ROOT / "app" / "static" / "remote.js"
BRIDGE_JS = ROOT / "app" / "static" / "remote-bridge.js"
STYLE_CSS = ROOT / "app" / "static" / "style.css"

DEFAULTS = {field.key: field.default for field in settings.FIELDS}


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _code_only(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def _block(source: str, start: int) -> str:
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : index]
    raise AssertionError("unbalanced braces")


def _function_body(source: str, name: str) -> str:
    return _block(source, source.index(f"function {name}("))


# === API =================================================================


def test_defaults_are_served_with_their_bounds(client: TestClient) -> None:
    response = client.get("/api/settings")
    assert response.status_code == 200
    payload = response.json()
    assert payload["values"] == DEFAULTS
    assert [group["key"] for group in payload["groups"]] == [
        "playback",
        "view",
        "ui",
        "remote",
    ]
    kinds = {field["key"]: field["kind"] for field in payload["fields"]}
    assert kinds["countin.steps"] == "number"
    assert kinds["ui.rate"] == "bool"
    assert kinds["view.stave"] == "choice"
    steps = next(
        field for field in payload["fields"] if field["key"] == "countin.steps"
    )
    assert (steps["min"], steps["max"], steps["step"]) == (1, 12, 1)


def test_saving_persists_every_value(client: TestClient) -> None:
    patch = {
        "countin.steps": 8,
        "countin.step_ms": 500,
        "countin.zero_ms": 0,
        "countin.enabled": False,
        "view.stave": "score",
        "ui.rate": False,
        "remote.tracks": False,
    }
    response = client.post("/api/settings", json=patch)
    assert response.status_code == 200
    values = response.json()["values"]
    for key, value in patch.items():
        assert values[key] == value

    # A second client (another browser or the TV) reads the same values.
    other = TestClient(app)
    assert other.get("/api/settings").json()["values"] == values


@pytest.mark.parametrize(
    "patch",
    [
        {"countin.steps": 0},
        {"countin.steps": 13},
        {"countin.step_ms": 100},
        {"countin.zero_ms": 5000},
        {"countin.steps": "eight"},
        {"countin.enabled": "yes"},
        {"view.stave": "nope"},
        {"ui.rate": 1},
        {"nope.nope": True},
    ],
)
def test_invalid_values_are_rejected(client: TestClient, patch: dict) -> None:
    before = client.get("/api/settings").json()["values"]
    response = client.post("/api/settings", json=patch)
    assert response.status_code == 422
    assert client.get("/api/settings").json()["values"] == before


def test_non_object_body_is_rejected(client: TestClient) -> None:
    assert client.post("/api/settings", json=[1, 2]).status_code == 422


def test_every_switch_defaults_to_visible() -> None:
    """v2.02: a function is shown unless the user turns it off."""
    switches = [field for field in settings.FIELDS if field.kind == "bool"]
    assert len(switches) >= 20
    assert all(field.default is True for field in switches)


def test_default_count_in_duration_is_the_documented_5_25_s() -> None:
    """5 × 1000 ms + 250 ms = the count-in the viewer has always used."""
    total = (
        DEFAULTS["countin.steps"] * DEFAULTS["countin.step_ms"]
        + DEFAULTS["countin.zero_ms"]
    )
    assert total == 5250


def test_saved_count_in_duration_is_what_the_viewer_counts(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/settings",
        json={"countin.steps": 8, "countin.step_ms": 500, "countin.zero_ms": 0},
    )
    assert response.status_code == 200
    values = response.json()["values"]
    assert values["countin.steps"] * values["countin.step_ms"] + values[
        "countin.zero_ms"
    ] == 4000
    # The rest of the values stay at their defaults.
    for key, default in DEFAULTS.items():
        if key.startswith("countin.") and key != "countin.enabled":
            continue
        assert values[key] == default


def test_settings_page_is_served(client: TestClient) -> None:
    response = client.get("/settings")
    assert response.status_code == 200
    assert "SETTINGS" in response.text
    assert f"v{__version__}" in response.text
    assert "/static/settings.js" in response.text


def test_settings_pill_sits_after_remote_and_api() -> None:
    html = _text(INDEX_HTML)
    nav = html[html.index('class="nav"') :]
    nav = nav[: nav.index("</nav>")]
    remote_at = nav.index('href="/remote"')
    api_at = nav.index('href="/docs"')
    settings_at = nav.index('href="/settings"')
    assert remote_at < api_at < settings_at



# === Viewer wiring =======================================================


def test_count_in_defaults_match_the_server() -> None:
    """The viewer's fallbacks are exactly the defaults the Settings view shows."""
    source = _text(APP_JS)
    assert f"const COUNT_IN_FROM = {DEFAULTS['countin.steps']};" in source
    assert f"const COUNT_IN_STEP_MS = {DEFAULTS['countin.step_ms']};" in source
    assert f"const COUNT_IN_ZERO_MS = {DEFAULTS['countin.zero_ms']};" in source


def test_viewer_reads_the_settings_api() -> None:
    source = _text(APP_JS)
    assert 'const SETTINGS_URL = "/api/settings";' in source
    loader = _function_body(source, "loadRuntimeSettings")
    assert "SETTINGS_URL" in loader
    apply_body = _function_body(source, "applyRuntimeSettings")
    for key in ('"countin.steps"', '"countin.step_ms"', '"countin.zero_ms"'):
        assert key in apply_body
    # The countdown reads the numbers; it still never touches audio or alphaTab.
    count_in = _code_only(_function_body(source, "beginCountIn"))
    for name in ("countInSteps", "countInStepMs", "countInZeroMs"):
        assert name in count_in
    assert "audio" not in count_in
    assert "api." not in count_in


def test_settings_never_enter_the_alignment_math() -> None:
    """Rule 07: the clock, the seek inverse and the audio adapter stay closed."""
    source = _text(APP_JS)
    for name in (
        "syncTimeMs",
        "bpmDrift",
        "barDurationMs",
        "scoreEndTimeMs",
        "syncPosition",
        "seekTo",
        "togglePlayback",
    ):
        body = _function_body(source, name)
        for marker in ("applyRuntimeSettings", "SETTINGS_URL", "countInSteps"):
            assert marker not in body, f"{name} must not read the settings"
    media_handler = _block(source, source.index("const mediaHandler ="))
    assert "applyRuntimeSettings" not in media_handler
    assert "countIn" not in media_handler



def test_every_ui_switch_has_a_css_rule() -> None:
    source = _text(APP_JS)
    features = re.findall(r'^\s{4}"([a-z_]+)",$', source, flags=re.M)
    assert len(features) >= 16
    css = _text(STYLE_CSS)
    for feature in features:
        assert f"body.hide-ui-{feature}" in css, f"missing hide rule for {feature}"
    # The switches only add body classes; they never hide through inline styles.
    body = _function_body(source, "applyUiVisibility")
    assert "classList.toggle(`hide-ui-${feature}`" in body
    assert ".style" not in body


# === Remote view =========================================================


def test_remote_shows_instruments_where_the_modes_used_to_be() -> None:
    html = _text(REMOTE_HTML)
    tracks_at = html.index('id="remote-tracks"')
    play_at = html.index('id="panel-play"')
    modes_at = html.index('class="remote-modes"')
    adjust_panel_at = html.index('id="panel-adjust"')
    assert tracks_at < play_at, "instruments belong at the top"
    assert modes_at > adjust_panel_at, "mode buttons belong at the end"


def test_remote_bridge_reports_and_clicks_track_chips() -> None:
    source = _text(BRIDGE_JS)
    assert "function readTracks()" in source
    assert "tracks: readTracks()," in source
    assert "track-chip" in source
    assert 'action === "track"' in source
    # The bridge still only clicks the controls a user could click.
    assert "audio.currentTime =" not in _code_only(source)


def test_remote_hides_the_switched_off_functions() -> None:
    source = _text(REMOTE_JS)
    for key in (
        "remote.tracks",
        "remote.modes.add",
        "remote.modes.adjust",
        "remote.rate",
    ):
        assert f'"{key}"' in source
    assert "renderTracks" in source
    assert 'send("track"' in source
    assert 'id="remote-rate-field"' in _text(REMOTE_HTML)
