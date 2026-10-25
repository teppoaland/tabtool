"""User-adjustable settings (v2.02).

The Settings view (``/settings``) edits the values; the SQLite ``settings``
table stores them. The defaults live here and are served to every page, so no
value is duplicated in JavaScript and ``app.js`` can keep its own fallbacks in
sync through ``tests/test_settings.py``.

Everything in this module is plain data. Nothing writes to the playback chain
(``.clinerules/07-playback-frozen.md``): the count-in duration is only a number
that ``beginCountIn()`` reads when it draws its overlay.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

from fastapi import Body, FastAPI, HTTPException

from app import db

# Rendered in this order in the Settings view.
GROUPS: tuple[tuple[str, str], ...] = (
    ("playback", "Toisto"),
    ("lyrics", "Sanat"),
    ("view", "Näkymä"),
    ("ui", "Toiminnot näkyvissä"),
    ("remote", "Puhelin (REMOTE)"),
)


@dataclass(frozen=True)
class Setting:
    """One editable value: type, bounds, default and the UI label."""

    key: str
    group: str
    label: str
    kind: str  # "number" | "bool" | "choice"
    default: Any
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    unit: str = ""
    options: tuple[tuple[str, str], ...] = ()
    help: str = ""

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "key": self.key,
            "group": self.group,
            "label": self.label,
            "kind": self.kind,
            "default": self.default,
            "unit": self.unit,
            "help": self.help,
        }
        if self.minimum is not None:
            payload["min"] = self.minimum
        if self.maximum is not None:
            payload["max"] = self.maximum
        if self.step is not None:
            payload["step"] = self.step
        if self.options:
            payload["options"] = [
                {"value": value, "label": label} for value, label in self.options
            ]
        return payload



# The count-in numbers are the documented v1.55 defaults: five steps, one
# second each and a 250 ms "0". app.js has the same fallbacks (COUNT_IN_*).
FIELDS: tuple[Setting, ...] = (
    Setting(
        "countin.steps",
        "playback",
        "Lähtölaskennan askelmat",
        "number",
        5,
        minimum=1,
        maximum=12,
        step=1,
        help="Montako lukua lasketaan ennen soittoa (5 → 0).",
    ),
    Setting(
        "countin.step_ms",
        "playback",
        "Askeleen kesto",
        "number",
        1000,
        minimum=200,
        maximum=3000,
        step=50,
        unit="ms",
        help="Yhden luvun näyttöaika.",
    ),
    Setting(
        "countin.zero_ms",
        "playback",
        "Nollan kesto",
        "number",
        250,
        minimum=0,
        maximum=2000,
        step=50,
        unit="ms",
        help="Viimeisen 0-lukeman kesto ennen soiton alkua.",
    ),
    Setting(
        "countin.enabled",
        "playback",
        "Lähtölaskenta oletuksena päällä",
        "bool",
        True,
        help="TV-näkymän ON/OFF-kytkin ohittaa tämän; tämä on oletus.",
    ),
    Setting(
        "lyrics.scale",
        "lyrics",
        "Sanoitusrivin koko",
        "number",
        200,
        minimum=100,
        maximum=400,
        step=25,
        unit="%",
        help=(
            "Soiton aikana näkyvän sanoitusrivin koko. 100 % = entinen koko, "
            "200 % = tuplat (oletus). Pätee myös koko näytön tilaan."
        ),
    ),
    Setting(
        "lyrics.offset_px",
        "lyrics",
        "Sanoitusrivin nosto",
        "number",
        100,
        minimum=0,
        maximum=600,
        step=10,
        unit="px",
        help=(
            "Kuinka monta pikseliä sanoitusrivi nousee ruudun alareunasta "
            "koko näytön tilassa (0 = aivan alhaalla, oletus 100 px)."
        ),
    ),
    Setting(
        "lyrics.sneak",
        "lyrics",
        "Seuraavan rivin esikatselu (Sneak peek)",
        "bool",
        True,
        help=(
            "Näyttää seuraavan sanoitusrivin pienenä nykyisen rivin alla "
            "yhtä tahtia ennen sen alkua. Tilaa tarvitaan vain vähän."
        ),
    ),
    Setting(
        "lyrics.sneak_position",
        "lyrics",
        "Sneak peek -sijainti",
        "choice",
        "below",
        options=(
            ("below", "Nykyisen rivin alla"),
            ("above", "Nykyisen rivin yllä"),
        ),
        help=(
            "Kumpi järjestys sopii laulajalle: esikatselu nykyisen rivin alla "
            "vai sen yllä. Helppo testata molemmat."
        ),
    ),
    Setting(
        "view.stave",
        "view",
        "Näkymän oletus",
        "choice",
        "tab",
        options=(
            ("tab", "Tab"),
            ("tabmixed", "Auto"),
            ("scoretab", "Tab + nuotit"),
            ("score", "Nuotit"),
        ),
        help="Näkymä uudelle selaimelle; TV-näkymän valinta ohittaa tämän.",
    ),
    Setting("ui.nav_library", "ui", "LIBRARY-painike", "bool", True,
            help="Kirjaston ja generaattorin avaus."),
    Setting("ui.nav_remote", "ui", "REMOTE-linkki", "bool", True,
            help="Päänäkymän yläpalkin linkki puhelimeen."),
    Setting("ui.nav_api", "ui", "API-linkki", "bool", True,
            help="Linkki FastAPIn rajapintadokumentaatioon."),
    Setting("ui.fullscreen", "ui", "FULLSCREEN-painike", "bool", True,
            help="Tabin koko näytön tila."),
    Setting("ui.countin_switch", "ui", "COUNT-IN-kytkin", "bool", True,
            help="Lähtölaskennan ON/OFF-kytkin FULLSCREEN-painikkeen alla."),
    Setting("ui.view_select", "ui", "Näkymä-valinta", "bool", True,
            help="Tab / Auto / Tab + nuotit / Nuotit -valinta."),
    Setting("ui.track_toggles", "ui", "Raitavalinnat", "bool", True,
            help="Näytettävien raitojen painikkeet."),
    Setting("ui.variant", "ui", "VALITSE TÄMÄ", "bool", True,
            help="Sormitusversion valinta AI-tabeille."),
    Setting("ui.attach_audio", "ui", "LIITÄ AUDIO", "bool", True,
            help="Audion liittäminen tuotuun tabiin."),
    Setting("ui.section", "ui", "TEE TAB TÄSTÄ", "bool", True,
            help="Pätkän generointi nykyisestä kohdasta."),
    Setting("ui.rate", "ui", "Nopeus", "bool", True,
            help="Harjoittelunopeus 50–150 %."),
    Setting("ui.sync", "ui", "SYNC", "bool", True,
            help="Tabin hienokohdistus prosentteina."),
    Setting("ui.shift", "ui", "SIIRTO", "bool", True,
            help="Tabin siirto tahdeittain."),
    Setting("ui.align", "ui", "KOHDISTA", "bool", True,
            help="Osoittimen kohdistus nuottia klikkaamalla."),
    Setting("ui.bpm", "ui", "TAB BPM", "bool", True,
            help="Tabin tempon tallennus."),
    Setting("ui.export", "ui", "EXPORT-rivi", "bool", True,
            help="GP5-, MusicXML- ja MIDI-lataukset tabin alta."),
    Setting("remote.modes.add", "remote", "LISÄÄ-välilehti", "bool", True,
            help="Kappaleen lisääminen puhelimesta."),
    Setting("remote.modes.adjust", "remote", "SÄÄDÄ-välilehti", "bool", True,
            help="Kirjaston tietojen muokkaus puhelimesta."),
    Setting("remote.rate", "remote", "Nopeussäädin", "bool", True,
            help="Toiston nopeus puhelimessa."),
    Setting("remote.tracks", "remote", "Soitinten valinta", "bool", True,
            help="Soittimet, jotka tablatuurissa näytetään."),
)

_FIELDS: dict[str, Setting] = {field.key: field for field in FIELDS}


def _number(field: Setting, raw: Any) -> int | float:
    if isinstance(raw, bool) or raw is None:
        raise ValueError(f"{field.key} must be a number")
    try:
        number = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field.key} must be a number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field.key} must be a finite number")
    if field.minimum is not None and number < field.minimum:
        raise ValueError(f"{field.key} must be at least {field.minimum}")
    if field.maximum is not None and number > field.maximum:
        raise ValueError(f"{field.key} must be at most {field.maximum}")
    # Every current number field is a whole number; keep the stored JSON tiny.
    if float(number).is_integer():
        return int(number)
    return round(number, 3)


def _clean(field: Setting, raw: Any) -> Any:
    """Validate one incoming value; raise ValueError when it is not usable."""
    if field.kind == "bool":
        if not isinstance(raw, bool):
            raise ValueError(f"{field.key} must be true or false")
        return raw
    if field.kind == "choice":
        text = str(raw or "").strip()
        allowed = [value for value, _ in field.options]
        if text not in allowed:
            raise ValueError(f"{field.key} must be one of {', '.join(allowed)}")
        return text
    return _number(field, raw)


def read_values() -> dict[str, Any]:
    """Current values; an unreadable or out-of-range stored value falls back."""
    values: dict[str, Any] = {}
    for field in FIELDS:
        raw = db.get_setting(field.key)
        if raw is None:
            values[field.key] = field.default
            continue
        try:
            values[field.key] = _clean(field, json.loads(raw))
        except (ValueError, json.JSONDecodeError):
            values[field.key] = field.default
    return values


def write_values(patch: dict[str, Any]) -> dict[str, Any]:
    """Validate and persist a partial update; return every current value."""
    if not isinstance(patch, dict):
        raise ValueError("settings must be an object")
    cleaned: dict[str, Any] = {}
    for key, raw in patch.items():
        field = _FIELDS.get(key) if isinstance(key, str) else None
        if field is None:
            raise ValueError(f"unknown setting: {key}")
        cleaned[key] = _clean(field, raw)
    for key, value in cleaned.items():
        db.set_setting(key, json.dumps(value))
    return read_values()


def schema() -> dict[str, Any]:
    return {
        "groups": [{"key": key, "label": label} for key, label in GROUPS],
        "fields": [field.as_dict() for field in FIELDS],
    }




def install(app: FastAPI) -> None:
    """Register ``/api/settings``; the Settings view is a static page."""

    @app.get("/api/settings", tags=["settings"])
    def api_settings() -> dict[str, Any]:
        return {"values": read_values(), **schema()}

    @app.post("/api/settings", tags=["settings"])
    def api_save_settings(
        payload: dict[str, Any] = Body(...),
    ) -> dict[str, Any]:
        try:
            values = write_values(payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"values": values}


__all__ = [
    "FIELDS",
    "GROUPS",
    "Setting",
    "install",
    "read_values",
    "schema",
    "write_values",
]
