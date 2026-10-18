/* AI TabTool TV view – Phase 2: generate, render and play tabs. */
(() => {
  "use strict";

  const STATUS_TEXT = {
    queued: "Queued",
    downloading: "Downloading audio…",
    separating: "Separating stems…",
    transcribing: "Transcribing guitar…",
    building: "Building tab…",
    ready: "Ready",
    failed: "Failed",
  };

  // Numeric fallbacks mirror alphaTab.StaveProfile in the vendored bundle.
  const STAVE_PROFILES = {
    tab: 3,
    tabmixed: 4,
    scoretab: 1,
    score: 2,
  };
  const STAVE_STORAGE_KEY = "tabtool:staveProfile";
  const TRACK_STORAGE_PREFIX = "tabtool:tracks:";
  const SYNC_LIMIT = 0.1;

  const form = document.getElementById("source-form");
  const fileInput = document.getElementById("file-input");
  const urlInput = document.getElementById("url-input");
  const tuningSelect = document.getElementById("tuning-select");
  const gridSelect = document.getElementById("grid-select");
  const quickCheckbox = document.getElementById("quick-checkbox");
  const regenerateCheckbox = document.getElementById("regenerate-checkbox");
  const generateButton = document.getElementById("generate-button");
  const statusEl = document.getElementById("job-status");
  const progressEl = document.getElementById("job-progress");
  const detailEl = document.getElementById("job-detail");
  const libraryEl = document.getElementById("library");

  const viewerSection = document.getElementById("viewer-section");
  const viewerEl = document.getElementById("alphaTab");
  const audio = document.getElementById("audio");
  const playButton = document.getElementById("play-button");
  const titleEl = document.getElementById("tab-title");
  const metaEl = document.getElementById("tab-meta");
  const staveSelect = document.getElementById("stave-select");
  const trackToggles = document.getElementById("track-toggles");
  const fullscreenButton = document.getElementById("fullscreen-button");
  const seekSlider = document.getElementById("seek-slider");
  const seekBack = document.getElementById("seek-back");
  const seekForward = document.getElementById("seek-forward");
  const timeCurrent = document.getElementById("time-current");
  const timeTotal = document.getElementById("time-total");
  const barReadout = document.getElementById("bar-readout");
  const sectionButton = document.getElementById("section-button");
  const sectionLength = document.getElementById("section-length");
  const sectionStatus = document.getElementById("section-status");
  const attachAudioButton = document.getElementById("attach-audio-button");
  const attachStatus = document.getElementById("attach-status");
  const rateSlider = document.getElementById("rate-slider");
  const rateReadout = document.getElementById("rate-readout");
  const syncSlider = document.getElementById("sync-slider");
  const syncReadout = document.getElementById("sync-readout");
  const syncStatus = document.getElementById("sync-status");
  const shiftInput = document.getElementById("shift-input");
  const bpmInput = document.getElementById("bpm-input");
  const bpmButton = document.getElementById("bpm-button");
  const bpmStatus = document.getElementById("bpm-status");
  const bpmField = bpmInput ? bpmInput.closest(".bpm-field") : null;
  const transport = document.querySelector(".transport");
  const gp5Input = document.getElementById("gp5-url-input");
  const gp5FileInput = document.getElementById("gp5-file-input");
  const makeMp3Checkbox = document.getElementById("make-mp3-checkbox");
  const searchModal = document.getElementById("search-modal");
  const openSearchButton = document.getElementById("open-search");
  const openSearchTopButton = document.getElementById("open-search-top");
  const closeSearchButton = document.getElementById("close-search");
  const libraryStatus = document.getElementById("library-status");
  const libraryCount = document.getElementById("library-count");
  const deleteDialog = document.getElementById("delete-dialog");
  const deleteDetail = document.getElementById("delete-detail");
  const deleteStatus = document.getElementById("delete-status");
  const deleteConfirm = document.getElementById("delete-confirm");
  const deleteCancel = document.getElementById("delete-cancel");
  const exportLinks = Array.from(
    document.querySelectorAll(".viewer-foot a[data-format]")
  );

  let api = null;
  let activeTab = null;
  let stream = null;
  let submitting = false;
  let allTracks = [];
  let visibleTrackIndexes = new Set();
  let sliderSeeking = false;
  let staveProfile = readStaveProfile();
  let syncDrift = 0;
  let syncOffsetBars = 0;
  let syncSaveTimer = null;
  let pendingDelete = null;

  function setPlayLabel(playing) {
    if (!playButton) return;
    playButton.textContent = playing ? "PAUSE" : "PLAY";
    playButton.dataset.state = playing ? "playing" : "paused";
  }

  function setLibraryStatus(text, isError) {
    if (!libraryStatus) return;
    libraryStatus.textContent = text;
    libraryStatus.classList.toggle("is-error", Boolean(isError));
  }

  function setDeleteStatus(text, isError) {
    if (!deleteStatus) return;
    deleteStatus.textContent = text;
    deleteStatus.classList.toggle("is-error", Boolean(isError));
  }

  function setSectionStatus(text) {
    if (sectionStatus) sectionStatus.textContent = text;
  }

  function setAttachStatus(text) {
    if (attachStatus) attachStatus.textContent = text;
  }

  function setBpmStatus(text, isError) {
    if (!bpmStatus) return;
    bpmStatus.textContent = text;
    bpmStatus.classList.toggle("is-error", Boolean(isError));
  }

  function setSyncStatus(text, isError) {
    if (!syncStatus) return;
    syncStatus.textContent = text;
    syncStatus.classList.toggle("is-error", Boolean(isError));
  }

  function bpmIsDirty() {
    if (!bpmInput || !activeTab) return false;
    const typed = Number(bpmInput.value);
    if (!Number.isFinite(typed) || typed <= 0) return false;
    const saved = Number(activeTab.bpm) || 0;
    return Math.abs(typed - saved) > 0.05;
  }

  // Fractional TAB BPM is applied as a playback correction: the GP5
  // stores an integer tempo, the decimal part is the real song tempo.
  function notatedTempo() {
    if (api && api.score && Number(api.score.tempo) > 0) {
      return Number(api.score.tempo);
    }
    const meta = (activeTab && activeTab.meta) || {};
    const saved = Number(meta.gp5_tempo);
    if (saved > 0) return saved;
    return Math.round(Number(activeTab && activeTab.bpm) || 0);
  }

  function bpmDrift() {
    if (!activeTab) return 0;
    const target = Number(activeTab.bpm) || 0;
    const notated = notatedTempo();
    if (target <= 0 || notated <= 0) return 0;
    return target / notated - 1;
  }

  // Red hint on the TAB BPM field until the typed value is saved.
  function updateBpmDirtyState() {
    if (!bpmField) return;
    bpmField.classList.toggle("is-dirty", bpmIsDirty());
  }

  function setPlaybackRate(value) {
    const rate = Math.min(1.5, Math.max(0.5, Number(value) || 1));
    audio.playbackRate = rate;
    try {
      audio.preservesPitch = true;
    } catch (error) {
      /* older browsers */
    }
    if (rateSlider && Math.abs(Number(rateSlider.value) - rate) > 0.0001) {
      rateSlider.value = String(rate);
    }
    if (rateReadout) {
      rateReadout.textContent = `${(rate * 100).toFixed(1)}%`;
    }
  }

  function normalizeSyncDrift(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return 0;
    return Math.min(SYNC_LIMIT, Math.max(-SYNC_LIMIT, number));
  }

  function setSyncDrift(value, options) {
    const settings = options || {};
    syncDrift = normalizeSyncDrift(value);
    const percent = syncDrift * 100;
    if (syncSlider && Math.abs(Number(syncSlider.value) - percent) > 0.001) {
      syncSlider.value = percent.toFixed(2);
    }
    if (syncReadout) {
      syncReadout.textContent = `${percent >= 0 ? "+" : ""}${percent.toFixed(2)}%`;
    }
    if (settings.sync !== false) syncPosition();
  }

  // Manual tab alignment: shift the tab timeline relative to the audio so a
  // hand-tuned correction stays in effect for the whole song.
  function barDurationMs() {
    let ticks = 0;
    if (api && api.score && Array.isArray(api.score.masterBars)) {
      const bars = api.score.masterBars;
      if (bars.length > 1) {
        ticks = Number(bars[1].start) - Number(bars[0].start);
      } else if (bars.length === 1) {
        const only = bars[0];
        if (typeof only.calculateDuration === "function") {
          ticks = Number(only.calculateDuration()) || 0;
        }
      }
    }
    const tempo = notatedTempo() || 120;
    if (ticks > 0) return (ticks * 60000) / (tempo * 960);
    return (4 * 60000) / tempo;
  }

  function setSyncOffsetBars(value, options) {
    const settings = options || {};
    const number = Number(value);
    // Quarter-bar steps (= one beat in 4/4); keeps the value human-sized.
    syncOffsetBars = Number.isFinite(number)
      ? Math.min(64, Math.max(-64, Math.round(number * 4) / 4))
      : 0;
    if (shiftInput && Number(shiftInput.value) !== syncOffsetBars) {
      shiftInput.value = String(syncOffsetBars);
    }
    if (settings.sync !== false) syncPosition(true);
  }

  function syncTimeMs() {
    const current = Number(audio.currentTime) || 0;
    const duration = Number.isFinite(audio.duration) ? audio.duration : 0;
    const base = current * 1000 * (1 + syncDrift + bpmDrift());
    const position = Math.max(0, base + syncOffsetBars * barDurationMs());
    return duration > 0 ? Math.min(position, duration * 1000) : position;
  }

  // End of the score timeline in milliseconds. alphaTab's external-media
  // clock maps the backing-track time onto the full score with the ratio
  // (scoreEnd / backingTrackDuration). If the reported backing track length
  // is the audio length and the score is longer, every feed of audio time is
  // stretched and the cursor runs ahead of the music. Returning the score's
  // own end here keeps that mapping 1:1, so only the explicit BPM/SYNC/SIIRTO
  // corrections in syncTimeMs() are applied.
  function scoreEndTimeMs() {
    if (api) {
      const cache = api.tickCache;
      if (cache) {
        const end = Number(cache.endTime);
        if (Number.isFinite(end) && end > 0) return end;
      }
      const end = Number(api.endTime);
      if (Number.isFinite(end) && end > 0) return end;
    }
    return 0;
  }

  async function persistSyncDrift() {
    if (!activeTab || !activeTab.id) return;
    const tabId = activeTab.id;
    if (syncSaveTimer) {
      window.clearTimeout(syncSaveTimer);
      syncSaveTimer = null;
    }
    const data = new FormData();
    data.append("drift", syncDrift.toFixed(4));
    data.append("offset_bars", String(syncOffsetBars));
    setSyncStatus("Tallennetaan…");
    try {
      const response = await fetch(`/api/tabs/${tabId}/sync`, {
        method: "POST",
        body: data,
      });
      if (!activeTab || activeTab.id !== tabId) return;
      if (!response.ok) {
        setSyncStatus(await readError(response), true);
        return;
      }
      const tab = await response.json();
      if (tab && tab.meta && typeof tab.meta === "object") {
        activeTab.meta = Object.assign({}, activeTab.meta, tab.meta);
      }
      setSyncStatus("Tallennettu");
      window.setTimeout(() => {
        if (syncStatus && syncStatus.textContent === "Tallennettu") {
          setSyncStatus("");
        }
      }, 1500);
    } catch (error) {
      setSyncStatus(error instanceof Error ? error.message : String(error), true);
    }
  }

  function setAudioAvailable(available) {
    if (playButton) {
      playButton.disabled = !available;
      playButton.title = available
        ? "Toista tai pysäytä audio. Koko näyttö avautuu toistettaessa; Esc palaa."
        : "Tälle tabille ei ole audiota. Tabi näytetään ilman toistoa.";
    }
    if (attachAudioButton) attachAudioButton.hidden = available;
    if (transport) transport.hidden = !available;
    if (!available) {
      audio.removeAttribute("src");
      audio.load();
      updateTransport();
    }
  }

  function formatTime(value) {
    const total = Math.max(0, Math.round(Number(value) || 0));
    const minutes = Math.floor(total / 60);
    const seconds = total % 60;
    return `${minutes}:${String(seconds).padStart(2, "0")}`;
  }

  function currentBarNumber() {
    if (api && api.score && Array.isArray(api.score.masterBars)) {
      const tick = Number(api.tickPosition);
      if (Number.isFinite(tick)) {
        const bars = api.score.masterBars;
        let index = 0;
        for (let i = 0; i < bars.length; i += 1) {
          if (tick >= (Number(bars[i].start) || 0)) index = i;
          else break;
        }
        return index + 1;
      }
    }
    const bpm = Number(activeTab && activeTab.bpm) || 0;
    if (bpm > 0) {
      return Math.floor(syncTimeMs() / 1000 / (240 / bpm)) + 1;
    }
    return null;
  }

  function updateTransport() {
    const duration = Number.isFinite(audio.duration) ? audio.duration : 0;
    if (seekSlider) {
      seekSlider.max = String(Math.max(0, duration));
      if (!sliderSeeking) {
        seekSlider.value = String(
          Math.min(Math.max(0, Number(audio.currentTime) || 0), duration || 0)
        );
      }
    }
    if (timeCurrent) timeCurrent.textContent = formatTime(audio.currentTime);
    if (timeTotal) timeTotal.textContent = formatTime(duration);
    if (barReadout) {
      const bar = currentBarNumber();
      barReadout.textContent = bar ? `Tahti ${bar}` : "Tahti –";
    }
  }

  function scrollScoreToCursor() {
    if (!viewerEl) return;
    const cursor =
      viewerEl.querySelector(".at-cursor-bar") ||
      viewerEl.querySelector(".at-cursor-beat");
    if (!cursor) return;
    const boxRect = viewerEl.getBoundingClientRect();
    const cursorRect = cursor.getBoundingClientRect();
    const factor = allTracks.length > 1 ? 0.42 : 0.34;
    const offset = Math.round(viewerEl.clientHeight * factor);
    const target =
      viewerEl.scrollTop + (cursorRect.top - boxRect.top) - offset;
    viewerEl.scrollTop = Math.max(0, target);
  }

  function seekTo(seconds) {
    if (!Number.isFinite(audio.duration) || audio.duration <= 0) return;
    clearPlaybackRange();
    const target = Math.min(
      Math.max(0, Number(seconds) || 0),
      audio.duration
    );
    audio.currentTime = target;
    syncPosition(true);
    updateTransport();
    window.setTimeout(scrollScoreToCursor, 80);
  }

  function seekBy(delta) {
    seekTo((Number(audio.currentTime) || 0) + delta);
  }

  function normalizeStaveProfile(value) {
    return Object.prototype.hasOwnProperty.call(STAVE_PROFILES, value)
      ? value
      : "tab";
  }

  function readStaveProfile() {
    try {
      return normalizeStaveProfile(localStorage.getItem(STAVE_STORAGE_KEY));
    } catch (error) {
      return "tab";
    }
  }

  function writeStaveProfile(value) {
    try {
      localStorage.setItem(STAVE_STORAGE_KEY, value);
    } catch (error) {
      /* storage disabled */
    }
  }

  function staveProfileValue(value) {
    const name = normalizeStaveProfile(value);
    if (window.alphaTab && alphaTab.StaveProfile) {
      switch (name) {
        case "scoretab":
          return alphaTab.StaveProfile.ScoreTab;
        case "score":
          return alphaTab.StaveProfile.Score;
        case "tabmixed":
          return alphaTab.StaveProfile.TabMixed;
        default:
          return alphaTab.StaveProfile.Tab;
      }
    }
    return STAVE_PROFILES[name];
  }

  function formatTimestamp(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    try {
      return date.toLocaleString("fi-FI", {
        dateStyle: "short",
        timeStyle: "short",
      });
    } catch (error) {
      return date.toLocaleString();
    }
  }

  function formatBpm(value) {
    const bpm = Number(value);
    if (!Number.isFinite(bpm) || bpm <= 0) return "";
    return Number.isInteger(bpm) ? String(bpm) : bpm.toFixed(1);
  }

  function libraryTooltip(tab) {
    const heading = tab.artist
      ? `${tab.artist} — ${tab.title}`
      : String(tab.title || tab.id);
    const parts = [
      heading,
      `${Number(tab.measure_count) || 0} tahtia · ` +
        `${Number(tab.note_count) || 0} nuottia · ` +
        `${formatBpm(tab.bpm)} BPM`,
    ];
    const created = formatTimestamp(tab.created_at);
    if (created) parts.push(`Lisätty ${created}`);
    if (tab.source_type) {
      const label =
        tab.source_type === "import"
          ? "tuotu tabi"
          : String(tab.source_type);
      parts.push(`Lähde: ${label}`);
    }
    parts.push(`ID: ${tab.id}`);
    return parts.join("\n");
  }

  function trackLabel(track, index) {
    const name = track && track.name ? String(track.name).trim() : "";
    return name || `Raita ${index + 1}`;
  }

  function renderTrackToggles() {
    if (!trackToggles) return;
    trackToggles.textContent = "";
    if (!allTracks.length) return;

    const labels = allTracks.map((track, index) => trackLabel(track, index));
    allTracks.forEach((track, index) => {
      const label = labels[index];
      const duplicate = labels.filter((item) => item === label).length > 1;
      const visible = visibleTrackIndexes.has(index);
      const button = document.createElement("button");
      button.type = "button";
      button.className = "track-chip";
      button.dataset.trackIndex = String(index);
      button.textContent = duplicate ? `${index + 1} · ${label}` : label;
      button.setAttribute("aria-pressed", visible ? "true" : "false");
      if (allTracks.length <= 1) {
        button.disabled = true;
        button.title = `${label} · tabissa on yksi raita.`;
      } else {
        button.title =
          `${label} · ${visible ? "näkyy" : "piilotettu"}. ` +
          `Klikkaa ${visible ? "piilottaaksesi" : "näyttääksesi"} raidan.`;
        button.addEventListener("click", () => toggleTrack(index));
      }
      trackToggles.append(button);
    });
  }

  function restoreTrackSelection() {
    visibleTrackIndexes = new Set(allTracks.map((_, index) => index));
    if (!activeTab || !allTracks.length) return;
    if (
      activeTab.meta &&
      activeTab.meta.source_type === "import" &&
      allTracks.length > 1
    ) {
      const guitarIndexes = allTracks
        .map((track, index) => ({
          index,
          name: track && track.name ? String(track.name) : "",
        }))
        .filter((track) => /guitar/i.test(track.name))
        .map((track) => track.index);
      visibleTrackIndexes = new Set(
        guitarIndexes.length ? guitarIndexes.slice(0, 2) : [0]
      );
    }
    try {
      const raw = localStorage.getItem(TRACK_STORAGE_PREFIX + activeTab.id);
      if (!raw) return;
      const stored = JSON.parse(raw);
      if (!Array.isArray(stored)) return;
      const valid = stored
        .map((value) => Number(value))
        .filter(
          (value) =>
            Number.isInteger(value) && value >= 0 && value < allTracks.length
        );
      if (valid.length) visibleTrackIndexes = new Set(valid);
    } catch (error) {
      /* ignore a broken stored selection */
    }
  }

  function persistTrackSelection() {
    if (!activeTab) return;
    try {
      localStorage.setItem(
        TRACK_STORAGE_PREFIX + activeTab.id,
        JSON.stringify(Array.from(visibleTrackIndexes).sort((a, b) => a - b))
      );
    } catch (error) {
      /* storage disabled */
    }
  }

  function syncPositionSoon(delay) {
    window.setTimeout(syncPosition, delay || 60);
  }

  function applyScrollOffset() {
    if (!api || !api.settings || !api.settings.player || !viewerEl) return;
    const height = viewerEl.clientHeight || 720;
    // Negative offset keeps the current system lower on screen so the
    // previous system stays visible above it.
    const factor = allTracks.length > 1 ? 0.42 : 0.34;
    api.settings.player.scrollOffsetY = -Math.round(height * factor);
  }

  function applyTrackSelection() {
    if (!api || !allTracks.length) return;
    const selected = allTracks.filter((_, index) =>
      visibleTrackIndexes.has(index)
    );
    if (!selected.length) return;
    if (typeof api.renderTracks === "function") {
      applyScrollOffset();
      api.renderTracks(selected);
      syncPositionSoon();
    }
  }

  function toggleTrack(index) {
    if (allTracks.length <= 1) return;
    if (visibleTrackIndexes.has(index)) {
      if (visibleTrackIndexes.size <= 1) return;
      visibleTrackIndexes.delete(index);
    } else {
      visibleTrackIndexes.add(index);
    }
    persistTrackSelection();
    renderTrackToggles();
    applyTrackSelection();
  }

  function applyStaveProfile(value, options) {
    const settings = options || {};
    staveProfile = normalizeStaveProfile(value);
    if (staveSelect) staveSelect.value = staveProfile;
    if (settings.persist !== false) writeStaveProfile(staveProfile);
    if (!api) return;
    try {
      api.settings.display.staveProfile = staveProfileValue(staveProfile);
      if (typeof api.updateSettings === "function") api.updateSettings();
      if (settings.render !== false && typeof api.render === "function") {
        api.render();
        syncPositionSoon();
      }
    } catch (error) {
      console.warn("view change failed", error);
    }
  }

  function viewerFullscreenActive() {
    if (!viewerSection) return false;
    return (
      document.fullscreenElement === viewerSection ||
      viewerSection.classList.contains("is-fullscreen")
    );
  }

  function applyDisplayScale() {
    if (!api) return;
    const active = viewerFullscreenActive();
    const viewport = window.innerWidth || 1280;
    const scale = active ? Math.min(2.4, Math.max(1, viewport / 1280)) : 1;
    try {
      api.settings.display.scale = scale;
      applyScrollOffset();
      if (typeof api.updateSettings === "function") api.updateSettings();
      if (typeof api.render === "function") api.render();
      syncPositionSoon(90);
    } catch (error) {
      console.warn("display scale failed", error);
    }
  }

  async function enterViewerFullscreen() {
    if (!viewerSection || viewerFullscreenActive()) return;
    if (
      document.fullscreenEnabled !== false &&
      typeof viewerSection.requestFullscreen === "function"
    ) {
      try {
        await viewerSection.requestFullscreen({ navigationUI: "hide" });
        return;
      } catch (error) {
        console.warn("fullscreen unavailable", error);
      }
    }
    viewerSection.classList.add("is-fullscreen");
    document.body.classList.add("viewer-fullscreen");
    setFullscreenButtonState();
    applyDisplayScale();
  }

  async function exitViewerFullscreen() {
    if (!viewerSection) return;
    if (document.fullscreenElement) {
      try {
        await document.exitFullscreen();
      } catch (error) {
        console.warn("fullscreen exit failed", error);
      }
    }
    viewerSection.classList.remove("is-fullscreen");
    document.body.classList.remove("viewer-fullscreen");
    setFullscreenButtonState();
    applyDisplayScale();
  }

  function toggleViewerFullscreen() {
    if (viewerFullscreenActive()) {
      exitViewerFullscreen();
    } else {
      enterViewerFullscreen();
    }
  }

  function setFullscreenButtonState() {
    if (!fullscreenButton) return;
    const active = viewerFullscreenActive();
    fullscreenButton.setAttribute("aria-pressed", active ? "true" : "false");
    fullscreenButton.title = active
      ? "Lopeta koko näyttö (Esc)."
      : "Koko näyttö: tabit täyttävät ruudun. Esc palaa.";
  }

  function setStatus(stage, detail) {
    if (statusEl) statusEl.textContent = STATUS_TEXT[stage] || STATUS_TEXT.queued;
    if (detailEl) detailEl.textContent = detail || "";
  }

  function setProgress(value, hidden) {
    if (!progressEl) return;
    progressEl.value = Math.max(0, Math.min(1, Number(value) || 0));
    progressEl.hidden = Boolean(hidden);
  }

  function renderJob(job) {
    setStatus(job.stage, job.status === "failed" ? job.error || "" : "");
    const done = job.status === "ready" || job.status === "failed";
    setProgress(done ? 1 : job.progress || 0, done);
  }

  async function readError(response) {
    try {
      const payload = await response.json();
      if (typeof payload.detail === "string") return payload.detail;
      return `HTTP ${response.status}`;
    } catch (error) {
      return `HTTP ${response.status}`;
    }
  }

  const mediaHandler = {
    get backingTrackDuration() {
      const scoreEnd = scoreEndTimeMs();
      if (scoreEnd > 0) return scoreEnd;
      return Number.isFinite(audio.duration) ? audio.duration * 1000 : 0;
    },
    get playbackRate() {
      return audio.playbackRate || 1;
    },
    set playbackRate(value) {
      setPlaybackRate(value);
    },
    masterVolume: 1,
    seekTo(time) {
      const target = Math.max(0, time / 1000);
      try {
        audio.currentTime = Number.isFinite(audio.duration)
          ? Math.min(target, audio.duration)
          : target;
      } catch (error) {
        console.warn("seek failed", error);
      }
      syncPosition();
    },
    play() {
      audio.play().catch((error) => console.warn("audio play failed", error));
    },
    pause() {
      audio.pause();
    },
  };

  function clearPlaybackRange() {
    if (!api) return;
    try {
      if (api.playbackRange) api.playbackRange = null;
    } catch (error) {
      /* older alphaTab builds */
    }
  }

  function syncPosition(force) {
    if (!api || !api.player || !Number.isFinite(audio.currentTime)) return;
    // While the browser is seeking, currentTime can still report the old
    // position. Feeding it to alphaTab would make the cursor jump back.
    if (!force && audio.seeking) return;
    const output = api.player.output;
    if (output && typeof output.updatePosition === "function") {
      output.updatePosition(syncTimeMs());
    }
  }

  function getAlphaTab() {
    if (api) return api;
    if (!window.alphaTab || !viewerEl) return null;
    try {
      api = new alphaTab.AlphaTabApi(viewerEl, {
        core: {
          fontDirectory: "/static/vendor/alphaTab/font/",
          logLevel: "warning",
          useWorkers: false,
        },
        display: {
          scale: 1,
          staveProfile: staveProfileValue(staveProfile),
          layoutMode: alphaTab.LayoutMode ? alphaTab.LayoutMode.Page : 0,
        },
        player: {
          playerMode: alphaTab.PlayerMode.EnabledExternalMedia,
          enableCursor: true,
          enableAnimatedBeatCursor: true,
          enableElementHighlighting: true,
          enableUserInteraction: true,
          scrollMode: alphaTab.ScrollMode
            ? alphaTab.ScrollMode.Smooth
            : 3,
          scrollElement: "#alphaTab",
          scrollOffsetY: -240,
        },
      });
    } catch (error) {
      console.error("alphaTab init failed", error);
      api = null;
      return null;
    }

    // The generator writes note velocities, and alphaTab renders them as
    // p/mp/mf/f markings. The player does not synthesize sound, so the
    // markings only add noise; hide EffectDynamics (NotationElement 18).
    if (
      api.settings &&
      api.settings.notation &&
      api.settings.notation.elements
    ) {
      const dynamicsElement =
        window.alphaTab && alphaTab.NotationElement
          ? alphaTab.NotationElement.EffectDynamics
          : 18;
      api.settings.notation.elements.set(dynamicsElement, false);
      if (typeof api.updateSettings === "function") api.updateSettings();
    }
    applyScrollOffset();

    api.playerStateChanged.on((args) => {
      // PlayerState.Playing === 1; the UMD bundle does not always expose
      // the enum on the global object.
      setPlayLabel(Number(args.state) === 1);
      if (Number(args.state) !== 1) {
        // alphaTab snaps to the beat start when pausing; restore quickly.
        window.setTimeout(() => syncPosition(true), 60);
      }
    });
    api.error.on((error) => console.error("alphaTab", error));
    // Dragging the mouse over the score creates a playback range (loop)
    // inside alphaTab. That range clamps seeks and makes the cursor jump,
    // so any range is cleared right away.
    if (
      api.playbackRangeChanged &&
      typeof api.playbackRangeChanged.on === "function"
    ) {
      api.playbackRangeChanged.on((args) => {
        if (!args || !args.playbackRange) return;
        clearPlaybackRange();
        window.setTimeout(() => syncPosition(true), 0);
      });
    }
    api.scoreLoaded.on(() => {
      clearPlaybackRange();
      const output = api.player && api.player.output;
      if (output) output.handler = mediaHandler;
      allTracks =
        api.score && Array.isArray(api.score.tracks)
          ? api.score.tracks.slice()
          : [];
      restoreTrackSelection();
      renderTrackToggles();
      applyScrollOffset();
      if (api.settings && api.settings.display) {
        api.settings.display.staveProfile = staveProfileValue(staveProfile);
      }
      // alphaTab renders only the first track when no track list is given.
      if (allTracks.length > 1) {
        window.setTimeout(applyTrackSelection, 0);
      }
      syncPositionSoon(80);
    });

    const output = api.player && api.player.output;
    if (output) {
      output.handler = mediaHandler;
    }
    return api;
  }

  function togglePlayback() {
    if (playButton && playButton.disabled) return;
    const willPlay = playButton
      ? playButton.dataset.state !== "playing"
      : audio.paused;
    if (willPlay) enterViewerFullscreen();
    if (api && activeTab) {
      try {
        api.playPause();
      } catch (error) {
        console.warn("playback failed", error);
      }
      return;
    }
    if (audio.paused) {
      audio.play().catch((error) => console.warn("audio play failed", error));
    } else {
      audio.pause();
    }
  }

  function renderTabMeta(tab) {
    if (titleEl) {
      titleEl.textContent = tab.artist
        ? `${tab.artist} — ${tab.title}`
        : tab.title;
    }
    if (metaEl) {
      const meta = tab.meta || {};
      const parts = [
        `${formatBpm(tab.bpm)} BPM`,
        `${tab.measure_count} bars`,
        `${tab.note_count} notes`,
      ];
      if (meta.tuning) parts.push(String(meta.tuning));
      metaEl.textContent = parts.join(" · ");
    }
    const files = (tab.meta && tab.meta.files) || {};
    for (const link of exportLinks) {
      const format = link.dataset.format;
      const available = Boolean(files[format]);
      link.hidden = !available;
      link.href = available
        ? `/api/tabs/${tab.id}/export/${format}`
        : "#";
    }
  }

  async function loadTab(tabId) {
    try {
      const response = await fetch(`/api/tabs/${tabId}`, { cache: "no-store" });
      if (!response.ok) return;
      const tab = await response.json();
      activeTab = tab;
      allTracks = [];
      visibleTrackIndexes = new Set();
      sliderSeeking = false;
      if (trackToggles) trackToggles.textContent = "";
      if (staveSelect) staveSelect.value = staveProfile;
      if (seekSlider) {
        seekSlider.max = "0";
        seekSlider.value = "0";
      }
      if (timeCurrent) timeCurrent.textContent = "0:00";
      if (timeTotal) timeTotal.textContent = "0:00";
      if (barReadout) barReadout.textContent = "Tahti –";
      if (sectionStatus) sectionStatus.textContent = "";
      if (attachStatus) attachStatus.textContent = "";
      if (bpmInput) {
        const savedBpm = Number(tab.bpm);
        bpmInput.value =
          Number.isFinite(savedBpm) && savedBpm > 0
            ? Number.isInteger(savedBpm)
              ? String(savedBpm)
              : savedBpm.toFixed(1)
            : "";
      }
      if (bpmStatus) bpmStatus.textContent = "";
      updateBpmDirtyState();
      setPlaybackRate(1);
      const storedSync = Number(tab.meta && tab.meta.sync_drift);
      setSyncDrift(Number.isFinite(storedSync) ? storedSync : 0, {
        sync: false,
      });
      const storedShift = Number(tab.meta && tab.meta.sync_offset_bars);
      setSyncOffsetBars(Number.isFinite(storedShift) ? storedShift : 0, {
        sync: false,
      });
      setSyncStatus("");
      try {
        localStorage.setItem("tabtool:lastTab", tab.id);
      } catch (error) {
        /* storage disabled */
      }

      renderTabMeta(tab);
      if (viewerSection) viewerSection.hidden = false;

      const files = (tab.meta && tab.meta.files) || {};
      const scoreFormat = files.gp5
        ? "gp5"
        : files.musicxml
          ? "musicxml"
          : "";
      if (!scoreFormat) {
        setStatus("failed", "Tabissa ei ole nuottitiedostoa.");
        return;
      }
      const hasAudio = Boolean(tab.audio_path);
      setAudioAvailable(hasAudio);
      if (hasAudio) {
        audio.src = `/api/tabs/${tab.id}/audio`;
        audio.load();
      }

      const score = await fetch(
        `/api/tabs/${tab.id}/score/${scoreFormat}`,
        {
          cache: "no-store",
        }
      );
      if (!score.ok) {
        setStatus("failed", await readError(score));
        return;
      }
      const bytes = new Uint8Array(await score.arrayBuffer());
      const instance = getAlphaTab();
      if (instance) instance.load(bytes);
    } catch (error) {
      console.error(error);
    }
  }

  async function importTabFile(file, youtubeUrl) {
    const data = new FormData();
    data.append("file", file);
    if (youtubeUrl) data.append("youtube_url", youtubeUrl);
    data.append("options", JSON.stringify(collectOptions()));
    setStatus("queued", "");
    setProgress(0, false);
    const response = await fetch("/api/tabs/import", {
      method: "POST",
      body: data,
    });
    if (!response.ok) {
      setStatus("failed", await readError(response));
      setProgress(1, true);
      return;
    }
    const payload = await response.json();
    if (gp5FileInput) gp5FileInput.value = "";
    // A YouTube link makes the endpoint return the audio job; without it
    // the response is a plain tab summary.
    if (payload && typeof payload.status === "string") {
      renderJob(payload);
      if (payload.tab_id) await loadTab(payload.tab_id);
      subscribe(payload.id, {
        onDone: (current) => {
          if (current.status === "ready") closeSearch();
        },
      });
      return;
    }
    await loadTab(payload.id);
    await loadLibrary();
    setStatus("ready", "");
    closeSearch();
    if (viewerSection) {
      viewerSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function libraryItemLabel(tab) {
    return tab.artist
      ? `${tab.artist} — ${tab.title}`
      : String(tab.title || tab.id);
  }

  function libraryItemMeta(tab) {
    const parts = [];
    const bpm = formatBpm(tab.bpm);
    if (bpm) parts.push(`${bpm} BPM`);
    parts.push(`${Number(tab.measure_count) || 0} tahtia`);
    parts.push(`${Number(tab.note_count) || 0} nuottia`);
    if (tab.source_type === "import") parts.push("tuotu tabi");
    const created = formatTimestamp(tab.created_at);
    if (created) parts.push(created);
    return parts.join(" · ");
  }

  function renderLibrary(tabs) {
    if (!libraryEl) return;
    libraryEl.textContent = "";
    if (libraryCount) {
      libraryCount.textContent = `${tabs.length} kappaletta`;
    }
    for (const tab of tabs) {
      const row = document.createElement("div");
      row.className = "library-item";
      row.dataset.tabId = tab.id;
      if (activeTab && activeTab.id === tab.id) row.classList.add("is-active");

      const open = document.createElement("button");
      open.type = "button";
      open.className = "library-open";
      open.title = libraryTooltip(tab);
      open.setAttribute("aria-label", open.title.replace(/\n/g, ", "));
      const name = document.createElement("span");
      name.className = "library-title";
      name.textContent = libraryItemLabel(tab);
      const meta = document.createElement("span");
      meta.className = "library-meta";
      meta.textContent = libraryItemMeta(tab);
      open.append(name, meta);
      open.addEventListener("click", () => selectTab(tab.id));

      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "ghost small library-delete";
      remove.textContent = "POISTA";
      remove.title = `Poista ${libraryItemLabel(tab)} kirjastosta.`;
      remove.addEventListener("click", () => requestDelete(tab));

      row.append(open, remove);
      libraryEl.append(row);
    }
    libraryEl.hidden = tabs.length === 0;
  }

  async function selectTab(tabId) {
    await loadTab(tabId);
    closeSearch();
    if (viewerSection) {
      viewerSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  async function loadLibrary() {
    if (!libraryEl) return;
    try {
      const response = await fetch("/api/tabs?limit=200", { cache: "no-store" });
      if (!response.ok) return;
      const tabs = await response.json();
      renderLibrary(tabs);
    } catch (error) {
      console.error(error);
    }
  }

  function openSearch() {
    if (!searchModal) return;
    searchModal.hidden = false;
    document.body.classList.add("modal-open");
    setLibraryStatus("");
    loadLibrary();
    if (urlInput) urlInput.focus();
  }

  function closeSearch() {
    if (!searchModal) return;
    searchModal.hidden = true;
    if (deleteDialog) deleteDialog.hidden = true;
    pendingDelete = null;
    document.body.classList.remove("modal-open");
  }

  function requestDelete(tab) {
    pendingDelete = tab;
    if (deleteDetail) {
      deleteDetail.textContent = `${libraryItemLabel(tab)} poistetaan kirjastosta.`;
    }
    setDeleteStatus("");
    if (deleteDialog) deleteDialog.hidden = false;
  }

  function cancelDelete() {
    if (deleteDialog) deleteDialog.hidden = true;
    pendingDelete = null;
    setDeleteStatus("");
  }

  function clearViewer() {
    activeTab = null;
    allTracks = [];
    visibleTrackIndexes = new Set();
    if (api) {
      try {
        api.stop();
      } catch (error) {
        /* ignore a stopped player */
      }
    }
    audio.pause();
    audio.removeAttribute("src");
    audio.load();
    if (viewerSection) viewerSection.hidden = true;
    if (titleEl) titleEl.textContent = "";
    if (metaEl) metaEl.textContent = "";
    if (trackToggles) trackToggles.textContent = "";
    if (barReadout) barReadout.textContent = "Tahti –";
    setPlayLabel(false);
    try {
      localStorage.removeItem("tabtool:lastTab");
    } catch (error) {
      /* storage disabled */
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    const tab = pendingDelete;
    if (deleteConfirm) deleteConfirm.disabled = true;
    setDeleteStatus("Poistetaan…");
    try {
      const response = await fetch(`/api/tabs/${tab.id}`, { method: "DELETE" });
      if (!response.ok) {
        setDeleteStatus(await readError(response), true);
        return;
      }
      const result = await response.json();
      if (deleteDialog) deleteDialog.hidden = true;
      pendingDelete = null;
      if (activeTab && activeTab.id === tab.id) clearViewer();
      await loadLibrary();
      setLibraryStatus(
        result.mp3_kept ? "Poistettu. MP3 jäi hakemistoon." : "Poistettu."
      );
    } catch (error) {
      setDeleteStatus(
        error instanceof Error ? error.message : String(error),
        true
      );
    } finally {
      if (deleteConfirm) deleteConfirm.disabled = false;
    }
  }

  function collectOptions() {
    const options = {};
    if (tuningSelect) options.tuning = tuningSelect.value;
    if (gridSelect) options.grid = Number(gridSelect.value);
    if (quickCheckbox && quickCheckbox.checked) options.separate = false;
    if (makeMp3Checkbox) options.archive_mp3 = makeMp3Checkbox.checked;
    return options;
  }

  async function importTabFromUrl(url) {
    const data = new FormData();
    data.append("url", url);
    setStatus("queued", "Haetaan tabia…");
    const response = await fetch("/api/tabs/import-url", {
      method: "POST",
      body: data,
    });
    if (!response.ok) {
      setStatus("failed", await readError(response));
      setProgress(1, true);
      return;
    }
    const tab = await response.json();
    await loadTab(tab.id);
    await loadLibrary();
    setStatus("ready", "");
    closeSearch();
    if (viewerSection) {
      viewerSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  async function submitJob(event) {
    event.preventDefault();
    if (submitting) return;

    const file = fileInput && fileInput.files ? fileInput.files[0] : null;
    const url = urlInput ? urlInput.value.trim() : "";
    const gp5Url = gp5Input ? gp5Input.value.trim() : "";
    const gp5File =
      gp5FileInput && gp5FileInput.files ? gp5FileInput.files[0] : null;

    if (!file && !url && !gp5Url && !gp5File) {
      setStatus(
        "failed",
        "Valitse audio, liitä YouTube-linkki tai valitse GP-linkki/-tiedosto."
      );
      return;
    }
    if (gp5Url && gp5File) {
      setStatus(
        "failed",
        "Valitse GP-linkki tai GP-tiedosto, ei molempia."
      );
      return;
    }
    if ((gp5Url || gp5File) && file) {
      setStatus(
        "failed",
        "GP5-lähteen kanssa käytä YouTube-linkkiä, ei omaa audiotiedostoa."
      );
      return;
    }

    submitting = true;
    if (generateButton) generateButton.disabled = true;
    setStatus("queued", "");
    setProgress(0, false);

    try {
      if (gp5File) {
        await importTabFile(gp5File, url);
        return;
      }
      if (gp5Url && !url) {
        await importTabFromUrl(gp5Url);
        return;
      }

      const data = new FormData();
      if (file) data.append("file", file);
      if (url) data.append("youtube_url", url);
      if (gp5Url) data.append("gp5_url", gp5Url);
      data.append("options", JSON.stringify(collectOptions()));
      if (regenerateCheckbox && regenerateCheckbox.checked) {
        data.append("regenerate", "true");
      }

      const response = await fetch("/api/jobs", { method: "POST", body: data });
      if (!response.ok) {
        setStatus("failed", await readError(response));
        setProgress(1, true);
        return;
      }
      const job = await response.json();
      renderJob(job);
      if (job.tab_id) {
        // GP5 jobs already have a tab; show the score while audio downloads.
        await loadTab(job.tab_id);
      }
      if (job.status === "ready" && job.tab_id) {
        await loadLibrary();
        setStatus("ready", "");
        closeSearch();
      } else {
        subscribe(job.id, {
          onDone: (current) => {
            if (current.status === "ready") closeSearch();
          },
        });
      }
    } catch (error) {
      setStatus("failed", error instanceof Error ? error.message : String(error));
    } finally {
      submitting = false;
      if (generateButton) generateButton.disabled = false;
    }
  }

  async function attachAudio() {
    if (!activeTab || !activeTab.id) return;
    if (attachAudioButton) attachAudioButton.disabled = true;
    setAttachStatus("Etsitään audiota…");
    try {
      const response = await fetch(
        `/api/tabs/${activeTab.id}/attach-audio`,
        { method: "POST" }
      );
      if (!response.ok) {
        setAttachStatus(await readError(response));
        return;
      }
      const summary = await response.json();
      const tabId = activeTab.id;
      const sourceBpm = Number(summary.source_bpm) || 0;
      await loadTab(tabId);
      await loadLibrary();
      const tabBpm = Number(activeTab && activeTab.bpm) || 0;
      setAttachStatus(
        sourceBpm && tabBpm
          ? `Audio liitetty. Tabi ${Math.round(tabBpm)} BPM, AI-arvio ${Math.round(sourceBpm)} BPM – aseta TAB BPM kappaleen tempoon tai säädä Nopeus.`
          : "Audio liitetty."
      );
    } catch (error) {
      setAttachStatus(
        error instanceof Error ? error.message : String(error)
      );
    } finally {
      if (attachAudioButton) attachAudioButton.disabled = false;
    }
  }

  async function applyTempo() {
    if (!activeTab || !activeTab.id) {
      setBpmStatus("Avaa tabi ensin.", true);
      return;
    }
    const bpm = Number(bpmInput && bpmInput.value);
    if (!Number.isFinite(bpm) || bpm < 20 || bpm > 400) {
      setBpmStatus("Anna BPM 20–400.", true);
      return;
    }
    if (bpmButton) bpmButton.disabled = true;
    setBpmStatus("Tallennetaan…");
    try {
      const data = new FormData();
      data.append("bpm", String(bpm));
      const response = await fetch(
        `/api/tabs/${activeTab.id}/tempo`,
        { method: "POST", body: data }
      );
      if (!response.ok) {
        setBpmStatus(await readError(response), true);
        return;
      }
      const tabId = activeTab.id;
      await loadTab(tabId);
      await loadLibrary();
      setBpmStatus("Tallennettu.");
    } catch (error) {
      setBpmStatus(
        error instanceof Error ? error.message : String(error),
        true
      );
    } finally {
      if (bpmButton) bpmButton.disabled = false;
    }
  }

  async function generateSection() {
    if (!activeTab || !activeTab.id) {
      setSectionStatus("Avaa tabi ensin.");
      return;
    }
    if (
      (playButton && playButton.disabled) ||
      !Number.isFinite(audio.duration) ||
      audio.duration <= 0
    ) {
      setSectionStatus("Tällä tabilla ei ole audiota.");
      return;
    }
    const start = Math.max(0, Number(audio.currentTime) || 0);
    const length = Number(sectionLength && sectionLength.value) || 60;
    const data = new FormData();
    data.append("start_seconds", String(start));
    data.append("clip_seconds", String(length));
    if (sectionButton) sectionButton.disabled = true;
    setSectionStatus("Valmistellaan…");
    try {
      const response = await fetch(
        `/api/tabs/${activeTab.id}/section`,
        { method: "POST", body: data }
      );
      if (!response.ok) {
        setSectionStatus(await readError(response));
        if (sectionButton) sectionButton.disabled = false;
        return;
      }
      const job = await response.json();
      if (job.status === "ready" && job.tab_id) {
        await loadTab(job.tab_id);
        loadLibrary();
        setSectionStatus("Valmis");
        if (sectionButton) sectionButton.disabled = false;
        return;
      }
      subscribe(job.id, {
        onJob: (current) =>
          setSectionStatus(STATUS_TEXT[current.stage] || "Queued"),
        onDone: (current) => {
          if (sectionButton) sectionButton.disabled = false;
          setSectionStatus(
            current.status === "ready"
              ? "Valmis"
              : current.error || "Failed"
          );
        },
      });
    } catch (error) {
      setSectionStatus(
        error instanceof Error ? error.message : String(error)
      );
      if (sectionButton) sectionButton.disabled = false;
    }
  }

  function subscribe(jobId, handlers) {
    const hooks = handlers || {};
    if (stream) stream.close();
    stream = new EventSource(`/api/jobs/${jobId}/events`);
    stream.onmessage = async (event) => {
      let job;
      try {
        job = JSON.parse(event.data);
      } catch (error) {
        return;
      }
      if (!job) return;
      renderJob(job);
      if (typeof hooks.onJob === "function") hooks.onJob(job);
      if (job.status === "ready" || job.status === "failed") {
        if (stream) stream.close();
        stream = null;
        if (job.status === "ready" && job.tab_id) {
          await loadTab(job.tab_id);
          loadLibrary();
        }
        if (typeof hooks.onDone === "function") hooks.onDone(job);
      }
    };
    stream.onerror = () => {
      /* EventSource reconnects automatically; the job row keeps the state. */
    };
  }

  if (form) form.addEventListener("submit", submitJob);
  if (openSearchButton) openSearchButton.addEventListener("click", openSearch);
  if (openSearchTopButton) {
    openSearchTopButton.addEventListener("click", openSearch);
  }
  if (closeSearchButton) {
    closeSearchButton.addEventListener("click", closeSearch);
  }
  if (searchModal) {
    searchModal.addEventListener("click", (event) => {
      if (event.target === searchModal) closeSearch();
    });
  }
  if (deleteCancel) deleteCancel.addEventListener("click", cancelDelete);
  if (deleteConfirm) deleteConfirm.addEventListener("click", confirmDelete);
  if (deleteDialog) {
    deleteDialog.addEventListener("click", (event) => {
      if (event.target === deleteDialog) cancelDelete();
    });
  }
  if (playButton) playButton.addEventListener("click", togglePlayback);
  if (staveSelect) {
    staveSelect.value = staveProfile;
    staveSelect.addEventListener("change", () =>
      applyStaveProfile(staveSelect.value)
    );
  }
  if (fullscreenButton) {
    fullscreenButton.addEventListener("click", toggleViewerFullscreen);
  }
  if (seekSlider) {
    seekSlider.addEventListener("input", () => {
      sliderSeeking = true;
      seekTo(Number(seekSlider.value));
    });
    const finishSeeking = () => {
      sliderSeeking = false;
      updateTransport();
    };
    seekSlider.addEventListener("change", finishSeeking);
    seekSlider.addEventListener("pointerup", finishSeeking);
    seekSlider.addEventListener("keyup", finishSeeking);
    document.addEventListener("pointerup", finishSeeking);
    window.addEventListener("blur", finishSeeking);
  }
  if (seekBack) seekBack.addEventListener("click", () => seekBy(-5));
  if (seekForward) seekForward.addEventListener("click", () => seekBy(5));
  if (sectionButton) {
    sectionButton.addEventListener("click", generateSection);
  }
  if (attachAudioButton) {
    attachAudioButton.addEventListener("click", attachAudio);
  }
  if (rateSlider) {
    rateSlider.addEventListener("input", () =>
      setPlaybackRate(rateSlider.value)
    );
  }
  if (syncSlider) {
    syncSlider.addEventListener("input", () => {
      setSyncStatus("");
      setSyncDrift(Number(syncSlider.value) / 100);
      if (syncSaveTimer) window.clearTimeout(syncSaveTimer);
      syncSaveTimer = window.setTimeout(persistSyncDrift, 700);
    });
    syncSlider.addEventListener("change", persistSyncDrift);
  }
  if (shiftInput) {
    shiftInput.addEventListener("input", () => {
      setSyncStatus("");
      setSyncOffsetBars(shiftInput.value);
      if (syncSaveTimer) window.clearTimeout(syncSaveTimer);
      syncSaveTimer = window.setTimeout(persistSyncDrift, 700);
    });
    shiftInput.addEventListener("change", () => {
      setSyncOffsetBars(shiftInput.value);
      persistSyncDrift();
    });
  }
  if (bpmButton) {
    bpmButton.addEventListener("click", applyTempo);
  }
  if (bpmInput) {
    bpmInput.addEventListener("input", () => {
      setBpmStatus("");
      updateBpmDirtyState();
    });
  }
  if (bpmInput) {
    bpmInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        applyTempo();
      }
    });
  }
  document.addEventListener("fullscreenchange", () => {
    if (!document.fullscreenElement) {
      if (viewerSection) viewerSection.classList.remove("is-fullscreen");
      document.body.classList.remove("viewer-fullscreen");
    }
    setFullscreenButtonState();
    applyDisplayScale();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && searchModal && !searchModal.hidden) {
      if (deleteDialog && !deleteDialog.hidden) {
        cancelDelete();
      } else {
        closeSearch();
      }
      return;
    }
    const tag = event.target && event.target.tagName;
    const interactive = ["INPUT", "SELECT", "TEXTAREA", "BUTTON"].includes(
      tag
    );
    if (!interactive && viewerSection && !viewerSection.hidden) {
      if (event.key === " ") {
        event.preventDefault();
        togglePlayback();
        return;
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        seekBy(-5);
        return;
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        seekBy(5);
        return;
      }
    }
    if (
      event.key === "Escape" &&
      viewerSection &&
      viewerSection.classList.contains("is-fullscreen")
    ) {
      exitViewerFullscreen();
    }
  });
  let resizeTimer = null;
  window.addEventListener("resize", () => {
    if (!viewerFullscreenActive()) {
      applyScrollOffset();
      return;
    }
    if (resizeTimer) window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(applyDisplayScale, 180);
  });
  if (audio) {
    audio.addEventListener("play", () => setPlayLabel(true));
    audio.addEventListener("pause", () => {
      setPlayLabel(false);
      // alphaTab snaps the cursor to the start of the current beat when the
      // player pauses; restore the exact audio position shortly after.
      window.setTimeout(() => syncPosition(true), 150);
    });
    audio.addEventListener("loadedmetadata", updateTransport);
    audio.addEventListener("durationchange", updateTransport);
    audio.addEventListener("timeupdate", updateTransport);
    audio.addEventListener("seeked", () => {
      syncPosition(true);
      updateTransport();
    });
    audio.addEventListener("ended", () => {
      setPlayLabel(false);
      updateTransport();
    });
    window.setInterval(() => {
      if (!audio.paused && !audio.seeking) syncPosition();
    }, 50);
  }
  setFullscreenButtonState();

  (async () => {
    await loadLibrary();
    let target = null;
    try {
      target = new URLSearchParams(window.location.search).get("tab");
    } catch (error) {
      target = null;
    }
    if (!target) {
      try {
        target = localStorage.getItem("tabtool:lastTab");
      } catch (error) {
        target = null;
      }
    }
    if (target) await loadTab(target);
  })();
})();



