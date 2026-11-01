"""Tempo automation in a GP5 tab (v2.26).

alphaTab follows a tab's own tempo automation. Seek & Destroy changes tempo at
bars 113 (208 BPM) and 165 (140 BPM) — part of the song — so the viewer honours
it by default: a blanket strip made that tab unplayable on 1.11.2026. Whiplash
instead ramps 200 -> 160 by bar 6, which is why its TAB BPM field looked dead
(measured: BPM 100 vs 200 moved the cursor 3 bars instead of 75).

Ignoring the automation is therefore a per-tab choice stored in the tab's meta
(Tiedot → "Ohita tempoautomatiikka", default off). These tests cover the API
round trip and the viewer's two loading paths.
"""

from __future__ import annotations

from pathlib import Path

from app import config, db

ROOT = Path(__file__).resolve().parents[1]
APP_JS = (config.STATIC_DIR / "app.js").read_text(encoding="utf-8")


def _body(function_name: str) -> str:
    start = APP_JS.index(f"function {function_name}(")
    end = APP_JS.index("\n  }\n", start)
    return APP_JS[start:end]


def _make_tab(tab_id: str, *, title: str, artist: str = "Artist") -> None:
    track_id = db.create_track(
        title=title,
        artist=artist,
        source_type="import",
        source_ref=f"tempo-test:{tab_id}",
        fingerprint=f"tempo-test:{tab_id}",
        audio_path=None,
        duration_seconds=None,
    )
    db.create_tab(
        tab_id=tab_id,
        track_id=track_id,
        cache_key=f"tempo-test:{tab_id}",
        directory=f"tabs/{tab_id}",
        title=title,
        artist=artist,
        bpm=120.0,
        tuning="standard",
        time_signature="4/4",
        measure_count=4,
        note_count=8,
        audio_path="",
        meta={"source_type": "import", "files": {"gp5": "tab.gp5"}},
    )


def test_the_flag_round_trips_through_the_library_route(client, data_dir):
    _make_tab("tempo1", title="Ramp")
    on = client.post(
        "/api/tabs/tempo1/library", data={"ignore_tempo_automation": "true"}
    )
    assert on.status_code == 200
    assert on.json()["ignore_tempo_automation"] is True
    detail = client.get("/api/tabs/tempo1")
    assert detail.status_code == 200
    assert detail.json()["meta"]["ignore_tempo_automation"] is True

    off = client.post(
        "/api/tabs/tempo1/library", data={"ignore_tempo_automation": "false"}
    )
    assert off.status_code == 200
    assert off.json()["ignore_tempo_automation"] is False


def test_the_default_is_to_honour_the_automation(client, data_dir):
    _make_tab("tempo2", title="Song with tempo changes")
    summary = client.get("/api/tabs/tempo2").json()
    assert summary["meta"].get("ignore_tempo_automation") in (None, False)


def test_default_loading_keeps_the_byte_loader():
    """Unflagged tabs must load exactly as before (Seek & Destroy needs it)."""
    load_tab = APP_JS[APP_JS.index("async function loadTab(") :]
    load_tab = load_tab[: load_tab.index("\n  }\n")]
    assert "instance.load(bytes)" in load_tab
    assert "loadScoreForTab(instance, bytes, true)" in load_tab
    assert "if (ignoreAutomation)" in load_tab


def test_stripping_only_happens_on_the_opt_in_path():
    load = _body("loadScoreForTab")
    assert "if (ignoreAutomation) stripTempoAutomations(score);" in load
    for name in ("collectTempoAutomations", "noteTempoAutomations"):
        body = _body(name)
        assert "tempoAutomations.length" not in body
        assert ".splice(" not in body


def test_the_backing_track_length_stays_exactly_as_it_was():
    """A per-tab override leaked its length into the next tab (1.11.2026).

    The getter must keep only alphaTab's own fallback: score end while the
    score is known, audio.duration otherwise. No cross-tab state.
    """
    start = APP_JS.index("get backingTrackDuration()")
    getter = APP_JS[start : APP_JS.index("get playbackRate()", start)]
    assert "pendingScoreEnd" not in getter
    assert "if (scoreEnd > 0) return scoreEnd;" in getter
    assert "audio.duration" in getter


def test_the_start_tempo_survives_the_strip():
    """Clearing every list drops alphaTab to 120 BPM (verified in Node)."""
    body = _body("stripTempoAutomations")
    assert "const keep = index === 0 ? list[0] : null;" in body
    assert "list.length = keep ? 1 : 0" in body


def test_tiedot_says_what_happens():
    assert "Tempoautomatiikka" in APP_JS
    assert "ohjaa toistoa" in APP_JS
    assert "ohitettu tämän tabin asetuksella" in APP_JS
    assert "tempoAutomationsByTab.get(tab.id)" in APP_JS


def test_playback_chain_has_no_automation_code():
    for name in (
        "notatedTempo",
        "bpmDrift",
        "barDurationMs",
        "syncTimeMs",
        "scoreEndTimeMs",
        "seekTo",
        "syncPosition",
    ):
        body = _body(name)
        assert "tempoAutomation" not in body
        assert "renderScore" not in body
