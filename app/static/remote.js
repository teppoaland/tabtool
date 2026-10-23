/* AI TabTool remote control (v1.83).
 *
 * The phone only sends commands and shows the state the TV reported. All
 * playback happens on the TV (remote-bridge.js), so this page never plays
 * audio and never touches tab data. The 150 px QR pairs a phone with the
 * current LAN address; it is hidden on narrow (phone) screens.
 */
(() => {
  "use strict";

  const REFRESH_MS = 1000;
  const LIBRARY_MS = 30000;

  const statusEl = document.getElementById("api-status");
  const detailEl = document.getElementById("api-version");
  const tvEl = document.getElementById("tv-status");
  const versionEl = document.getElementById("version-tag");
  const titleEl = document.getElementById("remote-title");
  const metaEl = document.getElementById("remote-meta");
  const playButton = document.getElementById("remote-play");
  const backButton = document.getElementById("remote-back");
  const forwardButton = document.getElementById("remote-forward");
  const seekSlider = document.getElementById("remote-seek");
  const rateSlider = document.getElementById("remote-rate");
  const rateReadout = document.getElementById("remote-rate-readout");
  const libraryEl = document.getElementById("remote-library");
  const libraryStatus = document.getElementById("remote-status");
  const pairEl = document.getElementById("remote-pair");
  const qrEl = document.getElementById("remote-qr");
  const pairUrlEl = document.getElementById("remote-url");
  const pairHintEl = document.getElementById("remote-hint");

  let state = null;
  let tvOnline = false;
  let tabs = [];
  let seeking = false;
  let rating = false;

  function formatTime(value) {
    const total = Math.max(0, Math.round(Number(value) || 0));
    const minutes = Math.floor(total / 60);
    const seconds = total % 60;
    return `${minutes}:${String(seconds).padStart(2, "0")}`;
  }

  function setStatus(text, ok) {
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.classList.toggle("status-ok", Boolean(ok));
    statusEl.classList.toggle("status-error", !ok);
  }

  function setLibraryStatus(text) {
    if (libraryStatus) libraryStatus.textContent = text;
  }

  async function send(action, value) {
    try {
      const response = await fetch("/api/remote/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, value }),
        cache: "no-store",
      });
      if (response.status === 401) {
        window.location.href = "/lan";
        return false;
      }
      return response.ok;
    } catch (error) {
      return false;
    }
  }

  function render() {
    const data = state || {};
    if (titleEl) titleEl.textContent = data.title || "–";
    if (metaEl) {
      const bar = data.bar ? `Tahti ${data.bar}` : "Tahti –";
      const bpm = data.bpm ? ` · ${Math.round(data.bpm * 10) / 10} BPM` : "";
      metaEl.textContent =
        `${bar} · ${formatTime(data.position)} / ${formatTime(data.duration)}${bpm}`;
    }
    const playing = Boolean(data.playing);
    if (playButton) {
      playButton.textContent = playing ? "PAUSE" : "PLAY";
      playButton.dataset.state = playing ? "playing" : "paused";
      // Red background while playback runs, so the phone shows the state at
      // a glance even before reading the label.
      playButton.classList.toggle("is-playing", playing);
    }
    if (seekSlider) {
      const duration = Number(data.duration) || 0;
      seekSlider.max = String(Math.max(0, duration));
      if (!seeking) {
        seekSlider.value = String(
          Math.min(Math.max(0, Number(data.position) || 0), duration || 0)
        );
      }
    }
    if (rateReadout) {
      rateReadout.textContent = `${((Number(data.rate) || 1) * 100).toFixed(1)}%`;
    }
    if (rateSlider && !rating && data.rate) {
      rateSlider.value = String(Number(data.rate));
    }
  }

  async function loadLanInfo() {
    if (!pairEl) return;
    try {
      const response = await fetch("/api/lan/info", { cache: "no-store" });
      if (!response.ok) return;
      const info = await response.json();
      pairEl.hidden = false;
      if (info.lan && info.remote_url) {
        if (qrEl) {
          qrEl.hidden = false;
          qrEl.src = `/api/lan/qr.svg?t=${Date.now()}`;
        }
        if (pairUrlEl) pairUrlEl.textContent = info.remote_url;
        if (pairHintEl) pairHintEl.textContent = "";
      } else {
        // Loopback-only start: a QR would not work on the phone, so show the
        // address and tell why it is not scannable.
        if (qrEl) qrEl.hidden = true;
        if (pairUrlEl) {
          pairUrlEl.textContent = info.ip ? `${info.ip}:${info.port}` : "–";
        }
        if (pairHintEl) {
          pairHintEl.textContent = "Palvelin kuuntelee vain tätä konetta.";
        }
      }
    } catch (error) {
      /* the status pill already tells about the connection */
    }
  }

  async function refresh() {
    try {
      const [health, remote] = await Promise.all([
        fetch("/api/health", { cache: "no-store" }),
        fetch("/api/remote/state", { cache: "no-store" }),
      ]);
      if (remote.status === 401) {
        window.location.href = "/lan";
        return;
      }
      if (!health.ok || !remote.ok) throw new Error(`HTTP ${remote.status}`);
      const healthData = await health.json();
      const remoteData = await remote.json();
      setStatus("Online", true);
      if (detailEl) detailEl.textContent = `${healthData.app} v${healthData.version}`;
      if (versionEl) versionEl.textContent = `v${healthData.version}`;
      const previousTab = state && state.tab_id;
      state = remoteData.state || {};
      tvOnline = Boolean(remoteData.tv_online);
      if (tvEl) {
        tvEl.textContent = tvOnline
          ? "TV: Online"
          : "TV: Offline · avaa TV-näkymä";
      }
      if ((state.tab_id || "") !== (previousTab || "")) renderLibrary();
      render();
    } catch (error) {
      setStatus("Offline", false);
      tvOnline = false;
      if (tvEl) tvEl.textContent = "TV: Offline · avaa TV-näkymä";
      render();
    }
  }

  function renderLibrary() {
    if (!libraryEl) return;
    const active = state && state.tab_id;
    libraryEl.textContent = "";
    for (const tab of tabs) {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "remote-item";
      if (tab.id === active) item.classList.add("is-active");
      const name = document.createElement("span");
      name.className = "remote-item-title";
      name.textContent = tab.title || "?";
      const meta = document.createElement("span");
      meta.className = "remote-item-meta";
      meta.textContent = [
        tab.artist,
        tab.bpm ? `${Math.round(Number(tab.bpm) * 10) / 10} BPM` : "",
        tab.measure_count ? `${tab.measure_count} bars` : "",
      ]
        .filter(Boolean)
        .join(" · ");
      item.append(name, meta);
      item.addEventListener("click", () => selectTab(tab.id));
      libraryEl.append(item);
    }
    if (!tabs.length) {
      const empty = document.createElement("p");
      empty.className = "muted";
      empty.textContent = "Kirjasto on tyhjä.";
      libraryEl.append(empty);
    }
  }

  async function loadLibrary() {
    try {
      const response = await fetch("/api/tabs?limit=200", { cache: "no-store" });
      if (response.status === 401) {
        window.location.href = "/lan";
        return;
      }
      if (!response.ok) return;
      const data = await response.json();
      tabs = Array.isArray(data) ? data.filter((tab) => !tab.archived) : [];
      renderLibrary();
    } catch (error) {
      /* the status pill already shows the offline state */
    }
  }

  async function selectTab(tabId) {
    if (!tabId) return;
    setLibraryStatus("");
    const ok = await send("select_tab", tabId);
    setLibraryStatus(ok ? "" : "Failed");
    if (ok) {
      window.setTimeout(refresh, 600);
      window.setTimeout(loadLibrary, 2500);
    }
  }

  if (playButton) {
    playButton.addEventListener("click", async () => {
      await send("toggle");
      window.setTimeout(refresh, 300);
    });
  }
  if (backButton) {
    backButton.addEventListener("click", async () => {
      await send("seek_rel", -5);
      window.setTimeout(refresh, 400);
    });
  }
  if (forwardButton) {
    forwardButton.addEventListener("click", async () => {
      await send("seek_rel", 5);
      window.setTimeout(refresh, 400);
    });
  }
  if (seekSlider) {
    seekSlider.addEventListener("input", () => {
      seeking = true;
    });
    const commitSeek = async () => {
      if (!seeking) return;
      seeking = false;
      await send("seek", Number(seekSlider.value));
      window.setTimeout(refresh, 300);
    };
    seekSlider.addEventListener("change", commitSeek);
    seekSlider.addEventListener("pointerup", commitSeek);
  }
  if (rateSlider) {
    rateSlider.addEventListener("input", () => {
      rating = true;
      if (rateReadout) {
        rateReadout.textContent = `${(Number(rateSlider.value) * 100).toFixed(1)}%`;
      }
    });
    rateSlider.addEventListener("change", async () => {
      rating = false;
      await send("rate", Number(rateSlider.value));
      window.setTimeout(refresh, 300);
    });
  }

  refresh();
  loadLibrary();
  loadLanInfo();
  window.setInterval(refresh, REFRESH_MS);
  window.setInterval(loadLibrary, LIBRARY_MS);
  window.setInterval(loadLanInfo, LIBRARY_MS);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) refresh();
  });
})();

