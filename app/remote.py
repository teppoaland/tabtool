"""LAN remote control (v1.86).

The phone opens ``/remote`` and sends commands; the TV page runs
``remote-bridge.js``, which polls the command queue and drives the existing
UI controls. Nothing in this module touches the playback chain: commands are
plain data and the bridge only clicks buttons that a user could click.

``start.bat`` binds all interfaces, so the QR code on ``/remote`` encodes the
current LAN address (never 127.0.0.1). When ``TABTOOL_LAN_PIN`` is set,
clients outside loopback must present the PIN cookie; the QR pairs a phone
without typing anything.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
import secrets
import socket
import sys
import threading
import time
from collections import deque
from typing import Any

import segno
from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from app import config
from app.config import is_loopback

# A queued command is meant for the TV that is open right now. Keeping the
# window short means a tab that was closed for a while does not suddenly
# start playing when it is reopened.
COMMAND_TTL_S = 60.0
COMMAND_QUEUE_SIZE = 50
# The phone shows "TV online" while the viewer keeps reporting. Browsers
# throttle timers in background tabs, so a background TV page reports less
# often; a short window would dim the phone controls for no real reason.
TV_ONLINE_S = 30.0

COOKIE_NAME = "tabtool_lan"
COOKIE_MAX_AGE = 30 * 24 * 3600
# The pairing token is regenerated on every server start, so a QR code from an
# earlier session stops working and no PIN is ever written into a URL.
PAIR_TOKEN = secrets.token_urlsafe(12)

ACTIONS = {"play", "pause", "toggle", "seek", "seek_rel", "rate", "select_tab"}
MAX_TAB_ID = 64
MAX_TITLE = 200
MAX_SECONDS = 24 * 3600.0

_PIN_ATTEMPTS: dict[str, deque[float]] = {}
_PIN_ATTEMPT_LIMIT = 10
_PIN_ATTEMPT_WINDOW_S = 60.0
_PIN_LOCK = threading.Lock()


class RemoteError(ValueError):
    """Raised when a remote payload is not acceptable."""


def _as_float(value: Any, name: str, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise RemoteError(f"{name} must be a number") from exc
    if number < low or number > high:
        raise RemoteError(f"{name} must be between {low} and {high}")
    return number


def _clean_tab_id(value: Any) -> str:
    text = str(value or "").strip()
    if not text or len(text) > MAX_TAB_ID:
        raise RemoteError("tab_id is invalid")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    if any(char not in allowed for char in text):
        raise RemoteError("tab_id is invalid")
    return text


def clean_command(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate one command from the phone; raise RemoteError when invalid."""
    action = str(payload.get("action") or "").strip().lower()
    if action not in ACTIONS:
        raise RemoteError(f"unknown action: {action or '-'}")
    value: float | str | None = None
    if action in {"play", "pause", "toggle"}:
        value = None
    elif action == "seek":
        value = _as_float(payload.get("value"), "value", 0.0, MAX_SECONDS)
    elif action == "seek_rel":
        value = _as_float(payload.get("value"), "value", -600.0, 600.0)
    elif action == "rate":
        value = _as_float(payload.get("value"), "value", 0.5, 1.5)
    elif action == "select_tab":
        value = _clean_tab_id(payload.get("value"))
    return {"action": action, "value": value}


