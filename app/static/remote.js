/* AI TabTool remote control (v1.89).
 *
 * Three modes, one operation at a time:
 *   SOITA  – transport + library selection
 *   LISÄÄ  – YouTube (+ optional GP5 link/file) -> job -> library
 *   SÄÄDÄ  – library basics (name, tuning, lock, archive)
 *
 * The phone only sends commands; playback happens on the TV page
 * (remote-bridge.js). The server enforces the same "one operation at a time"
 * rule with 409 responses, so a stale tab cannot bypass it.
 */
(() => {
  "use strict";

  const REFRESH_MS = 1000;
  const JOB_POLL_MS = 1500;
  const LIBRARY_MS = 30000;

  const STATUS_TEXT = {
    queued: "Queued",
    downloading: "Downloading audio…",
    separating: "Separating stems…",
    transcribing: "Transcribing guitar…",
    building: "Building tab…",
    ready: "Ready",
    failed: "Failed",
  };

  const byId = (id) => document.getElementById(id);

  const statusEl = byId("api-status");
  const detailEl = byId("api-version");
  const versionEl = byId("version-tag");

  const titleEl = byId("remote-title");
  const metaEl = byId("remote-meta");
  const playButton = byId("remote-play");
  const backButton = byId("remote-back");
  const seekSlider = byId("remote-seek");
  const rateSlider = byId("remote-rate");
  const rateReadout = byId("remote-rate-readout");
  const playNote = byId("play-note");
  const libraryEl = byId("remote-library");
  const libraryStatus = byId("remote-status");

  const pairEl = byId("remote-pair");
  const qrEl = byId("remote-qr");
  const pairUrlEl = byId("remote-url");
  const pairHintEl = byId("remote-hint");

  // v2.02: the instruments of the open tab. The mode buttons moved to the end
  // of the page, so these chips take their place at the top.
  const tracksCard = byId("remote-tracks");
  const trackList = byId("remote-track-list");
  const rateField = byId("remote-rate-field");

  const modePlay = byId("mode-play");
  const modeAdd = byId("mode-add");
  const modeAdjust = byId("mode-adjust");
  const panelPlay = byId("panel-play");
  const panelAdd = byId("panel-add");
  const panelAdjust = byId("panel-adjust");

  const addForm = byId("add-form");
  const addYoutube = byId("add-youtube");
  const addGp5Url = byId("add-gp5-url");
  const addGp5File = byId("add-gp5-file");
  const addSubmit = byId("add-submit");
  const addProgress = byId("add-progress");
  const addStatus = byId("add-status");
  const addNote = byId("add-note");

  const adjustList = byId("adjust-list");
  const adjustForm = byId("adjust-form");
  const adjustTitle = byId("adjust-title");
  const adjustName = byId("adjust-name");
  const adjustTuning = byId("adjust-tuning");
  const adjustLocked = byId("adjust-locked");
  const adjustArchived = byId("adjust-archived");
  const adjustStatus = byId("adjust-status");
  const adjustNote = byId("adjust-note");

  let state = null;
  let tvOnline = false;
  let jobActive = false;
  let localJob = null;
  let tabs = [];
  let seeking = false;
  let rating = false;
  let adjustTab = null;
  let activeMode = "play";
  let trackSignature = "";

  // Settings (v2.02). Everything is visible by default; a failed request or an
  // older server leaves these as they are.
  const features = {
    tracks: true,
    addMode: true,
    adjustMode: true,
    rate: true,
  };

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

  function setAddStatus(text, isError) {
    if (!addStatus) return;
    addStatus.textContent = text || "";
    addStatus.classList.toggle("is-error", Boolean(isError));
  }

  function setAdjustStatus(text, isError) {
    if (!adjustStatus) return;
    adjustStatus.textContent = text || "";
    adjustStatus.classList.toggle("is-error", Boolean(isError));
  }

  async function readError(response) {
    try {
      const data = await response.json();
      if (data && typeof data.detail === "string") return data.detail;
    } catch (error) {
      /* not JSON */
    }
    return `HTTP ${response.status}`;
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
      if (!response.ok) {
        setLibraryStatus(await readError(response));
        return false;
      }
      return true;
    } catch (error) {
      setLibraryStatus("Failed");
      return false;
    }
  }

  function setMode(mode) {
    activeMode = mode;
    const modes = {
      play: [modePlay, panelPlay],
      add: [modeAdd, panelAdd],
      adjust: [modeAdjust, panelAdjust],
    };
    for (const [key, [button, panel]] of Object.entries(modes)) {
      const active = key === mode;
      if (button) {
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-selected", active ? "true" : "false");
      }
      if (panel) panel.hidden = !active;
    }
    if (mode === "adjust") renderAdjustList();
  }

  // Hide the modes and the speed slider the Settings view turned off. The
  // active panel always falls back to SOITA, so a hidden tab cannot stay open.
  function applyFeatures() {
    if (modeAdd) modeAdd.hidden = !features.addMode;
    if (modeAdjust) modeAdjust.hidden = !features.adjustMode;
    if (rateField) rateField.hidden = !features.rate;
    if (
      (activeMode === "add" && !features.addMode) ||
      (activeMode === "adjust" && !features.adjustMode)
    ) {
      setMode("play");
    }
  }

  // The instrument chips of the open tab. The TV reports the track list and its
  // visible flags (remote-bridge.js); a tap sends the track command, which
  // clicks the same chip on the TV.
  function renderTracks() {
    if (!tracksCard || !trackList) return;
    const list = Array.isArray(state && state.tracks) ? state.tracks : [];
    const show =
      features.tracks && Boolean(state && state.tab_id) && list.length > 1;
    tracksCard.hidden = !show;
    if (!show) {
      trackList.textContent = "";
      trackSignature = "";
      return;
    }
    const signature = `${jobActive ? 1 : 0}|${list
      .map((track) => `${track.index}:${track.name}:${track.visible ? 1 : 0}`)
      .join("|")}`;
    if (signature === trackSignature) return;
    trackSignature = signature;
    trackList.textContent = "";
    for (const track of list) {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "remote-track";
      item.dataset.trackIndex = String(track.index);
      item.textContent = track.name || `Raita ${Number(track.index) + 1}`;
      item.setAttribute("aria-pressed", track.visible ? "true" : "false");
      item.title = `${item.textContent} · ${
        track.visible ? "näkyy tablatuurissa" : "piilotettu"
      }`;
      item.disabled = Boolean(jobActive);
      item.addEventListener("click", () => toggleTrack(track.index));
      trackList.append(item);
    }
  }

  async function toggleTrack(index) {
    if (jobActive) return;
    await send("track", Number(index));
    // The TV reports the new visible flag right after the click, so a short
    // delay is enough to redraw the chips from the real state.
    window.setTimeout(refresh, 300);
  }

  async function loadSettings() {
    try {
      const response = await fetch("/api/settings", { cache: "no-store" });
      if (!response.ok) return;
      const data = await response.json();
      const values = (data && data.values) || {};
      features.tracks = values["remote.tracks"] !== false;
      features.addMode = values["remote.modes.add"] !== false;
      features.adjustMode = values["remote.modes.adjust"] !== false;
      features.rate = values["remote.rate"] !== false;
      applyFeatures();
      renderTracks();
    } catch (error) {
      /* the defaults keep every control visible */
    }
  }

  function setAdjustEnabled(enabled) {
    if (!adjustForm) return;
    const locked = Boolean(adjustTab && adjustTab.locked);
    const unlockOnly = enabled && locked;
    for (const element of adjustForm.querySelectorAll("input, button")) {
      if (element === adjustLocked) {
        element.disabled = !enabled;
      } else {
        element.disabled = !enabled || unlockOnly;
      }
    }
  }

  function applyGuards(playing) {
    const canAdd = !jobActive && !playing;
    if (addSubmit) addSubmit.disabled = !canAdd;
    if (addNote) {
      if (jobActive) {
        addNote.textContent = "Tabia luodaan… odota valmistumista.";
        addNote.hidden = false;
      } else if (playing) {
        addNote.textContent = "Pysäytä soitto ennen lisäystä.";
        addNote.hidden = false;
      } else {
        addNote.hidden = true;
      }
    }
    const canAdjust = !jobActive && !playing;
    if (adjustNote) {
      if (jobActive) {
        adjustNote.textContent = "Tabia luodaan… odota valmistumista.";
        adjustNote.hidden = false;
      } else if (playing) {
        adjustNote.textContent = "Pysäytä soitto ennen säätämistä.";
        adjustNote.hidden = false;
      } else {
        adjustNote.hidden = true;
      }
    }
    setAdjustEnabled(canAdjust);
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
      playButton.disabled = jobActive;
    }
    if (backButton) backButton.disabled = jobActive;
    if (seekSlider) {
      seekSlider.disabled = jobActive;
      const duration = Number(data.duration) || 0;
      seekSlider.max = String(Math.max(0, duration));
      if (!seeking) {
        seekSlider.value = String(
          Math.min(Math.max(0, Number(data.position) || 0), duration || 0)
        );
      }
    }
    if (rateSlider) rateSlider.disabled = jobActive;
    if (rateReadout) {
      rateReadout.textContent = `${((Number(data.rate) || 1) * 100).toFixed(1)}%`;
    }
    if (rateSlider && !rating && data.rate) {
      rateSlider.value = String(Number(data.rate));
    }
    if (playNote) playNote.hidden = !jobActive;
    applyGuards(playing);
    renderTracks();
  }

  async function refresh() {
    let health = null;
    let remote = null;
    try {
      [health, remote] = await Promise.all([
        fetch("/api/health", { cache: "no-store" }),
        fetch("/api/remote/state", { cache: "no-store" }),
      ]);
    } catch (error) {
      /* a failed request is handled as offline below */
    }

    if (remote && remote.status === 401) {
      window.location.href = "/lan";
      return;
    }

    // One connection indicator with three states:
    //   Online     – this phone reaches the server and the TV reports
    //   Offline    – this phone cannot reach the server
    //   Offline-TV – the server is up but the TV page is not reporting
    // A failed request never claims that the TV view is closed; the old
    // hint did that whenever the phone briefly lost the API.
    if (!health || !health.ok) {
      setStatus("Offline", false);
      tvOnline = false;
      render();
      return;
    }

    try {
      const healthData = await health.json();
      if (detailEl) detailEl.textContent = `${healthData.app} v${healthData.version}`;
      if (versionEl) versionEl.textContent = `v${healthData.version}`;
    } catch (error) {
      /* the version text is optional */
    }

    if (!remote || !remote.ok) {
      setStatus("Online", true);
      return;
    }

    let remoteData;
    try {
      remoteData = await remote.json();
    } catch (error) {
      setStatus("Online", true);
      return;
    }

    const previousTab = state && state.tab_id;
    const wasBusy = jobActive;
    state = remoteData.state || {};
    tvOnline = Boolean(remoteData.tv_online);
    jobActive = Boolean(remoteData.job_active);
    setStatus(tvOnline ? "Online" : "Offline-TV", tvOnline);
    if ((state.tab_id || "") !== (previousTab || "")) renderLibrary();
    // A job that finished elsewhere (TV or another phone) also refreshes
    // the library here.
    if (wasBusy && !jobActive) loadLibrary();
    render();
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

  // Match the TV library: band name first, song title as the tiebreaker.
  function tabSortKey(tab) {
    return `${String(tab.artist || "")} ${String(tab.title || tab.id || "")}`.trim();
  }

  function sortTabs(list) {
    return list.slice().sort((left, right) =>
      tabSortKey(left).localeCompare(tabSortKey(right), "fi", {
        numeric: true,
        sensitivity: "base",
      })
    );
  }

  function renderLibrary() {
    if (!libraryEl) return;
    const active = state && state.tab_id;
    libraryEl.textContent = "";
    const visible = tabs.filter((tab) => !tab.archived);
    for (const tab of visible) {
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
    if (!visible.length) {
      const empty = document.createElement("p");
      empty.className = "muted";
      empty.textContent = "Kirjasto on tyhjä.";
      libraryEl.append(empty);
    }
  }

  function renderAdjustList() {
    if (!adjustList) return;
    adjustList.textContent = "";
    for (const tab of tabs) {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "remote-item";
      if (adjustTab && tab.id === adjustTab.id) item.classList.add("is-active");
      const name = document.createElement("span");
      name.className = "remote-item-title";
      name.textContent = tab.title || "?";
      const meta = document.createElement("span");
      meta.className = "remote-item-meta";
      meta.textContent = [
        tab.artist,
        tab.tuning_label,
        tab.locked ? "lukittu" : "",
        tab.archived ? "arkistoitu" : "",
      ]
        .filter(Boolean)
        .join(" · ");
      item.append(name, meta);
      item.addEventListener("click", () => selectAdjust(tab));
      adjustList.append(item);
    }
    if (!tabs.length) {
      const empty = document.createElement("p");
      empty.className = "muted";
      empty.textContent = "Kirjasto on tyhjä.";
      adjustList.append(empty);
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
      tabs = sortTabs(Array.isArray(data) ? data : []);
      renderLibrary();
      renderAdjustList();
      if (adjustTab) {
        const updated = tabs.find((tab) => tab.id === adjustTab.id);
        if (updated) selectAdjust(updated, true);
        else {
          adjustTab = null;
          if (adjustForm) adjustForm.hidden = true;
        }
      }
    } catch (error) {
      /* the status pill already shows the offline state */
    }
  }

  async function selectTab(tabId) {
    if (!tabId) return;
    setLibraryStatus("");
    const ok = await send("select_tab", tabId);
    if (!ok) return;
    window.setTimeout(refresh, 600);
    window.setTimeout(loadLibrary, 2500);
  }

  function selectAdjust(tab, silent) {
    adjustTab = tab;
    if (adjustForm) adjustForm.hidden = false;
    if (adjustTitle) adjustTitle.textContent = tab.title || "";
    if (adjustName) adjustName.value = tab.title_override || tab.title || "";
    if (adjustTuning) {
      adjustTuning.value = tab.tuning_override || tab.tuning_label || "";
    }
    if (adjustLocked) adjustLocked.checked = Boolean(tab.locked);
    if (adjustArchived) adjustArchived.checked = Boolean(tab.archived);
    if (!silent) setAdjustStatus("");
    renderAdjustList();
    setAdjustEnabled(!jobActive && !(state && state.playing));
  }

  async function submitAdjust(event) {
    event.preventDefault();
    if (!adjustTab) return;
    const data = new FormData();
    if (adjustTab.locked) {
      // A locked tab is read-only; the only allowed write is the unlock.
      data.append("locked", "false");
    } else {
      data.append("title", adjustName ? adjustName.value : "");
      data.append("locked", adjustLocked && adjustLocked.checked ? "true" : "false");
      data.append(
        "archived",
        adjustArchived && adjustArchived.checked ? "true" : "false"
      );
      const tuning = adjustTuning ? adjustTuning.value.trim() : "";
      if (tuning) data.append("tuning", tuning);
      else data.append("tuning_clear", "true");
    }
    const response = await fetch(`/api/tabs/${adjustTab.id}/library`, {
      method: "POST",
      body: data,
      cache: "no-store",
    });
    if (!response.ok) {
      setAdjustStatus(await readError(response), true);
      return;
    }
    setAdjustStatus("Tallennettu.");
    await loadLibrary();
    const updated = adjustTab ? tabs.find((tab) => tab.id === adjustTab.id) : null;
    if (updated) selectAdjust(updated, true);
  }

  async function submitAdd(event) {
    event.preventDefault();
    if (jobActive) {
      setAddStatus("Tabia luodaan jo – odota valmistumista.", true);
      return;
    }
    if (state && state.playing) {
      setAddStatus("Pysäytä soitto ennen lisäystä.", true);
      return;
    }
    const youtube = addYoutube ? addYoutube.value.trim() : "";
    const gp5Url = addGp5Url ? addGp5Url.value.trim() : "";
    const file = addGp5File && addGp5File.files ? addGp5File.files[0] : null;
    if (!youtube && !file) {
      setAddStatus("Anna YouTube-linkki tai GP5-tiedosto.", true);
      return;
    }
    if (gp5Url && !youtube) {
      setAddStatus("GP5-linkki tarvitsee YouTube-linkin.", true);
      return;
    }
    const data = new FormData();
    data.append("options", "{}");
    let endpoint = "/api/jobs";
    if (file) {
      endpoint = "/api/tabs/import";
      data.append("file", file);
      if (youtube) data.append("youtube_url", youtube);
    } else if (gp5Url) {
      data.append("gp5_url", gp5Url);
      data.append("youtube_url", youtube);
    } else {
      data.append("youtube_url", youtube);
    }
    setAddStatus(STATUS_TEXT.queued);
    if (addProgress) {
      addProgress.hidden = false;
      addProgress.value = 0;
    }
    let response;
    try {
      response = await fetch(endpoint, { method: "POST", body: data });
    } catch (error) {
      setAddStatus(STATUS_TEXT.failed, true);
      if (addProgress) addProgress.hidden = true;
      return;
    }
    if (!response.ok) {
      setAddStatus(await readError(response), true);
      if (addProgress) addProgress.hidden = true;
      return;
    }
    const payload = await response.json();
    if (payload && payload.id && payload.status) {
      pollJob(payload.id);
      return;
    }
    // A GP5 file without a YouTube link is imported directly (no audio job).
    setAddStatus(STATUS_TEXT.ready);
    if (addProgress) addProgress.hidden = true;
    await loadLibrary();
    refresh();
  }

  async function pollJob(jobId) {
    localJob = jobId;
    while (localJob === jobId) {
      await new Promise((resolve) => window.setTimeout(resolve, JOB_POLL_MS));
      let job = null;
      try {
        const response = await fetch(`/api/jobs/${jobId}`, { cache: "no-store" });
        if (!response.ok) break;
        job = await response.json();
      } catch (error) {
        continue;
      }
      const label = STATUS_TEXT[job.stage] || STATUS_TEXT[job.status] || job.status;
      setAddStatus(label);
      if (addProgress) {
        addProgress.hidden = false;
        addProgress.value = Number(job.progress) || 0;
      }
      if (job.status === "ready" || job.status === "failed") {
        localJob = null;
        if (addProgress) addProgress.hidden = true;
        if (job.status === "ready") {
          setAddStatus(STATUS_TEXT.ready);
          await loadLibrary();
          refresh();
        } else {
          setAddStatus(
            job.error ? `${STATUS_TEXT.failed}: ${job.error}` : STATUS_TEXT.failed,
            true
          );
        }
        break;
      }
    }
  }

  if (modePlay) modePlay.addEventListener("click", () => setMode("play"));
  if (modeAdd) modeAdd.addEventListener("click", () => setMode("add"));
  if (modeAdjust) modeAdjust.addEventListener("click", () => setMode("adjust"));
  if (addForm) addForm.addEventListener("submit", submitAdd);
  if (adjustForm) adjustForm.addEventListener("submit", submitAdjust);

  if (playButton) {
    playButton.addEventListener("click", async () => {
      if (jobActive) return;
      await send("toggle");
      window.setTimeout(refresh, 300);
    });
  }
  if (backButton) {
    backButton.addEventListener("click", async () => {
      if (jobActive) return;
      // Absolute seek to 0: the bridge sets the TV seek slider to the start,
      // so SIIRTO/SYNC/BPM corrections apply exactly as a user seek would.
      await send("seek", 0);
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
      if (jobActive) return;
      await send("seek", Number(seekSlider.value));
      window.setTimeout(refresh, 300);
    };
    seekSlider.addEventListener("change", commitSeek);
    seekSlider.addEventListener("pointerup", commitSeek);
  }
  // Speed: step=0.01 (1 % steps) removes the fine jitter, a ±5 % window
  // (10 % in total) around 100 % snaps to the neutral speed, and a double
  // tap on the readout always returns to exactly 100 %.
  const RATE_SNAP_PERCENT = 5;

  function showRate(value) {
    if (rateReadout) {
      rateReadout.textContent = `${(Number(value) * 100).toFixed(1)}%`;
    }
  }

  function setRateValue(value) {
    const number = Math.min(1.5, Math.max(0.5, Number(value) || 1));
    if (rateSlider) rateSlider.value = String(number);
    showRate(number);
  }

  if (rateSlider) {
    rateSlider.addEventListener("input", () => {
      rating = true;
      const percent = Math.round(Number(rateSlider.value) * 100);
      if (Math.abs(percent - 100) <= RATE_SNAP_PERCENT) {
        rateSlider.value = "1";
      }
      showRate(rateSlider.value);
    });
    rateSlider.addEventListener("change", async () => {
      rating = false;
      if (jobActive) return;
      await send("rate", Number(rateSlider.value));
      window.setTimeout(refresh, 300);
    });
  }

  if (rateReadout) {
    let lastTap = 0;
    rateReadout.addEventListener("pointerup", async () => {
      const now = Date.now();
      if (!lastTap || now - lastTap > 350) {
        lastTap = now;
        return;
      }
      lastTap = 0;
      setRateValue(1);
      if (jobActive) return;
      await send("rate", 1);
      window.setTimeout(refresh, 600);
    });
  }

  setMode("play");
  refresh();
  loadLibrary();
  loadLanInfo();
  loadSettings();
  window.setInterval(refresh, REFRESH_MS);
  window.setInterval(loadLibrary, LIBRARY_MS);
  window.setInterval(loadLanInfo, LIBRARY_MS);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      refresh();
      loadSettings();
    }
  });
})();