def clean_state(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep the state the TV reports small, typed and bounded."""
    state: dict[str, Any] = {}
    tab_id = payload.get("tab_id")
    if isinstance(tab_id, str) and tab_id.strip():
        state["tab_id"] = _clean_tab_id(tab_id)
    title = payload.get("title")
    if isinstance(title, str):
        state["title"] = title.strip()[:MAX_TITLE]
    state["playing"] = bool(payload.get("playing"))
    state["position"] = _as_float(
        payload.get("position", 0), "position", 0.0, MAX_SECONDS
    )
    state["duration"] = _as_float(
        payload.get("duration", 0), "duration", 0.0, MAX_SECONDS
    )
    state["rate"] = _as_float(payload.get("rate", 1), "rate", 0.5, 1.5)
    bar = payload.get("bar")
    if isinstance(bar, (int, float)) and not isinstance(bar, bool):
        state["bar"] = max(0, min(int(bar), 100000))
    else:
        state["bar"] = None
    bpm = payload.get("bpm")
    if isinstance(bpm, (int, float)) and not isinstance(bpm, bool):
        state["bpm"] = round(float(bpm), 2)
    state["visible"] = bool(payload.get("visible"))
    return state


class RemoteHub:
    """Thread-safe command queue plus the last reported player state."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._seq = 0
        self._commands: deque[dict[str, Any]] = deque(maxlen=COMMAND_QUEUE_SIZE)
        self._state: dict[str, Any] = {}
        self._state_ts = 0.0

    def push(self, command: dict[str, Any]) -> int:
        with self._lock:
            self._seq += 1
            self._commands.append(
                {"seq": self._seq, "at": time.monotonic(), **command}
            )
            return self._seq

    def poll(self, since: int) -> dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            last = self._seq
            commands = [
                {
                    "seq": entry["seq"],
                    "action": entry["action"],
                    "value": entry["value"],
                }
                for entry in self._commands
                if entry["seq"] > since and now - entry["at"] <= COMMAND_TTL_S
            ]
            reset = since > last
        return {"seq": last, "reset": reset, "commands": commands}

    def report(self, state: dict[str, Any]) -> None:
        with self._lock:
            self._state = state
            self._state_ts = time.monotonic()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            age = time.monotonic() - self._state_ts if self._state_ts else None
            return {
                "seq": self._seq,
                "state": dict(self._state),
                "tv_online": bool(age is not None and age <= TV_ONLINE_S),
                "state_age": round(age, 2) if age is not None else None,
            }

    def reset(self) -> None:
        """Drop queued commands and the reported state (used by tests)."""
        with self._lock:
            self._seq = 0
            self._commands.clear()
            self._state = {}
            self._state_ts = 0.0


# === LAN discovery and pairing ===========================================


def lan_enabled() -> bool:
    """True when the server was started for the local network.

    ``start.bat`` sets ``TABTOOL_HOST=0.0.0.0`` before uvicorn starts, so
    ``config.HOST`` is enough there. A manual
    ``uvicorn app.main:app --host 0.0.0.0`` does not touch the environment,
    so the bind address is read from the command line as a fallback.
    """
    host = (config.HOST or "").strip().lower()
    if host in {"0.0.0.0", "::", "*"}:
        return True
    args = sys.argv[1:]
    for index, arg in enumerate(args):
        if arg == "--host" and index + 1 < len(args):
            return args[index + 1].strip().lower() in {"0.0.0.0", "::"}
        if arg.startswith("--host="):
            return arg.split("=", 1)[1].strip().lower() in {"0.0.0.0", "::"}
    return False


def lan_ip() -> str | None:
    """Return the address a phone on the same LAN should use."""
    override = os.getenv("TABTOOL_LAN_IP", "").strip()
    if override:
        return override
    # Connecting a UDP socket sends no packets but asks the routing table
    # which local address would be used; that avoids hard-coding an
    # interface name when the router hands out dynamic addresses.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        candidate = sock.getsockname()[0]
    except OSError:
        candidate = ""
    finally:
        sock.close()
    if candidate and not candidate.startswith("127."):
        return candidate
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = info[4][0]
            if not address.startswith("127."):
                return address
    except OSError:
        pass
    return None


def lan_url() -> str | None:
    """Base URL for the phone, or None when the server is loopback-only."""
    if not lan_enabled():
        return None
    address = lan_ip()
    if not address:
        return None
    return f"http://{address}:{config.PORT}"


def pair_url() -> str | None:
    """URL the QR code encodes (the PIN is never part of the URL)."""
    base = lan_url()
    if base is None:
        return None
    if config.LAN_PIN.strip():
        return f"{base}/lan?t={PAIR_TOKEN}"
    return f"{base}/remote"


def pin_token(pin: str) -> str:
    """Stable cookie value for a PIN; the PIN itself never leaves the server."""
    return hashlib.sha256(f"tabtool-lan:{pin}".encode("utf-8")).hexdigest()


def _cookie_ok(request: Request) -> bool:
    pin = config.LAN_PIN.strip()
    if not pin:
        return True
    value = request.cookies.get(COOKIE_NAME, "")
    return bool(value) and hmac.compare_digest(value, pin_token(pin))


def _gate_open(request: Request, path: str) -> bool:
    if not config.LAN_PIN.strip():
        return True
    client = request.client.host if request.client else None
    if is_loopback(client):
        return True
    if path in {"/api/health", "/lan", "/favicon.ico"}:
        return True
    if path.startswith("/static/"):
        return True
    return _cookie_ok(request)


def _set_pin_cookie(response: Response, pin: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        pin_token(pin),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )


def _too_many_attempts(client: str) -> bool:
    now = time.monotonic()
    with _PIN_LOCK:
        attempts = _PIN_ATTEMPTS.setdefault(client, deque())
        while attempts and now - attempts[0] > _PIN_ATTEMPT_WINDOW_S:
            attempts.popleft()
        return len(attempts) >= _PIN_ATTEMPT_LIMIT


def _record_attempt(client: str) -> None:
    with _PIN_LOCK:
        _PIN_ATTEMPTS.setdefault(client, deque()).append(time.monotonic())


def _login_page(error: str = "") -> str:
    message = f'<p class="pin-error" role="alert">{error}</p>' if error else ""
    return f"""<!doctype html>
<html lang="fi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <title>AI TabTool · LAN-PIN</title>
  <link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="/static/style.css?v={config.VERSION}">
</head>
<body>
  <header class="topbar">
    <div class="brand">
      <span class="brand-mark" aria-hidden="true">AT</span>
      <span class="brand-name">AI TABTOOL</span>
    </div>
  </header>
  <main class="shell">
    <section class="hero">
      <p class="kicker">LAN-PIN</p>
      <h1>AI TABTOOL</h1>
    </section>
    <form class="card pin-card" method="post" action="/lan">
      <label class="field">
        <span>LAN-PIN</span>
        <input type="password" name="pin" inputmode="numeric"
               autocomplete="current-password" autofocus required>
      </label>
      {message}
      <button class="primary" type="submit">JATKA</button>
    </form>
  </main>
</body>
</html>"""


def _login_redirect(pin: str) -> RedirectResponse:
    response = RedirectResponse("/remote", status_code=303)
    _set_pin_cookie(response, pin)
    return response


# === HTTP surface ========================================================


def install(app: FastAPI) -> None:
    """Register the LAN guard, remote endpoints and the pairing page."""
    hub = RemoteHub()
    app.state.remote_hub = hub

    @app.middleware("http")
    async def _lan_guard(request: Request, call_next):  # type: ignore[no-untyped-def]
        path = request.url.path
        if _gate_open(request, path):
            return await call_next(request)
        if path.startswith("/api/"):
            return JSONResponse({"detail": "LAN-PIN required"}, status_code=401)
        return HTMLResponse(_login_page("LAN-PIN vaaditaan."), status_code=401)

    @app.get("/lan", include_in_schema=False)
    def lan_page(request: Request, t: str = Query(default="")) -> Response:
        pin = config.LAN_PIN.strip()
        if not pin:
            return RedirectResponse("/remote", status_code=303)
        # The QR code carries a per-session token, so scanning it pairs the
        # phone without the PIN ever appearing in the URL.
        if t and hmac.compare_digest(t, PAIR_TOKEN):
            return _login_redirect(pin)
        if _cookie_ok(request):
            return RedirectResponse("/remote", status_code=303)
        return HTMLResponse(_login_page())

    @app.post("/lan", include_in_schema=False)
    def lan_login(request: Request, pin: str = Form(default="")) -> Response:
        expected = config.LAN_PIN.strip()
        if not expected:
            return RedirectResponse("/remote", status_code=303)
        client = request.client.host if request.client else "unknown"
        if _too_many_attempts(client):
            return HTMLResponse(_login_page("Liikaa yrityksiä."), status_code=429)
        if pin and hmac.compare_digest(pin.strip(), expected):
            return _login_redirect(expected)
        _record_attempt(client)
        return HTMLResponse(_login_page("Väärä PIN."), status_code=401)

    @app.get("/api/lan/info", tags=["system"], include_in_schema=False)
    def lan_info() -> dict[str, Any]:
        base = lan_url()
        return {
            "lan": base is not None,
            "host": config.HOST,
            "port": config.PORT,
            "ip": lan_ip(),
            "url": base,
            "remote_url": f"{base}/remote" if base else None,
            "pair_url": pair_url(),
            "pin_required": bool(config.LAN_PIN.strip()),
        }

    @app.get("/api/lan/qr.svg", include_in_schema=False)
    def lan_qr() -> Response:
        url = pair_url()
        if url is None:
            raise HTTPException(status_code=404, detail="LAN is not enabled")
        qr = segno.make(url, error="m")
        # svg_inline() leaves out xmlns because it is meant for inline HTML.
        # Served as image/svg+xml the SVG must be a standalone document or
        # the browser shows a broken image instead of the QR code.
        buffer = io.BytesIO()
        qr.save(
            buffer,
            kind="svg",
            scale=8,
            border=3,
            dark="#0b0f14",
            light="#f6f8fb",
            xmldecl=False,
        )
        return Response(
            content=buffer.getvalue(),
            media_type="image/svg+xml",
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/api/remote/state", tags=["remote"])
    def remote_state() -> dict[str, Any]:
        snapshot = hub.snapshot()
        snapshot["pin_required"] = bool(config.LAN_PIN.strip())
        return snapshot

    @app.post("/api/remote/state", status_code=204, tags=["remote"])
    async def remote_report(request: Request) -> Response:
        try:
            payload = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise HTTPException(status_code=422, detail="state must be JSON") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=422, detail="state must be an object")
        try:
            hub.report(clean_state(payload))
        except RemoteError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return Response(status_code=204)

    @app.post("/api/remote/command", status_code=202, tags=["remote"])
    async def remote_command(request: Request) -> dict[str, Any]:
        try:
            payload = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise HTTPException(status_code=422, detail="command must be JSON") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=422, detail="command must be an object")
        try:
            command = clean_command(payload)
        except RemoteError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"seq": hub.push(command)}

    @app.get("/api/remote/commands", tags=["remote"])
    def remote_commands(since: int = Query(default=0, ge=0)) -> dict[str, Any]:
        return hub.poll(since)

    if lan_enabled():
        address = lan_ip()
        if address:
            print(f"AI TabTool phone remote: http://{address}:{config.PORT}/remote")
        print(f"AI TabTool QR code:      http://127.0.0.1:{config.PORT}/remote")
        if not config.LAN_PIN.strip():
            print(
                "AI TabTool LAN: TABTOOL_LAN_PIN is empty - "
                "any device on the network can control the app."
            )


__all__ = [
    "RemoteHub",
    "RemoteError",
    "clean_command",
    "clean_state",
    "install",
    "lan_enabled",
    "lan_ip",
    "lan_url",
    "pair_url",
    "pin_token",
]
