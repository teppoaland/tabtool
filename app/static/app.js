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
  const COUNT_IN_STORAGE_KEY = "tabtool:countIn";
  // Sanat-editorin kelluva sijainti muistetaan selaimessa (v2.07).
  const LYRICS_POS_KEY = "tabtool:lyricsPos";
  // Sanoitusrivin koko on kerroin (v2.08): 200 % = tuplat entisestä, ja
  // sama oletus on app/settings.py:ssä (lyrics.scale).
  const LYRICS_SCALE_DEFAULT = 200;
  // Koko näytön nosto alareunasta pikseleinä (v2.09), default 100 px.
  const LYRICS_OFFSET_DEFAULT = 100;
  // Tahtilistan oletuskorkeus pikseleinä (v2.13) = CSS:n 14rem.
  const LYRICS_BARS_DEFAULT = 224;
  const SYNC_LIMIT = 0.1;
  // SIIRTO (whole-bar shift) may have to bridge a large structure difference
  // in the tab data, so its range is generous (v1.75). syncTimeMs() still
  // clamps the resulting position to the score end, so the clock is unchanged.
  const SYNC_OFFSET_LIMIT = 999;
  // Hold the fed score position just short of the score end (v1.69). A tab can
  // end before the recording does (e.g. WASP: the guitars stop, the drums ring
  // out). As soon as the position reaches the last bar, alphaTab's player
  // finishes: it pauses the output (our <audio>) and rewinds to tick 0, so the
  // song was cut at the last tab bar. Keeping the feed this much before the end
  // lets the engine keep playing while the audio runs out on its own. alphaTab
  // maps backing-track time onto the score linearly, so the resulting tick is
  // always below endTick; every other position keeps the 1:1 clock, SIIRTO,
  // SYNC and BPM unchanged.
  const SCORE_END_GUARD_MS = 50;
  // The browser reports audio.currentTime in chunks (typically ~250 ms) that
  // can repeat or step back a little between two reads. alphaTab turns every
  // fed position into the cursor, so one stale read rewinds it: the cursor
  // hops a beat forward and back. While the audio plays the feed therefore
  // keeps the highest position seen (it always comes from a real read, so the
  // clock cannot run ahead). A bigger backwards jump is a real seek and resets
  // the baseline (v1.91).
  const FEED_JITTER_S = 0.3;

  // === SETTINGS (v2.02) =================================================
  // The Settings view (/settings) owns these values and app/settings.py serves
  // them. Everything is clamped here, so a broken stored value cannot stall
  // the count-in or hide a control that is needed to bring it back. The UI
  // switches only add body classes; the playback chain is not involved and
  // every feature is visible by default.
  const SETTINGS_URL = "/api/settings";
  const UI_FEATURES = [
    "nav_library",
    "nav_remote",
    "nav_api",
    "fullscreen",
    "countin_switch",
    "view_select",
    "track_toggles",
    "variant",
    "attach_audio",
    "section",
    "rate",
    "sync",
    "shift",
    "align",
    "bpm",
    "export",
  ];
  // Defaults used only when the browser has no local choice of its own.
  let defaultCountInEnabled = true;
  let defaultStaveProfile = null;

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
  const playCountdown = document.getElementById("play-countdown");
  const playCountdownValue = document.getElementById("play-countdown-value");
  const titleEl = document.getElementById("tab-title");
  const metaEl = document.getElementById("tab-meta");
  const staveSelect = document.getElementById("stave-select");
  const trackToggles = document.getElementById("track-toggles");
  const variantButton = document.getElementById("variant-button");
  const variantRestoreButton = document.getElementById("variant-restore-button");
  // Versiovalinnan varmistus (v2.04).
  const variantDialog = document.getElementById("variant-dialog");
  const variantDetail = document.getElementById("variant-detail");
  const variantStatus = document.getElementById("variant-status");
  const variantConfirm = document.getElementById("variant-confirm");
  const variantCancel = document.getElementById("variant-cancel");
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
  // Sanat (v2.06): sidecar lyrics, painted outside the playback chain.
  const lyricsButton = document.getElementById("lyrics-button");
  const lyricsStrip = document.getElementById("lyrics-strip");
  const lyricsCurrent = document.getElementById("lyrics-current");
  // Sneak peek (v2.19): the next line, one bar early.
  const lyricsNext = document.getElementById("lyrics-next");
  const lyricsDialog = document.getElementById("lyrics-dialog");
  const lyricsHandle = document.getElementById("lyrics-handle");
  // Kaksi kahvaa (v2.11): vasen yläkulma ja oikea alakulma.
  const lyricsResizeGrips = Array.from(
    document.querySelectorAll(".lyrics-resize")
  );
  const lyricsBarBadge = document.getElementById("lyrics-bar-badge");
  // Soittoeditori (v2.12): samat perustoiminnot kuin kaukosäätimessä.
  const lyricsPlayButton = document.getElementById("lyrics-play");
  const lyricsStartButton = document.getElementById("lyrics-start");
  const lyricsBackButton = document.getElementById("lyrics-back");
  const lyricsForwardButton = document.getElementById("lyrics-forward");
  const lyricsForm = document.getElementById("lyrics-form");
  const lyricsSubject = document.getElementById("lyrics-subject");
  const lyricsInput = document.getElementById("lyrics-input");
  // Muistiinpanot (v2.20): free text in the same sidecar.
  const lyricsNotesInput = document.getElementById("lyrics-notes");
  const lyricsBars = document.getElementById("lyrics-bars");
  const lyricsSplitter = document.getElementById("lyrics-split");
  const lyricsStatus = document.getElementById("lyrics-status");
  const lyricsSave = document.getElementById("lyrics-save");
  const lyricsClose = document.getElementById("lyrics-close");
  // v2.22: bulk numbering of a pasted block, one line per bar.
  const lyricsFillButton = document.getElementById("lyrics-fill");
  // Lukitus (v2.18): valmis sanoitus pysyy muuttumattomana.
  const lyricsLockInput = document.getElementById("lyrics-lock");
  const rateSlider = document.getElementById("rate-slider");
  const rateReadout = document.getElementById("rate-readout");
  const syncSlider = document.getElementById("sync-slider");
  const syncReadout = document.getElementById("sync-readout");
  const syncStatus = document.getElementById("sync-status");
  const shiftInput = document.getElementById("shift-input");
  const syncOffsetReadout = document.getElementById("sync-offset-readout");
  const alignButton = document.getElementById("align-button");
  const countInToggle = document.getElementById("countin-toggle");
  const countInState = document.getElementById("countin-state");
  const bpmInput = document.getElementById("bpm-input");
  const bpmButton = document.getElementById("bpm-button");
  const bpmStatus = document.getElementById("bpm-status");
  const bpmField = bpmInput ? bpmInput.closest(".bpm-field") : null;
  const transport = document.querySelector(".transport");
  const gp5Input = document.getElementById("gp5-url-input");
  const gp5FileInput = document.getElementById("gp5-file-input");
  const makeMp3Checkbox = document.getElementById("make-mp3-checkbox");
  const searchModal = document.getElementById("search-modal");
  // v2.05: LIBRARY lives in the topbar only; the in-card duplicate is gone.
  const openSearchTopButton = document.getElementById("open-search-top");
  const closeSearchButton = document.getElementById("close-search");
  const libraryStatus = document.getElementById("library-status");
  const libraryCount = document.getElementById("library-count");
  const deleteDialog = document.getElementById("delete-dialog");
  const deleteDetail = document.getElementById("delete-detail");
  const deleteStatus = document.getElementById("delete-status");
  const deleteConfirm = document.getElementById("delete-confirm");
  const deleteCancel = document.getElementById("delete-cancel");
  // Tiedot-modali (v2.03): every editable library field plus read-only metadata.
  const detailDialog = document.getElementById("detail-dialog");
  const detailForm = document.getElementById("detail-form");
  const detailSubject = document.getElementById("detail-subject");
  const detailArtist = document.getElementById("detail-artist");
  const detailName = document.getElementById("detail-name");
  const detailTuning = document.getElementById("detail-tuning");
  const detailLocked = document.getElementById("detail-locked");
  const detailArchived = document.getElementById("detail-archived");
  const detailMeta = document.getElementById("detail-meta");
  const detailStatus = document.getElementById("detail-status");
  const detailSave = document.getElementById("detail-save");
  const detailCancel = document.getElementById("detail-cancel");
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
  let detailTab = null;
  let pendingVariant = null;
  let libraryTabs = [];
  let showArchive = false;
  let alignArmed = false;
  // Cursor feed (v1.91): the last position handed to alphaTab and the audio
  // time it was computed from. Used only to keep the feed monotonic while the
  // audio plays; the clock (syncTimeMs) is untouched.
  let lastFedScoreMs = -1;
  let lastFedAudioS = -1;

  // Count-in (v1.55): five steps then a short "0". UI-only state; see the
  // COUNT-IN block below and .clinerules/07-playback-frozen.md.
  const COUNT_IN_FROM = 5;
  const COUNT_IN_STEP_MS = 1000;
  const COUNT_IN_ZERO_MS = 250;
  // v2.02: the Settings view may override the duration. These start from the
  // documented defaults and are replaced (and clamped) by applyRuntimeSettings.
  let countInSteps = COUNT_IN_FROM;
  let countInStepMs = COUNT_IN_STEP_MS;
  let countInZeroMs = COUNT_IN_ZERO_MS;
  let countInDone = false;
  let countInActive = false;
  let countInSkipped = false;
  // Audio position captured when PLAY arms the countdown. Pressing FULLSCREEN
  // during the countdown re-renders the score, which can move the audio off its
  // start position; finishCountIn() restores it so the delayed PLAY starts from
  // exactly where an immediate PLAY would have (v1.92).
  let countInAudioTime = 0;
  let countInTimer = null;
  let countInZeroTimer = null;
  let countInValue = COUNT_IN_FROM;
  let countInEnabled = true;

  // === SANAT (v2.06) – own overlay, rule 07 ===========================
  // Lyrics live in data/lyrics/<tab_id>.json (sidecar). This state never
  // takes part in the clock, seek or alphaTab wiring: the strip reads the
  // bar number that updateTransport() already printed into #bar-readout.
  let lyricsTabId = "";
  let lyricsMeasures = {};
  let lyricsBarsTotal = 0;
  let lyricsLoadingFor = "";
  let lyricsShownBar = -1;
  let lyricsDirty = false;
  // v2.17: the bar last pressed in the editor. Ctrl+Enter writes the selected
  // words into it and moves the anchor one bar ahead (quick numbering).
  let lyricsAnchorBar = 0;
  // Offsets of the selection focusLyricsBarLine() made, so it is never
  // mistaken for words the user picked to assign to a bar.
  let lyricsLineSelection = null;
  // v2.18: a finished lyric can be locked in the sidecar. While locked the
  // field is read-only and the bar handlers refuse to write; viewing and
  // seeking keep working.
  let lyricsLocked = false;
  // v2.20: the free-text note from the sidecar (source, open fixes).
  let lyricsNotes = "";
  // Sanoitusrivin koko prosentteina (v2.08) ja nosto pikseleinä (v2.09),
  // molemmat tulevat /api/settingsistä.
  let lyricsScale = LYRICS_SCALE_DEFAULT;
  let lyricsOffset = LYRICS_OFFSET_DEFAULT;
  // Sneak peek on/off (v2.19), Settings `lyrics.sneak` (oletus päällä).
  let lyricsSneak = true;
  // Floating editor drag state (v2.07): DOM only, no audio/api involvement.
  let lyricsDrag = null;
  // Resize state for the floating editor (v2.08): DOM only as well.
  let lyricsResize = null;
  // Splitter between the bar list and the text field (v2.13).
  let lyricsSplitDrag = null;

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
      ? Math.min(
          SYNC_OFFSET_LIMIT,
          Math.max(-SYNC_OFFSET_LIMIT, Math.round(number * 4) / 4)
        )
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
    // Never feed the score end itself (v1.69), otherwise alphaTab finishes and
    // pauses/rewinds the audio. The clamp only touches the very end of the
    // score; the 1:1 mapping and the corrections above stay as they were.
    const audioLimit = duration > 0 ? duration * 1000 : position;
    const scoreEnd = scoreEndTimeMs();
    const limit =
      scoreEnd > SCORE_END_GUARD_MS
        ? Math.min(audioLimit, scoreEnd - SCORE_END_GUARD_MS)
        : audioLimit;
    return Math.min(position, limit);
  }

  // End of the score timeline in milliseconds. alphaTab's external-media
  // clock maps the backing-track time onto the full score with the ratio
  // (scoreEnd / backingTrackDuration). If the reported backing track length
  // is the audio length and the score is longer, every feed of audio time is
  // stretched and the cursor runs ahead of the music. Returning the score's
  // own end here keeps that mapping 1:1, so only the explicit BPM/SYNC/SIIRTO
  // corrections in syncTimeMs() are applied.
  function scoreEndTimeMs() {
    // The score end in ms. alphaTab's api.endTime reflects the live
    // currentPosition and is 0 until playback starts, so compute it from the
    // master bars instead: totalTicks * 60000 / (tempo * 960 PPQ). This must
    // be correct on the very first cursor tick, otherwise alphaTab stretches
    // the backing-track time onto the score and the cursor runs ahead.
    if (api && api.score && Array.isArray(api.score.masterBars)) {
      const bars = api.score.masterBars;
      if (bars.length) {
        const last = bars[bars.length - 1];
        const endTick =
          (Number(last.start) || 0) +
          (typeof last.calculateDuration === "function"
            ? Number(last.calculateDuration()) || 0
            : 0);
        const tempo = notatedTempo() || 120;
        if (endTick > 0) return (endTick * 60000) / (tempo * 960);
      }
    }
    return 0;
  }

  // Number of ticks in one bar (4/4 at 960 PPQ = 3840).
  function ticksPerBar() {
    if (api && api.score && Array.isArray(api.score.masterBars)) {
      const bars = api.score.masterBars;
      if (bars.length > 1) {
        const ticks = Number(bars[1].start) - Number(bars[0].start);
        if (ticks > 0) return ticks;
      }
    }
    return 3840;
  }

  // Difference between the cursor and the audio's musical position, in bars.
  // Positive = the cursor is ahead of the music, negative = behind.
  function currentOffsetBars() {
    if (!api || !activeTab) return null;
    const bpm = Number(activeTab.bpm) || 0;
    const tick = Number(api.tickPosition);
    if (bpm <= 0 || !Number.isFinite(tick)) return null;
    const audioTick = ((Number(audio.currentTime) || 0) * bpm * 960) / 60000;
    const perBar = ticksPerBar();
    if (!perBar) return null;
    return (tick - audioTick) / perBar;
  }

  function updateOffsetReadout() {
    if (!syncOffsetReadout) return;
    const offset = currentOffsetBars();
    if (offset === null) {
      syncOffsetReadout.textContent = "";
      return;
    }
    const bars = Math.round(offset * 4) / 4;
    if (Math.abs(bars) < 0.05) {
      syncOffsetReadout.textContent = "Kohdallaan";
      syncOffsetReadout.classList.remove("is-error");
      return;
    }
    const value = `${bars > 0 ? "+" : "−"}${Math.abs(bars)
      .toFixed(2)
      .replace(".", ",")} tahtia`;
    syncOffsetReadout.textContent =
      bars > 0 ? `Osoitin ${value} edellä` : `Osoitin ${value} jäljessä`;
    syncOffsetReadout.classList.toggle("is-error", Math.abs(bars) > 0.5);
  }

  // "Grab the cursor" alignment: while armed, alphaTab's click-to-seek is
  // disabled and the next click on a note shifts the tab so that note lands
  // on the audio's current position (saved as SIIRTO).
  function armAlign() {
    if (!api || !activeTab) return;
    alignArmed = true;
    if (alignButton) {
      alignButton.textContent = "KLIKKAA NUOTTIA";
      alignButton.setAttribute("aria-pressed", "true");
    }
    setSyncStatus("Klikkaa tabista sitä nuottia, jonka pitäisi soida nyt…");
    if (api.settings && api.settings.player) {
      api.settings.player.enableUserInteraction = false;
      if (typeof api.updateSettings === "function") api.updateSettings();
    }
  }

  function disarmAlign() {
    alignArmed = false;
    if (alignButton) {
      alignButton.textContent = "KOHDISTA";
      alignButton.removeAttribute("aria-pressed");
    }
    // Restore click-to-seek after the current mouseup, so alphaTab does not
    // also seek on the click that performed the alignment.
    window.setTimeout(() => {
      if (!alignArmed && api && api.settings && api.settings.player) {
        api.settings.player.enableUserInteraction = true;
        if (typeof api.updateSettings === "function") api.updateSettings();
      }
    }, 200);
  }

  function handleAlignClick(beat) {
    if (!alignArmed) return;
    if (!api || !activeTab) {
      disarmAlign();
      return;
    }
    const clickedTick = Number(beat && beat.absolutePlaybackStart);
    const currentTick = Number(api.tickPosition);
    const perBar = ticksPerBar();
    if (!Number.isFinite(clickedTick) || !Number.isFinite(currentTick) || !perBar) {
      disarmAlign();
      return;
    }
    const deltaBars = (clickedTick - currentTick) / perBar;
    const next = Math.min(
      SYNC_OFFSET_LIMIT,
      Math.max(
        -SYNC_OFFSET_LIMIT,
        Math.round((syncOffsetBars + deltaBars) * 4) / 4
      )
    );
    setSyncOffsetBars(next);
    persistSyncDrift();
    setSyncStatus(`Kohdistettu ${next > 0 ? "+" : ""}${next} tahtia`);
    disarmAlign();
  }

  async function persistSyncDrift() {
    if (!activeTab || !activeTab.id) return;
    if (tabIsLocked(activeTab)) {
      setSyncStatus(LOCKED_HINT, true);
      return;
    }
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
        ? "Toista tai pysäytä audio. Koko näyttö avataan FULLSCREEN-painikkeesta."
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

  // A locked tab is read-only (v1.70): the lock protects every stored setting
  // (name, tuning, archive flag, TAB BPM, SYNC, SIIRTO, attached audio), not
  // only deletion. Only the library editor may clear the lock itself.
  const LOCKED_HINT = "Tabi on lukittu. Avaa lukitus kirjastossa (Tiedot).";

  function tabIsLocked(tab) {
    return Boolean(tab && tab.locked);
  }

  function setLockedControl(element, locked) {
    if (!element) return;
    if (!Object.prototype.hasOwnProperty.call(element.dataset, "lockTitle")) {
      element.dataset.lockTitle = element.title || "";
    }
    element.disabled = locked;
    element.title = locked ? LOCKED_HINT : element.dataset.lockTitle;
  }

  function applyLockState() {
    const locked = tabIsLocked(activeTab);
    for (const element of [
      bpmInput,
      bpmButton,
      syncSlider,
      shiftInput,
      alignButton,
      attachAudioButton,
    ]) {
      setLockedControl(element, locked);
    }
    if (bpmField) bpmField.classList.toggle("is-locked", locked);
    updateVariantButton();
  }

  function updateVariantButton() {
    if (!variantButton) return;
    const meta = (activeTab && activeTab.meta) || {};
    const variants = Array.isArray(meta.variants) ? meta.variants : [];
    const show = variants.length > 1 && !meta.variant_finalized;
    variantButton.hidden = !show;
    if (show) variantButton.disabled = tabIsLocked(activeTab);
    if (variantRestoreButton) {
      // v2.04: a finalized tab can always be restored from its backup.
      const canRestore = Boolean(meta.variant_finalized && meta.variant_backup);
      variantRestoreButton.hidden = !canRestore;
      variantRestoreButton.disabled = tabIsLocked(activeTab);
    }
  }

  // The variant whose track is the only one visible (the one the user picked
  // with the track chips).
  function visibleVariantEntry() {
    const variants = (activeTab && activeTab.meta && activeTab.meta.variants) || [];
    const visible = Array.from(visibleTrackIndexes).filter((index) =>
      variants.some((item) => Number(item.track) === index)
    );
    if (visible.length !== 1) return null;
    return variants.find((item) => Number(item.track) === visible[0]) || null;
  }

  function setVariantStatus(text, isError) {
    if (!variantStatus) return;
    variantStatus.textContent = text || "";
    variantStatus.classList.toggle("is-error", Boolean(isError));
  }

  function closeVariantDialog() {
    if (!variantDialog) return;
    variantDialog.hidden = true;
    pendingVariant = null;
    setVariantStatus("");
    if (!searchModal || searchModal.hidden) {
      document.body.classList.remove("modal-open");
    }
  }

  // v2.04: finalizing deletes the other fingerings, so the choice is confirmed
  // first. The server backs the deleted variants up before it writes anything.
  function openVariantDialog() {
    if (!activeTab || !activeTab.id) return;
    if (tabIsLocked(activeTab)) {
      setAttachStatus(LOCKED_HINT);
      return;
    }
    const entry = visibleVariantEntry();
    if (!entry) {
      setAttachStatus("Valitse ensin yksi versio näkyviin.");
      return;
    }
    pendingVariant = entry;
    if (variantDetail) {
      variantDetail.textContent = `Pidettävä versio: ${entry.label}`;
    }
    setVariantStatus("");
    if (variantConfirm) variantConfirm.disabled = false;
    if (variantDialog) {
      variantDialog.hidden = false;
      document.body.classList.add("modal-open");
    }
    if (variantConfirm) variantConfirm.focus();
  }

  async function finalizeVariant() {
    const entry = pendingVariant || visibleVariantEntry();
    if (!activeTab || !activeTab.id) return;
    if (tabIsLocked(activeTab)) {
      setAttachStatus(LOCKED_HINT);
      closeVariantDialog();
      return;
    }
    if (!entry) {
      closeVariantDialog();
      setAttachStatus("Valitse ensin yksi versio näkyviin.");
      return;
    }
    if (variantConfirm) variantConfirm.disabled = true;
    setVariantStatus("Valitaan…");
    try {
      const data = new FormData();
      data.append("variant", String(entry.id));
      const response = await fetch(`/api/tabs/${activeTab.id}/variant`, {
        method: "POST",
        body: data,
      });
      if (!response.ok) {
        setVariantStatus(await readError(response), true);
        return;
      }
      const updated = await response.json();
      const backup = (updated && updated.variant_backup) || "";
      const tabId = activeTab.id;
      closeVariantDialog();
      await loadTab(tabId);
      await loadLibrary();
      setAttachStatus(
        backup
          ? `Valittu: ${entry.label} · varmuuskopio ${backup}`
          : `Valittu: ${entry.label}`
      );
    } catch (error) {
      setVariantStatus(
        error instanceof Error ? error.message : String(error),
        true
      );
    } finally {
      if (variantConfirm) variantConfirm.disabled = false;
      if (variantButton) variantButton.disabled = tabIsLocked(activeTab);
    }
  }

  async function restoreVariants() {
    if (!activeTab || !activeTab.id) return;
    if (tabIsLocked(activeTab)) {
      setAttachStatus(LOCKED_HINT);
      return;
    }
    if (variantRestoreButton) variantRestoreButton.disabled = true;
    setAttachStatus("Palautetaan versioita…");
    try {
      const response = await fetch(
        `/api/tabs/${activeTab.id}/variant/restore`,
        { method: "POST" }
      );
      if (!response.ok) {
        setAttachStatus(await readError(response));
        return;
      }
      const tabId = activeTab.id;
      await loadTab(tabId);
      await loadLibrary();
      setAttachStatus("Versiot palautettu. Kokeile toista raitaa.");
    } catch (error) {
      setAttachStatus(error instanceof Error ? error.message : String(error));
    } finally {
      if (variantRestoreButton) {
        variantRestoreButton.disabled = tabIsLocked(activeTab);
      }
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
    updateOffsetReadout();
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
    // A saved local choice wins; the Settings default fills in only when this
    // browser has no stave choice yet (v2.02).
    try {
      const stored = localStorage.getItem(STAVE_STORAGE_KEY);
      if (stored) return normalizeStaveProfile(stored);
    } catch (error) {
      /* storage disabled */
    }
    return normalizeStaveProfile(defaultStaveProfile || "tab");
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
    if (tab.channel) parts.push(`YouTube: ${tab.channel}`);
    if (tab.source_url) parts.push(`Audio: ${tab.source_url}`);
    if (tab.tab_source_url) parts.push(`Tabi: ${tab.tab_source_url}`);
    else if (tab.tab_source_file) parts.push(`Tabi: ${tab.tab_source_file}`);
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
    // A multi-variant AI tab (v1.72) defaults to the best-scoring variant; the
    // user's own track choice is still restored from localStorage below.
    const variants =
      activeTab.meta && Array.isArray(activeTab.meta.variants)
        ? activeTab.meta.variants
        : [];
    if (variants.length) {
      const preferred = activeTab.meta.default_variant || variants[0].id;
      const entry =
        variants.find((item) => item.id === preferred) || variants[0];
      const track = Number(entry.track);
      if (Number.isInteger(track) && track >= 0 && track < allTracks.length) {
        visibleTrackIndexes = new Set([track]);
      }
    }
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

  // === SETTINGS (v2.02) =================================================
  // Values arrive from /api/settings. These functions only read numbers and
  // toggle body classes: the clock, the seek inverse and the audio adapter
  // never learn about them, and the count-in reads its duration inside
  // beginCountIn() alone (rule 07).
  function clampSetting(value, low, high, fallback) {
    const number = Number(value);
    if (!Number.isFinite(number)) return fallback;
    return Math.min(high, Math.max(low, number));
  }

  function applyLyricsStyle() {
    // Two document variables, read only by the lyric overlay CSS:
    //   --lyrics-scale   multiplies the clamp() font size (100 % = old size),
    //   --lyrics-offset  lifts the strip from the bottom edge in fullscreen.
    // A document style only: no audio write, no alphaTab call (rule 07).
    const factor = Math.min(4, Math.max(1, lyricsScale / 100));
    const offset = Math.min(600, Math.max(0, Math.round(lyricsOffset)));
    if (document.documentElement) {
      document.documentElement.style.setProperty(
        "--lyrics-scale",
        String(factor)
      );
      document.documentElement.style.setProperty(
        "--lyrics-offset",
        `${offset}px`
      );
    }
  }

  function applyUiVisibility(values) {
    for (const feature of UI_FEATURES) {
      const shown = values[`ui.${feature}`] !== false;
      document.body.classList.toggle(`hide-ui-${feature}`, !shown);
    }
  }

  function applyRuntimeSettings(values) {
    const settings = values || {};
    countInSteps = Math.round(
      clampSetting(settings["countin.steps"], 1, 12, COUNT_IN_FROM)
    );
    countInStepMs = Math.round(
      clampSetting(settings["countin.step_ms"], 200, 3000, COUNT_IN_STEP_MS)
    );
    countInZeroMs = Math.round(
      clampSetting(settings["countin.zero_ms"], 0, 2000, COUNT_IN_ZERO_MS)
    );
    defaultCountInEnabled = settings["countin.enabled"] !== false;
    // The lyric strip font and lift are CSS variables (v2.08–v2.09); the
    // defaults double the old size and lift the line 100 px in fullscreen.
    // Only document styles are written, never an audio/api value.
    lyricsScale = Math.round(
      clampSetting(
        settings["lyrics.scale"],
        100,
        400,
        LYRICS_SCALE_DEFAULT
      )
    );
    lyricsOffset = Math.round(
      clampSetting(
        settings["lyrics.offset_px"],
        0,
        600,
        LYRICS_OFFSET_DEFAULT
      )
    );
    // Sneak peek (v2.19): on unless the stored value is exactly false.
    lyricsSneak = settings["lyrics.sneak"] !== false;
    applyLyricsStyle();
    applyLyricsSneak();
    renderLyricsStrip(true);
    defaultStaveProfile = Object.prototype.hasOwnProperty.call(
      STAVE_PROFILES,
      settings["view.stave"]
    )
      ? settings["view.stave"]
      : null;
    applyUiVisibility(settings);
  }

  function applyStoredDefaults() {
    // A saved local choice always wins; the Settings value is only the default
    // for a browser that has never chosen (v2.02).
    try {
      if (localStorage.getItem(COUNT_IN_STORAGE_KEY) === null) {
        setCountInEnabled(defaultCountInEnabled, { persist: false });
      }
      if (
        localStorage.getItem(STAVE_STORAGE_KEY) === null &&
        defaultStaveProfile
      ) {
        applyStaveProfile(defaultStaveProfile, {
          persist: false,
          render: false,
        });
      }
    } catch (error) {
      /* storage disabled */
    }
  }

  async function loadRuntimeSettings() {
    try {
      const response = await fetch(SETTINGS_URL, { cache: "no-store" });
      if (!response.ok) return;
      const payload = await response.json();
      applyRuntimeSettings(payload && payload.values);
      applyStoredDefaults();
    } catch (error) {
      /* the built-in defaults keep the viewer usable */
    }
  }
  // === /SETTINGS ========================================================

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
      // alphaTab passes the *score* time (ms). Invert syncTimeMs() so the
      // audio position matches the cursor (click-to-seek and the engine's
      // own start/stop seeks). time === 0 (rewind/stop) is left as-is.
      let targetMs = time;
      if (time > 0) {
        const drift = 1 + syncDrift + bpmDrift();
        targetMs = (time - syncOffsetBars * barDurationMs()) / drift;
      }
      const target = Math.max(0, targetMs / 1000);
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
    const reported = Number(audio.currentTime) || 0;
    let position = syncTimeMs();
    // Keep the feed monotonic while the audio plays (v1.91). alphaTab applies
    // every fed value as the cursor position without any check, so a repeated
    // or slightly stale currentTime rewinds the cursor for a moment. The held
    // value is a position that was already computed from a real read, so the
    // clock is not moved ahead of the audio; the cursor only waits instead of
    // hopping back. Forced syncs (seek, pause, load, SIIRTO/SYNC) and a real
    // backwards seek reset the baseline, so rewind still works.
    const playing = !audio.paused && !audio.ended;
    const backwardsSeek =
      lastFedAudioS >= 0 && reported < lastFedAudioS - FEED_JITTER_S;
    if (force || !playing || backwardsSeek) {
      lastFedScoreMs = position;
    } else if (lastFedScoreMs >= 0 && position < lastFedScoreMs) {
      position = lastFedScoreMs;
    } else {
      lastFedScoreMs = position;
    }
    lastFedAudioS = reported;
    const output = api.player.output;
    if (output && typeof output.updatePosition === "function") {
      output.updatePosition(position);
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
          // Horizontal/vertical score margin. alphaTab sizes its
          // .at-surface from the container's offsetWidth and draws the
          // score inside this padding, so the viewer element must stay
          // padding/border free (see .alphatab in style.css, v1.57).
          // 30 px horizontal leaves the 15 px scrollbar its own lane in
          // the right margin instead of running over the score (v1.58).
          padding: [30, 15],
          // Dark score: light glyphs and muted staff lines on the dark
          // .alphatab surface (hex strings are parsed by alphaTab's Color).
          resources: {
            mainGlyphColor: "#e9edf5",
            secondaryGlyphColor: "#aab4c4",
            staffLineColor: "#4a5361",
            barSeparatorColor: "#6b7482",
            barNumberColor: "#f0b35a",
            scoreInfoColor: "#e9edf5",
          },
        },
        player: {
          playerMode: alphaTab.PlayerMode.EnabledExternalMedia,
          enableCursor: true,
          // The animated beat cursor extrapolates the cursor past the next
          // beat (CSS transition), so during playback it visually runs ahead
          // of the audio and snaps back on pause. Disable it: the cursor then
          // jumps to the exact tickPosition on every 50 ms sync update.
          enableAnimatedBeatCursor: false,
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
    if (api.beatMouseDown && typeof api.beatMouseDown.on === "function") {
      api.beatMouseDown.on(handleAlignClick);
    }
    return api;
  }

  function togglePlayback() {
    if (playButton && playButton.disabled) return;
    // v2.05: PLAY only starts or pauses playback. Fullscreen is the separate
    // FULLSCREEN button, so the play path never changes the viewport (the
    // clock, seekTo inverse and audio events stay untouched).
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

  // === COUNT-IN (v1.55) – UI only, rule 07 ============================
  // The countdown runs once per tab load, before the first playback. It owns
  // nothing but its own overlay: no audio writes, no alphaTab calls and no
  // changes to the playback chain. Playback starts by calling the unchanged
  // togglePlayback() exactly once, so the sync path stays identical.
  function drawCountIn(value) {
    if (!playCountdown) return;
    if (value === null) {
      playCountdown.hidden = true;
      return;
    }
    if (playCountdownValue) playCountdownValue.textContent = String(value);
    playCountdown.hidden = false;
  }

  function shouldRunCountIn() {
    if (!playButton || playButton.disabled) return false;
    if (countInDone) return false;
    // The switch under FULLSCREEN turns the countdown off (default on). It is
    // read here only, so the playback chain itself never learns about it.
    if (!countInEnabled) return false;
    // alphaTab pre-positions the audio on the first beat while loading
    // (~0.85 s with SIIRTO −0,75), so audio.currentTime cannot tell a user
    // seek apart from the engine's own initial seek. Only an explicit UI
    // seek before the first PLAY skips the countdown (documented choice).
    return !countInSkipped;
  }

  function cancelCountIn() {
    if (countInTimer) window.clearInterval(countInTimer);
    if (countInZeroTimer) window.clearTimeout(countInZeroTimer);
    countInTimer = null;
    countInZeroTimer = null;
    countInActive = false;
    drawCountIn(null);
  }

  function readCountInEnabled() {
    // The ON/OFF switch stores its own value; the Settings view only supplies
    // the default for a browser that has never touched the switch (v2.02).
    try {
      const stored = localStorage.getItem(COUNT_IN_STORAGE_KEY);
      if (stored === "on") return true;
      if (stored === "off") return false;
    } catch (error) {
      return defaultCountInEnabled;
    }
    return defaultCountInEnabled;
  }

  function setCountInEnabled(enabled, options) {
    const settings = options || {};
    countInEnabled = Boolean(enabled);
    if (countInToggle && countInToggle.checked !== countInEnabled) {
      countInToggle.checked = countInEnabled;
    }
    if (countInState) countInState.textContent = countInEnabled ? "ON" : "OFF";
    if (!countInEnabled && countInActive) cancelCountIn();
    if (settings.persist === false) return;
    try {
      localStorage.setItem(COUNT_IN_STORAGE_KEY, countInEnabled ? "on" : "off");
    } catch (error) {
      /* storage disabled */
    }
  }

  function finishCountIn() {
    if (!countInActive) return;
    cancelCountIn();
    countInDone = true;
    // Restore the audio position captured at PLAY: a FULLSCREEN press during
    // the countdown can re-render the score and move the audio off the start,
    // so the delayed PLAY would begin at the wrong spot. The restored value was
    // read from the audio itself, so it is a no-op when nothing moved (v1.92).
    if (Number.isFinite(countInAudioTime)) {
      audio.currentTime = countInAudioTime;
    }
    togglePlayback();
  }

  function beginCountIn() {
    // Without the overlay the countdown would be invisible; never delay
    // playback silently. The caller falls back to a normal PLAY.
    if (!playCountdown) return false;
    cancelCountIn();
    countInActive = true;
    countInValue = countInSteps;
    drawCountIn(countInValue);
    countInTimer = window.setInterval(() => {
      countInValue -= 1;
      if (countInValue > 0) {
        drawCountIn(countInValue);
        return;
      }
      window.clearInterval(countInTimer);
      countInTimer = null;
      drawCountIn(0);
      countInZeroTimer = window.setTimeout(finishCountIn, countInZeroMs);
    }, countInStepMs);
    return true;
  }

  function handlePlayButton() {
    if (countInActive) {
      // Second PLAY cancels; the count-in stays pending for the next press.
      cancelCountIn();
      return;
    }
    // The score end is held back (SCORE_END_GUARD_MS), so alphaTab no longer
    // stops itself when the tab runs out. Once the audio has reached its own
    // end, rewind once: PLAY then starts from the beginning instead of pausing
    // an engine that is still marked as playing.
    if (audio.ended && api && activeTab) {
      try {
        api.stop();
      } catch (error) {
        /* ignore a stopped player */
      }
    }
    const willPlay = playButton
      ? playButton.dataset.state !== "playing"
      : audio.paused;
    if (!willPlay) {
      togglePlayback();
      return;
    }
    if (shouldRunCountIn()) {
      // v2.05: the countdown no longer starts fullscreen. The audio position is
      // still captured, because pressing FULLSCREEN during the countdown
      // re-renders the score and can move the audio (v1.92 restore).
      countInAudioTime = Number(audio.currentTime) || 0;
      if (beginCountIn()) return;
    }
    countInDone = true;
    togglePlayback();
  }
  // === /COUNT-IN ======================================================

  // === SANAT (v2.06) ==================================================
  // Decoupled by design: the tab (GP5/MusicXML/MIDI) and its metadata are
  // never written here, and nothing in the playback chain (clock, seekTo
  // inverse, mediaHandler, syncPosition) is called or changed. The strip is
  // an overlay that watches #bar-readout, which the transport already keeps
  // up to date, and paints the sidecar line for that bar.
  function lyricForBar(bar) {
    // v2.18: an empty bar is cleared instead of holding the previous line.
    // If a later line exists, the strip counts down to it (9, 8, … 1), so a
    // gap becomes the singer's cue for when the words continue. After the
    // last line there is no cue and the strip hides.
    const start = Number(bar) || 0;
    if (!start) return "";
    const text = lyricsMeasures[String(start)];
    if (text) return text;
    const next = nextLyricBar(start);
    return next ? String(next - start) : "";
  }

  function nextLyricBar(bar) {
    // The first stored line after this bar, or 0 when the song has no more.
    const start = Number(bar) || 0;
    let next = 0;
    Object.keys(lyricsMeasures).forEach((key) => {
      const value = Number(key);
      if (!Number.isFinite(value) || value <= start) return;
      if (!next || value < next) next = value;
    });
    return next;
  }

  function lyricPeekForBar(bar) {
    // v2.19: the next line, shown one bar early in the smaller band. Only one
    // bar ahead, so a long instrumental gap stays clean (the main strip has
    // the countdown for that). Reads the same sidecar map; DOM only.
    if (!lyricsSneak) return "";
    const start = Number(bar) || 0;
    if (!start) return "";
    const next = nextLyricBar(start);
    if (!next || next - start !== 1) return "";
    return String(lyricsMeasures[String(next)] || "");
  }

  function currentLyricsBar() {
    if (!barReadout) return 0;
    const match = /Tahti\s+(\d+)/.exec(barReadout.textContent || "");
    return match ? Number(match[1]) : 0;
  }

  function renderLyricsStrip(force) {
    if (!lyricsStrip || !lyricsCurrent) return;
    const bar = currentLyricsBar();
    if (!force && bar === lyricsShownBar) return;
    const moved = bar !== lyricsShownBar;
    lyricsShownBar = bar;
    const text = lyricForBar(bar);
    // A number is a cue, not a lyric: paint it in the accent colour (colour
    // only, so the band keeps its size).
    const isCue = Boolean(text) && !lyricsMeasures[String(bar)];
    lyricsCurrent.textContent = text;
    lyricsCurrent.classList.toggle("is-cue", isCue);
    // v2.19: the next line is previewed one bar early in a smaller band.
    // The band keeps its space (is-empty = invisible), so the main line does
    // not jump up and down when a gap starts.
    const peek = lyricPeekForBar(bar);
    if (lyricsNext) {
      lyricsNext.textContent = peek;
      lyricsNext.classList.toggle("is-empty", !peek);
    }
    lyricsStrip.hidden = !text;
    markLyricsPlayingBar(bar, moved);
  }

  function markLyricsPlayingBar(bar, moved) {
    // A read-only helper for the floating editor: the bar number comes from
    // the same #bar-readout the transport already writes.
    if (lyricsBarBadge) {
      lyricsBarBadge.textContent = bar ? `Tahti ${bar}` : "Tahti –";
    }
    if (!lyricsBars || !lyricsBars.children.length) return;
    let current = null;
    Array.from(lyricsBars.children).forEach((chip) => {
      const isCurrent = bar > 0 && Number(chip.dataset.bar) === bar;
      chip.classList.toggle("is-current", isCurrent);
      if (isCurrent) current = chip;
    });
    if (current && moved) {
      // Scroll only the chip list, never the page: the panel is fixed and the
      // transport behind it must not jump while the song plays.
      const top = current.offsetTop;
      const bottom = top + current.offsetHeight;
      if (top < lyricsBars.scrollTop) {
        lyricsBars.scrollTop = Math.max(0, top - 4);
      } else if (bottom > lyricsBars.scrollTop + lyricsBars.clientHeight) {
        lyricsBars.scrollTop = bottom - lyricsBars.clientHeight + 4;
      }
    }
  }

  function resetLyrics() {
    lyricsTabId = "";
    lyricsMeasures = {};
    lyricsBarsTotal = 0;
    lyricsShownBar = -1;
    lyricsLocked = false;
    lyricsNotes = "";
    if (lyricsNotesInput) lyricsNotesInput.value = "";
    applyLyricsLock();
    renderLyricsStrip(true);
  }

  function setLyricsStatus(text, isError) {
    if (!lyricsStatus) return;
    lyricsStatus.textContent = text;
    lyricsStatus.classList.toggle("is-error", Boolean(isError));
  }

  function applyLyricsSneak() {
    // v2.19: the peek band reserves its space only when the setting is on, so
    // switching it off returns the strip to the pre-v2.19 height. DOM only.
    if (lyricsStrip) lyricsStrip.classList.toggle("has-peek", lyricsSneak);
  }

  async function loadLyrics(tabId) {
    const id = String(tabId || "");
    if (!id) {
      resetLyrics();
      return;
    }
    if (lyricsLoadingFor === id) return;
    lyricsLoadingFor = id;
    try {
      const response = await fetch(`/api/tabs/${id}/lyrics`, {
        cache: "no-store",
      });
      if (!response.ok) throw new Error("Sanojen luku epäonnistui.");
      const payload = await response.json();
      if (lyricsLoadingFor !== id) return;
      lyricsTabId = id;
      lyricsMeasures =
        payload && payload.measures && typeof payload.measures === "object"
          ? payload.measures
          : {};
      lyricsBarsTotal = Number(payload && payload.bars) || 0;
      lyricsShownBar = -1;
      lyricsLocked = Boolean(payload && payload.locked);
      lyricsNotes = String((payload && payload.notes) || "");
      applyLyricsLock();
      renderLyricsStrip(true);
      // A fetch that lands after the user started typing must not overwrite
      // the edit; the save button is the only writer of the sidecar.
      if (lyricsDialog && !lyricsDialog.hidden && !lyricsDirty) {
        fillLyricsDialog();
      }
    } catch (error) {
      if (lyricsLoadingFor !== id) return;
      lyricsTabId = id;
      lyricsMeasures = {};
      lyricsShownBar = -1;
      lyricsLocked = false;
      lyricsNotes = "";
      if (lyricsNotesInput && !lyricsDirty) lyricsNotesInput.value = "";
      applyLyricsLock();
      renderLyricsStrip(true);
    } finally {
      if (lyricsLoadingFor === id) lyricsLoadingFor = "";
    }
  }

  function parseLyricsText(text) {
    // "10 | text" is the canonical form; ":", "=" and a tab also work.
    // A bare line continues from the previous bar (10, 11, 12 ...), so a
    // pasted block can be mapped line by line.
    const measures = {};
    const errors = [];
    let nextBar = 0;
    String(text || "")
      .split(/\r?\n/)
      .forEach((line, index) => {
        const raw = line.trim();
        if (!raw || raw.startsWith("#")) return;
        const match = /^(\d+)\s*[|:=\t]\s*(.+)$/.exec(raw);
        let bar = 0;
        let lyric = "";
        if (match) {
          bar = Number(match[1]);
          lyric = match[2].trim();
        } else if (nextBar) {
          bar = nextBar;
          lyric = raw;
        } else {
          errors.push(`Rivi ${index + 1}: aloita muodossa "tahti | teksti".`);
          return;
        }
        if (!Number.isFinite(bar) || bar < 1 || bar > 10000) {
          errors.push(`Rivi ${index + 1}: tahdin numero ei kelpaa.`);
          return;
        }
        if (!lyric) return;
        measures[String(bar)] = lyric;
        nextBar = bar + 1;
      });
    return { measures, errors };
  }

  function formatLyricsText(measures) {
    return Object.keys(measures || {})
      .sort((left, right) => Number(left) - Number(right))
      .map((bar) => `${bar} | ${measures[bar]}`)
      .join("\n");
  }

  function markLyricsBars() {
    if (!lyricsBars) return;
    const parsed = parseLyricsText(lyricsInput ? lyricsInput.value : "");
    Array.from(lyricsBars.children).forEach((chip) => {
      chip.classList.toggle(
        "has-text",
        Boolean(parsed.measures[chip.dataset.bar])
      );
    });
  }

  function insertLyricsBar(bar) {
    if (!lyricsInput || lyricsLocked) return;
    const text = lyricsInput.value;
    const separator = !text || text.endsWith("\n") ? "" : "\n";
    lyricsInput.value = `${text}${separator}${bar} | `;
    lyricsInput.focus();
    const end = lyricsInput.value.length;
    lyricsInput.setSelectionRange(end, end);
    lyricsLineSelection = null;
    markLyricsBars();
  }

  function lyricsBarLineRange(text, bar) {
    // v2.16: the field is one line per bar ("95 | text") and a bare line
    // continues from the previous bar (same rule as parseLyricsText). Returns
    // the offsets of the lyric text alone, so the "95 | " prefix survives if
    // the highlighted words are replaced. Pure string work, no DOM.
    const target = Math.round(Number(bar) || 0);
    if (!target) return null;
    let nextBar = 0;
    let offset = 0;
    for (const line of String(text == null ? "" : text).split("\n")) {
      const lineStart = offset;
      offset += line.length + 1;
      const raw = line.trim();
      if (!raw || raw.startsWith("#")) continue;
      const match = /^(\d+)\s*[|:=\t]\s*(.+)$/.exec(raw);
      const lineBar = match ? Number(match[1]) : nextBar;
      if (!Number.isFinite(lineBar) || lineBar < 1 || lineBar > 10000) continue;
      if (lineBar === target) {
        const lead = line.length - line.trimStart().length;
        const value = match ? match[2] : raw;
        const start = lineStart + lead + (raw.length - value.length);
        // A bare line is only a continuation of the previous number; it has
        // no prefix of its own yet (v2.17), so it can still be formatted.
        return {
          start: start,
          end: start + value.length,
          numbered: Boolean(match),
        };
      }
      nextBar = lineBar + 1;
    }
    return null;
  }

  function focusLyricsBarLine(bar) {
    // v2.16: pressing bar 95 also selects its "95 | …" line, so a line can be
    // checked or rewritten without hunting for it in the field. DOM only: the
    // field is a sidecar editor and the transport keeps its own state.
    if (!lyricsInput) return false;
    const range = lyricsBarLineRange(lyricsInput.value, bar);
    if (!range) return false;
    lyricsInput.focus({ preventScroll: true });
    lyricsInput.setSelectionRange(range.start, range.end);
    lyricsLineSelection = { start: range.start, end: range.end };
    // Scroll only the text field. Most engines bring the caret into view on
    // their own; this keeps the line visible when they do not.
    const lineHeight =
      Number.parseFloat(window.getComputedStyle(lyricsInput).lineHeight) || 18;
    const index =
      lyricsInput.value.slice(0, range.start).split("\n").length - 1;
    const top = index * lineHeight;
    if (top < lyricsInput.scrollTop) {
      lyricsInput.scrollTop = Math.max(0, top - lineHeight);
    } else if (
      top + lineHeight >
      lyricsInput.scrollTop + lyricsInput.clientHeight
    ) {
      lyricsInput.scrollTop = top + lineHeight - lyricsInput.clientHeight;
    }
    return true;
  }

  function normalizeLyricChunk(text) {
    // Words taken from a paste may still carry old numbers ("10 | …"), line
    // breaks or double spaces. Only the words are kept: one bar, one line.
    return String(text == null ? "" : text)
      .split(/\r?\n/)
      .map((line) =>
        line
          .replace(/^\s*\d+\s*[|:=\t]\s*/, "")
          .replace(/\s+/g, " ")
          .trim()
      )
      .filter(Boolean)
      .join(" ");
  }

  function expandLyricsSelection(text, start, end) {
    // v2.17: a consumed phrase takes its line with it, so no empty raw line
    // is left behind. The range is widened only when the selection covers the
    // whole visible line.
    const lineStart = text.lastIndexOf("\n", start - 1) + 1;
    let lineEnd = text.indexOf("\n", end);
    if (lineEnd === -1) lineEnd = text.length;
    if (
      !text.slice(lineStart, start).trim() &&
      !text.slice(end, lineEnd).trim()
    ) {
      if (lineEnd < text.length) return { start: lineStart, end: lineEnd + 1 };
      if (lineStart > 0) return { start: lineStart - 1, end: lineEnd };
      return { start: lineStart, end: lineEnd };
    }
    return { start: start, end: end };
  }

  function assignLyricsSelectionToBar(bar) {
    // v2.17: select words, press a bar (or Ctrl+Enter) -> the words become
    // that bar's line and the number comes from the press. The selected text
    // is removed from the field, so a pasted block is consumed phrase by
    // phrase and the rest stays selectable in place. DOM only: no alphaTab
    // call, no clock and no transport write.
    if (!lyricsInput) return false;
    if (lyricsLocked) return false;
    const number = Math.round(Number(bar) || 0);
    if (number < 1) return false;
    const value = lyricsInput.value;
    const start = lyricsInput.selectionStart;
    const end = lyricsInput.selectionEnd;
    if (!(end > start)) return false;
    if (
      lyricsLineSelection &&
      lyricsLineSelection.start === start &&
      lyricsLineSelection.end === end
    ) {
      return false;
    }
    const chunk = normalizeLyricChunk(value.slice(start, end));
    if (!chunk) return false;
    const target = lyricsBarLineRange(value, number);
    if (target && target.numbered && start >= target.start && end <= target.end) {
      return false;
    }
    // Only a numbered line already belongs to that bar. A bare continuation
    // line is still raw text, so it is formatted through the insert path.
    const occupied = target && target.numbered ? target : null;
    const consume = expandLyricsSelection(value, start, end);
    const prefix = `${number} | ${chunk}`;
    let next = value;
    let caret = 0;

    if (occupied) {
      // The bar already has words: keep its line and swap only the words,
      // then remove the consumed source text. The later edit runs first so
      // the offsets stay valid.
      if (consume.start >= occupied.end) {
        next = `${next.slice(0, consume.start)}${next.slice(consume.end)}`;
        next = `${next.slice(0, occupied.start)}${chunk}${next.slice(occupied.end)}`;
        caret = occupied.start + chunk.length;
      } else if (consume.end <= occupied.start) {
        next = `${next.slice(0, occupied.start)}${chunk}${next.slice(occupied.end)}`;
        next = `${next.slice(0, consume.start)}${next.slice(consume.end)}`;
        caret = occupied.start + chunk.length - (consume.end - consume.start);
      } else {
        return false;
      }
    } else {
      const before = value.slice(0, consume.start);
      const after = value.slice(consume.end);
      const lead = before && !before.endsWith("\n") ? "\n" : "";
      const tail = after && !after.startsWith("\n") ? "\n" : "";
      next = `${before}${lead}${prefix}${tail}${after}`;
      caret = before.length + lead.length + prefix.length;
    }
    lyricsInput.value = next;
    lyricsDirty = true;
    lyricsLineSelection = null;
    markLyricsBars();
    lyricsInput.focus({ preventScroll: true });
    lyricsInput.setSelectionRange(caret, caret);
    return true;
  }

  function lyricsLineRecords(text) {
    // One record per editor line. `numbered` is true only when the line really
    // starts with a bar number; a bare line continues the previous number
    // (same rule as parseLyricsText). Offsets let the bulk fill delete whole
    // lines without leaving empty gaps.
    const records = [];
    let nextBar = 0;
    let offset = 0;
    for (const line of String(text == null ? "" : text).split("\n")) {
      const lineStart = offset;
      offset += line.length + 1;
      const raw = line.trim();
      const match = raw ? /^(\d+)\s*[|:=\t]\s*(.+)$/.exec(raw) : null;
      const bar = match ? Number(match[1]) : raw && nextBar ? nextBar : 0;
      if (bar) nextBar = bar + 1;
      records.push({
        lineStart: lineStart,
        lineEnd: lineStart + line.length,
        raw: raw,
        numbered: Boolean(match),
        bar: bar,
      });
    }
    return records;
  }

  function wholeLineRange(record, length) {
    // Take the trailing newline with the line, so deleting it leaves no hole.
    if (record.lineEnd < length) {
      return { start: record.lineStart, end: record.lineEnd + 1 };
    }
    if (record.lineStart > 0) {
      return { start: record.lineStart - 1, end: record.lineEnd };
    }
    return { start: record.lineStart, end: record.lineEnd };
  }

  function removeTextRanges(text, ranges) {
    let out = "";
    let cursor = 0;
    ranges.forEach((range) => {
      out += text.slice(cursor, range.start);
      cursor = range.end;
    });
    return out + text.slice(cursor);
  }

  function handleLyricsBarClick(bar) {
    // A bar press is the anchor for Ctrl+Enter; with a selection it also
    // writes the words into that bar and moves the anchor one bar ahead.
    lyricsAnchorBar = bar;
    if (assignLyricsSelectionToBar(bar)) {
      lyricsAnchorBar = bar + 1;
      return;
    }
    focusLyricsBarLine(bar);
  }

  function assignLyricsBlockToBars(bar) {
    // v2.22: one selected line per bar, numbered from the pressed bar. A
    // pasted block becomes a draft in one go; Ctrl+Enter still writes one
    // phrase into one bar. Already numbered lines of the target bars are
    // replaced, so no bar gets two lines. DOM/string work only.
    if (!lyricsInput || lyricsLocked) return false;
    const first = Math.round(Number(bar) || 0);
    if (first < 1) return false;
    const value = lyricsInput.value;
    const length = value.length;
    const records = lyricsLineRecords(value);
    const hasSelection = lyricsInput.selectionEnd > lyricsInput.selectionStart;
    const selStart = hasSelection ? lyricsInput.selectionStart : 0;
    const selEnd = hasSelection ? lyricsInput.selectionEnd : 0;
    const consumed = [];
    let lines = [];
    if (hasSelection) {
      consumed.push(expandLyricsSelection(value, selStart, selEnd));
      lines = value
        .slice(selStart, selEnd)
        .split(/\r?\n/)
        .map((line) => normalizeLyricChunk(line))
        .filter(Boolean);
    } else {
      records.forEach((record) => {
        if (record.numbered || !record.raw || record.raw.startsWith("#")) return;
        lines.push(normalizeLyricChunk(record.raw));
        consumed.push(wholeLineRange(record, length));
      });
    }
    lines = lines.filter(Boolean);
    if (!lines.length) return false;
    const last = first + lines.length - 1;
    if (last > 10000) return false;
    const insertAt = consumed.length ? consumed[0].start : 0;
    const ranges = consumed.slice();
    records.forEach((record) => {
      if (!record.numbered) return;
      if (record.bar < first || record.bar > last) return;
      // A line that overlaps the picked text is already being consumed; any
      // other line for a target bar is replaced by the new block.
      if (hasSelection && record.lineStart < selEnd && selStart < record.lineEnd) {
        return;
      }
      ranges.push(wholeLineRange(record, length));
    });
    ranges.sort((left, right) => left.start - right.start);
    const merged = [];
    ranges.forEach((range) => {
      const previous = merged[merged.length - 1];
      if (previous && range.start <= previous.end) {
        previous.end = Math.max(previous.end, range.end);
      } else {
        merged.push({ start: range.start, end: range.end });
      }
    });
    let at = insertAt;
    let removed = 0;
    merged.forEach((range) => {
      if (range.end <= at) {
        removed += range.end - range.start;
        return;
      }
      if (range.start < at) at = range.start;
    });
    at = Math.max(0, at - removed);
    const stripped = removeTextRanges(value, merged);
    const block = lines
      .map((text, index) => `${first + index} | ${text}`)
      .join("\n");
    const before = stripped.slice(0, at);
    const after = stripped.slice(at);
    const lead = before && !before.endsWith("\n") ? "\n" : "";
    const tail = after && !after.startsWith("\n") ? "\n" : "";
    lyricsInput.value = `${before}${lead}${block}${tail}${after}`;
    lyricsDirty = true;
    lyricsLineSelection = null;
    lyricsAnchorBar = last + 1;
    markLyricsBars();
    lyricsInput.focus({ preventScroll: true });
    const caret = before.length + lead.length + block.length;
    lyricsInput.setSelectionRange(caret, caret);
    return true;
  }

  function fillLyricsFromSelection() {
    const bar = lyricsAnchorBar || currentLyricsBar() || 1;
    if (assignLyricsBlockToBars(bar)) return true;
    setLyricsStatus(
      "Ei numeroimattomia rivejä. Maalaa rivit tai liitä teksti kenttään.",
      true
    );
    return false;
  }

  function handleLyricsAssignKey(event) {
    // Ctrl+Enter: the same as pressing the anchor bar, so consecutive phrases
    // get consecutive numbers without leaving the keyboard. Ctrl+Shift+Enter
    // numbers a whole block, one line per bar (v2.22).
    if (event.key !== "Enter" || !(event.ctrlKey || event.metaKey)) return;
    event.preventDefault();
    if (event.shiftKey) {
      fillLyricsFromSelection();
      return;
    }
    const bar = lyricsAnchorBar || currentLyricsBar() || 1;
    if (assignLyricsSelectionToBar(bar)) lyricsAnchorBar = bar + 1;
  }

  function jumpToBar(bar) {
    // Press a bar number to put the song, the tab and the cursor there.
    // alphaTab owns the tempo map (Seek & Destroy changes tempo at bar 113),
    // so the bar is given to it as a *tick*: the engine converts the tick to
    // score time with the tempo changes, maps that onto the backing track and
    // calls the frozen mediaHandler.seekTo() inverse itself (v2.14). A time
    // computed here from a constant tempo drifted after any automation.
    if (!api || !activeTab) return false;
    const bars =
      api.score && Array.isArray(api.score.masterBars)
        ? api.score.masterBars
        : null;
    if (!bars || !bars.length) return false;
    const number = Math.max(1, Math.round(Number(bar) || 1));
    const index = Math.min(number, bars.length) - 1;
    const startTick = Number(bars[index].start) || 0;
    clearPlaybackRange();
    try {
      api.tickPosition = startTick;
    } catch (error) {
      return false;
    }
    syncPosition(true);
    updateTransport();
    window.setTimeout(scrollScoreToCursor, 80);
    return true;
  }

  function syncLyricsPlayLabel() {
    // Mirror the real PLAY button (which already owns the label) instead of
    // adding another audio listener: no new coupling to the chain.
    if (!lyricsPlayButton || !playButton) return;
    const playing = playButton.dataset.state === "playing";
    lyricsPlayButton.textContent = playing ? "PAUSE" : "PLAY";
    lyricsPlayButton.dataset.state = playing ? "playing" : "paused";
  }

  function renderLyricsBars(count) {
    if (!lyricsBars) return;
    lyricsBars.textContent = "";
    // A tab with hundreds of bars would be an unusable wall of chips; the
    // first 400 are clickable and the editor accepts any bar number anyway.
    const total = Math.min(Math.max(Number(count) || 0, 1), 400);
    for (let bar = 1; bar <= total; bar += 1) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "lyrics-bar";
      chip.dataset.bar = String(bar);
      chip.textContent = String(bar);
      chip.title = `Hyppää tahtiin ${bar}. Maalatut sanat siirretään tähän tahtiin. Kaksoisklikkaus lisää rivin.`;
      // Click = seek, double-click = start a line for that bar (v2.12).
      // v2.16–v2.17: the same click selects the matching "tahti | teksti"
      // line, or writes the selected words into that bar.
      chip.addEventListener("click", () => jumpToBar(bar));
      chip.addEventListener("click", () => handleLyricsBarClick(bar));
      chip.addEventListener("dblclick", () => insertLyricsBar(bar));
      lyricsBars.appendChild(chip);
    }
    markLyricsBars();
  }

  function fillLyricsDialog() {
    if (lyricsInput) lyricsInput.value = formatLyricsText(lyricsMeasures);
    lyricsDirty = false;
    lyricsAnchorBar = 0;
    lyricsLineSelection = null;
    if (lyricsNotesInput) lyricsNotesInput.value = lyricsNotes;
    if (lyricsSubject) {
      lyricsSubject.textContent = activeTab
        ? activeTab.artist
          ? `${activeTab.artist} — ${activeTab.title}`
          : String(activeTab.title || "")
        : "";
    }
    const total =
      lyricsBarsTotal || Number(activeTab && activeTab.measure_count) || 0;
    renderLyricsBars(total);
    applyLyricsLock();
    setLyricsStatus("");
  }

  // --- floating panel (v2.07) -----------------------------------------
  // The editor is a plain fixed panel: it never adds body.modal-open, so the
  // playback cursor stays visible and PLAY/seek behind it keep working. All
  // of this is DOM only, so the rule 07 boundary still holds.
  function clampPixels(value, low, high) {
    if (!Number.isFinite(value)) return low;
    return Math.min(Math.max(value, low), high);
  }

  function placeLyricsPanel(left, top) {
    if (!lyricsDialog) return;
    const width = lyricsDialog.offsetWidth || 640;
    const height = lyricsDialog.offsetHeight || 480;
    const maxLeft = Math.max(8, window.innerWidth - width - 8);
    const maxTop = Math.max(8, window.innerHeight - height - 8);
    lyricsDialog.style.transform = "none";
    lyricsDialog.style.left = `${Math.round(clampPixels(left, 8, maxLeft))}px`;
    lyricsDialog.style.top = `${Math.round(clampPixels(top, 8, maxTop))}px`;
  }

  function sizeLyricsPanel(width, height) {
    if (!lyricsDialog) return;
    const maxWidth = Math.max(320, window.innerWidth - 16);
    const maxHeight = Math.max(260, window.innerHeight - 16);
    lyricsDialog.style.width = `${Math.round(
      clampPixels(width, 360, maxWidth)
    )}px`;
    lyricsDialog.style.height = `${Math.round(
      clampPixels(height, 280, maxHeight)
    )}px`;
  }

  function readLyricsPanelPosition() {
    try {
      const raw = JSON.parse(localStorage.getItem(LYRICS_POS_KEY) || "null");
      if (raw && Number.isFinite(raw.left) && Number.isFinite(raw.top)) {
        return raw;
      }
    } catch (error) {
      /* storage disabled */
    }
    return null;
  }

  function saveLyricsPanelPosition() {
    if (!lyricsDialog) return;
    try {
      localStorage.setItem(
        LYRICS_POS_KEY,
        JSON.stringify({
          left: Math.round(lyricsDialog.offsetLeft),
          top: Math.round(lyricsDialog.offsetTop),
          width: Math.round(lyricsDialog.offsetWidth),
          height: Math.round(lyricsDialog.offsetHeight),
          barsHeight: lyricsBars
            ? Math.round(lyricsBars.getBoundingClientRect().height)
            : LYRICS_BARS_DEFAULT,
        })
      );
    } catch (error) {
      /* storage disabled */
    }
  }

  function startLyricsDrag(event) {
    if (!lyricsDialog) return;
    if (event.button !== undefined && event.button !== 0) return;
    event.preventDefault();
    const rect = lyricsDialog.getBoundingClientRect();
    lyricsDrag = {
      dx: event.clientX - rect.left,
      dy: event.clientY - rect.top,
    };
    if (lyricsHandle && typeof lyricsHandle.setPointerCapture === "function") {
      try {
        lyricsHandle.setPointerCapture(event.pointerId);
      } catch (error) {
        /* the pointer may already be gone */
      }
    }
  }

  function moveLyricsDrag(event) {
    if (!lyricsDrag) return;
    placeLyricsPanel(
      event.clientX - lyricsDrag.dx,
      event.clientY - lyricsDrag.dy
    );
  }

  function endLyricsDrag() {
    if (!lyricsDrag) return;
    lyricsDrag = null;
    saveLyricsPanelPosition();
  }

  function startLyricsResize(event) {
    if (!lyricsDialog) return;
    if (event.button !== undefined && event.button !== 0) return;
    const grip = event.currentTarget;
    const corner = (grip && grip.dataset && grip.dataset.corner) || "se";
    event.preventDefault();
    const rect = lyricsDialog.getBoundingClientRect();
    lyricsResize = {
      corner,
      startX: event.clientX,
      startY: event.clientY,
      left: rect.left,
      top: rect.top,
      width: rect.width,
      height: rect.height,
    };
    if (grip && typeof grip.setPointerCapture === "function") {
      try {
        grip.setPointerCapture(event.pointerId);
      } catch (error) {
        /* the pointer may already be gone */
      }
    }
  }

  function moveLyricsResize(event) {
    if (!lyricsResize) return;
    const dx = event.clientX - lyricsResize.startX;
    const dy = event.clientY - lyricsResize.startY;
    const maxWidth = Math.max(320, window.innerWidth - 16);
    const maxHeight = Math.max(260, window.innerHeight - 16);
    let width = lyricsResize.width;
    let height = lyricsResize.height;
    let left = lyricsResize.left;
    let top = lyricsResize.top;
    if (lyricsResize.corner === "nw") {
      // The top-left grip keeps the bottom-right edge in place: the panel
      // grows left/up while the position follows the pointer.
      width = clampPixels(lyricsResize.width - dx, 360, maxWidth);
      height = clampPixels(lyricsResize.height - dy, 280, maxHeight);
      left = lyricsResize.left + (lyricsResize.width - width);
      top = lyricsResize.top + (lyricsResize.height - height);
    } else {
      width = clampPixels(lyricsResize.width + dx, 360, maxWidth);
      height = clampPixels(lyricsResize.height + dy, 280, maxHeight);
    }
    sizeLyricsPanel(width, height);
    // Clamping the position also keeps a grown panel inside the window, and
    // a shrunk panel must not keep an oversized bar list.
    if (lyricsBars) {
      setLyricsBarsHeight(lyricsBars.getBoundingClientRect().height);
    }
    placeLyricsPanel(left, top);
  }

  function endLyricsResize() {
    if (!lyricsResize) return;
    lyricsResize = null;
    // A shrunken panel may no longer fit the stored bar-list height.
    if (lyricsBars) {
      setLyricsBarsHeight(lyricsBars.getBoundingClientRect().height);
    }
    saveLyricsPanelPosition();
  }

  function setLyricsBarsHeight(height) {
    // The bar list and the text field share the panel height: a taller list
    // means a shorter textarea (v2.13). Only a style is written.
    if (!lyricsBars || !lyricsDialog) return;
    const available = Math.max(120, lyricsDialog.clientHeight - 220);
    const next = clampPixels(
      Number(height) || LYRICS_BARS_DEFAULT,
      80,
      available
    );
    lyricsBars.style.height = `${Math.round(next)}px`;
  }

  function startLyricsSplit(event) {
    if (!lyricsBars || !lyricsDialog) return;
    if (event.button !== undefined && event.button !== 0) return;
    event.preventDefault();
    lyricsSplitDrag = {
      startY: event.clientY,
      height: lyricsBars.getBoundingClientRect().height,
    };
    if (lyricsSplitter && typeof lyricsSplitter.setPointerCapture === "function") {
      try {
        lyricsSplitter.setPointerCapture(event.pointerId);
      } catch (error) {
        /* the pointer may already be gone */
      }
    }
  }

  function moveLyricsSplit(event) {
    if (!lyricsSplitDrag) return;
    setLyricsBarsHeight(
      lyricsSplitDrag.height + (event.clientY - lyricsSplitDrag.startY)
    );
  }

  function endLyricsSplit() {
    if (!lyricsSplitDrag) return;
    lyricsSplitDrag = null;
    saveLyricsPanelPosition();
  }

  function showLyricsPanel() {
    if (!lyricsDialog) return;
    const saved = readLyricsPanelPosition();
    if (saved) {
      if (
        Number.isFinite(saved.width) &&
        Number.isFinite(saved.height) &&
        saved.width > 0 &&
        saved.height > 0
      ) {
        sizeLyricsPanel(saved.width, saved.height);
      }
      placeLyricsPanel(saved.left, saved.top);
      setLyricsBarsHeight(
        Number.isFinite(saved.barsHeight)
          ? saved.barsHeight
          : LYRICS_BARS_DEFAULT
      );
      return;
    }
    const width = lyricsDialog.offsetWidth || 640;
    placeLyricsPanel((window.innerWidth - width) / 2, 88);
    setLyricsBarsHeight(LYRICS_BARS_DEFAULT);
  }

  function openLyricsDialog() {
    if (!lyricsDialog || !activeTab) return;
    const tabId = String(activeTab.id || "");
    fillLyricsDialog();
    lyricsDialog.hidden = false;
    // No backdrop and no modal-open (v2.07): the transport, the score and the
    // cursor stay usable while the lines are placed by ear.
    showLyricsPanel();
    markLyricsPlayingBar(currentLyricsBar(), false);
    syncLyricsPlayLabel();
    if (lyricsInput) lyricsInput.focus({ preventScroll: true });
    if (tabId && lyricsTabId !== tabId) loadLyrics(tabId);
  }

  function closeLyricsDialog() {
    if (!lyricsDialog) return;
    lyricsDialog.hidden = true;
    lyricsDrag = null;
    lyricsResize = null;
    setLyricsStatus("");
  }

  function applyLyricsLock() {
    // v2.18: the flag lives in the sidecar; this only mirrors it in the DOM.
    // A locked lyric stays readable and seekable, but the field is read-only
    // and TALLENNA is off until the box is cleared again.
    if (lyricsLockInput) lyricsLockInput.checked = lyricsLocked;
    if (lyricsInput) lyricsInput.readOnly = lyricsLocked;
    // The note belongs to the same sidecar, so the lock covers it too.
    if (lyricsNotesInput) lyricsNotesInput.readOnly = lyricsLocked;
    if (lyricsSave) lyricsSave.disabled = lyricsLocked;
    if (lyricsDialog) lyricsDialog.classList.toggle("is-locked", lyricsLocked);
  }

  async function saveLyrics(event) {
    event.preventDefault();
    await saveLyricsField();
  }

  async function saveLyricsField() {
    if (!activeTab || lyricsLocked) return false;
    const parsed = parseLyricsText(lyricsInput ? lyricsInput.value : "");
    if (parsed.errors.length) {
      setLyricsStatus(parsed.errors[0], true);
      return false;
    }
    if (lyricsSave) lyricsSave.disabled = true;
    setLyricsStatus("Tallennetaan…");
    try {
      const response = await fetch(`/api/tabs/${activeTab.id}/lyrics`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          measures: parsed.measures,
          // v2.20: the memo travels with the lines (and is kept when omitted).
          notes: lyricsNotesInput ? lyricsNotesInput.value : lyricsNotes,
        }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(
          payload && payload.detail
            ? String(payload.detail)
            : "Tallennus epäonnistui."
        );
      }
      const saved = await response.json();
      lyricsTabId = String(activeTab.id || "");
      lyricsMeasures =
        saved && saved.measures && typeof saved.measures === "object"
          ? saved.measures
          : parsed.measures;
      lyricsBarsTotal = Number(saved && saved.bars) || lyricsBarsTotal;
      // v2.20: the server trims the note, so the field shows the stored text.
      lyricsNotes =
        saved && typeof saved.notes === "string"
          ? saved.notes
          : String(lyricsNotesInput ? lyricsNotesInput.value : lyricsNotes);
      if (lyricsNotesInput) lyricsNotesInput.value = lyricsNotes;
      lyricsLocked = Boolean(saved && saved.locked);
      lyricsShownBar = -1;
      lyricsDirty = false;
      applyLyricsLock();
      renderLyricsStrip(true);
      markLyricsBars();
      setLyricsStatus(
        `Tallennettu (${Object.keys(lyricsMeasures).length} riviä).`
      );
      return true;
    } catch (error) {
      setLyricsStatus(
        error instanceof Error ? error.message : String(error),
        true
      );
      return false;
    } finally {
      if (lyricsSave) lyricsSave.disabled = lyricsLocked;
    }
  }

  async function toggleLyricsLock() {
    // A finished lyric is saved and locked in one step: otherwise ticking the
    // box would hide unsaved words behind a read-only field (v2.18).
    if (!lyricsLockInput || !activeTab) return;
    const want = Boolean(lyricsLockInput.checked);
    if (want === lyricsLocked) return;
    if (want && !(await saveLyricsField())) {
      lyricsLockInput.checked = false;
      return;
    }
    lyricsLockInput.disabled = true;
    try {
      const response = await fetch(`/api/tabs/${activeTab.id}/lyrics/lock`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ locked: want }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(
          payload && payload.detail
            ? String(payload.detail)
            : "Lukitus epäonnistui."
        );
      }
      const saved = await response.json();
      lyricsTabId = String(activeTab.id || "");
      lyricsLocked = Boolean(saved && saved.locked);
      if (saved && saved.measures && typeof saved.measures === "object") {
        lyricsMeasures = saved.measures;
      }
      lyricsDirty = false;
      lyricsShownBar = -1;
      applyLyricsLock();
      renderLyricsStrip(true);
      markLyricsBars();
      setLyricsStatus(lyricsLocked ? "Sanat lukittu." : "Lukitus avattu.");
    } catch (error) {
      lyricsLockInput.checked = lyricsLocked;
      setLyricsStatus(
        error instanceof Error ? error.message : String(error),
        true
      );
    } finally {
      lyricsLockInput.disabled = false;
    }
  }

  function watchLyrics() {
    if (typeof MutationObserver !== "function") return;
    // A new tab changes the title; the readout changes while the transport
    // runs. Both are read-only observations of UI that already exists, so
    // the playback chain is not connected to lyrics in any way.
    if (titleEl) {
      const titleObserver = new MutationObserver(() => {
        const tabId = activeTab && activeTab.id ? String(activeTab.id) : "";
        if (!tabId) {
          resetLyrics();
          return;
        }
        if (tabId !== lyricsTabId) loadLyrics(tabId);
        lyricsShownBar = -1;
        renderLyricsStrip(true);
      });
      titleObserver.observe(titleEl, {
        childList: true,
        characterData: true,
        subtree: true,
      });
    }
    if (barReadout) {
      const barObserver = new MutationObserver(() => renderLyricsStrip(false));
      barObserver.observe(barReadout, {
        childList: true,
        characterData: true,
        subtree: true,
      });
    }
    if (playButton) {
      // The editor's PLAY/PAUSE mirrors the real button, so no audio listener
      // is added anywhere (the chain stays exactly as it is).
      const playObserver = new MutationObserver(() => syncLyricsPlayLabel());
      playObserver.observe(playButton, {
        childList: true,
        characterData: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["data-state"],
      });
    }
  }
  // === /SANAT =========================================================

  function renderTabMeta(tab) {
    if (titleEl) {
      titleEl.textContent = tab.artist
        ? `${tab.artist} — ${tab.title}`
        : tab.title;
    }
    if (metaEl) {
      const meta = tab.meta || {};
      const tuningText =
        meta.tuning_override ||
        meta.tuning_label ||
        (meta.tuning ? String(meta.tuning) : "");
      const parts = [];
      // Tuning first: it is the thing you must remember before playing.
      if (tuningText) parts.push(tuningText);
      parts.push(
        `${formatBpm(tab.bpm)} BPM`,
        `${tab.measure_count} bars`,
        `${tab.note_count} notes`
      );
      // Keep the YouTube upload visible: a GP5 tab may only fit one upload.
      if (meta.youtube_channel) parts.push(`YT: ${meta.youtube_channel}`);
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
    // The count-in is per tab: switching tabs cancels it and re-arms it.
    cancelCountIn();
    countInDone = false;
    countInSkipped = false;
    try {
      const response = await fetch(`/api/tabs/${tabId}`, { cache: "no-store" });
      if (!response.ok) return;
      const tab = await response.json();
      activeTab = tab;
      allTracks = [];
      visibleTrackIndexes = new Set();
      sliderSeeking = false;
      if (alignArmed) disarmAlign();
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
      applyLockState();
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
    if (tab.tuning_label && (tab.tuning_override || tab.tuning !== "standard")) {
      parts.push(tab.tuning_label);
    }
    if (tab.source_type === "import") parts.push("tuotu tabi");
    if (tab.channel) parts.push(`YT: ${tab.channel}`);
    const created = formatTimestamp(tab.created_at);
    if (created) parts.push(created);
    return parts.join(" · ");
  }

  // Bands first: the library is alphabetical by artist (band name), with the
  // song title as the tiebreaker.
  function librarySortKey(tab) {
    return `${String(tab.artist || "")} ${String(tab.title || tab.id || "")}`.trim();
  }

  function sortLibraryTabs(tabs) {
    return tabs.slice().sort((left, right) =>
      librarySortKey(left).localeCompare(librarySortKey(right), "fi", {
        numeric: true,
        sensitivity: "base",
      })
    );
  }

  function libraryButton(label, className, title) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.textContent = label;
    if (title) button.title = title;
    return button;
  }

  function libraryFlag(labelText, checked, onChange, options) {
    const settings = options || {};
    const label = document.createElement("label");
    label.className = "library-flag";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = Boolean(checked);
    input.disabled = Boolean(settings.disabled);
    if (settings.disabled) label.title = LOCKED_HINT;
    input.addEventListener("change", () => onChange(input.checked));
    label.append(input, document.createTextNode(labelText));
    return label;
  }

  function renderLibraryRow(tab) {
    const row = document.createElement("div");
    row.className = "library-item";
    row.dataset.tabId = tab.id;
    if (activeTab && activeTab.id === tab.id) row.classList.add("is-active");
    if (tab.archived) row.classList.add("is-archived");

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

    // A lock icon after the song marks a read-only tab (v1.71); the icon sits
    // outside the ellipsised title so it never disappears with a long name.
    let lockIcon = null;
    if (tab.locked) {
      lockIcon = document.createElement("span");
      lockIcon.className = "library-lock";
      lockIcon.textContent = "🔒";
      lockIcon.title =
        "Lukittu: nimi, viritys, arkistointi, TAB BPM, SYNC, SIIRTO ja poisto on estetty.";
      lockIcon.setAttribute("role", "img");
      lockIcon.setAttribute("aria-label", "Lukittu");
    }

    // v2.03: NIMEÄ became Tiedot – the dialog edits the artist as well, which
    // is what a YouTube upload usually gets wrong.
    const details = libraryButton(
      "Tiedot",
      "ghost small library-details",
      `Tiedot: ${libraryItemLabel(tab)}.`
    );
    details.addEventListener("click", () => openDetailDialog(tab));

    const remove = libraryButton(
      "×",
      "ghost small library-delete library-delete-x",
      tab.locked
        ? "Lukittu: avaa lukitus ennen poistoa."
        : `Poista ${libraryItemLabel(tab)} kirjastosta.`
    );
    remove.setAttribute("aria-label", remove.title);
    remove.disabled = Boolean(tab.locked);
    remove.addEventListener("click", () => requestDelete(tab));

    row.append(open);
    if (lockIcon) row.append(lockIcon);
    row.append(details, remove);
    if (tab.archived) {
      row.append(
        libraryFlag(
          "Arkistoi",
          true,
          (checked) => saveLibraryMeta(tab, { archived: checked }),
          { disabled: Boolean(tab.locked) }
        )
      );
    }
    return row;
  }

  // === TIEDOT-MODAALI (v2.03) ==========================================
  // Every editable library field (artist, name, tuning, lock, archive) lives
  // in one dialog. The absolute metadata (BPM, bars, notes, channel, date,
  // source links) is shown read-only, because editing it would lie about the
  // tab file. A locked tab stays read-only, exactly like the server rule.
  function setDetailStatus(text, isError) {
    if (!detailStatus) return;
    detailStatus.textContent = text || "";
    detailStatus.classList.toggle("is-error", Boolean(isError));
  }

  function detailLink(url) {
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = url;
    return link;
  }

  function appendDetailRow(label, value) {
    if (!detailMeta) return;
    const term = document.createElement("dt");
    term.textContent = label;
    const data = document.createElement("dd");
    if (value instanceof Node) data.append(value);
    else data.textContent = value || "–";
    detailMeta.append(term, data);
  }

  function renderDetailMeta(tab) {
    if (!detailMeta) return;
    detailMeta.textContent = "";
    appendDetailRow("BPM", formatBpm(tab.bpm));
    appendDetailRow("Tahtia", String(Number(tab.measure_count) || 0));
    appendDetailRow("Nuotteja", String(Number(tab.note_count) || 0));
    if (tab.channel) appendDetailRow("YouTube-kanava", tab.channel);
    if (tab.artist_override) {
      appendDetailRow("Alkuperäinen esittäjä", tab.original_artist || "–");
    }
    if (tab.title_override) {
      appendDetailRow("Alkuperäinen nimi", tab.original_title || "–");
    }
    if (tab.source_url) {
      appendDetailRow("Audiolähde", detailLink(tab.source_url));
    } else if (tab.source_type) {
      appendDetailRow("Audiolähde", `ei linkkiä (${tab.source_type})`);
    }
    if (tab.tab_source_url) {
      appendDetailRow("Tablähde", detailLink(tab.tab_source_url));
    } else if (tab.tab_source_file) {
      appendDetailRow("Tablähde", tab.tab_source_file);
    }
    if (tab.variant_backup) {
      appendDetailRow("Versioiden varmuuskopio", tab.variant_backup);
    }
    appendDetailRow("Lisätty", formatTimestamp(tab.created_at) || "–");
    appendDetailRow("ID", tab.id);
  }

  function openDetailDialog(tab) {
    if (!detailDialog || !detailForm) return;
    detailTab = tab;
    const locked = Boolean(tab.locked);
    if (detailSubject) detailSubject.textContent = libraryItemLabel(tab);
    if (detailArtist) {
      detailArtist.value = tab.artist_override || tab.artist || "";
      detailArtist.placeholder = tab.original_artist
        ? `Esittäjä: ${tab.original_artist}`
        : "Esittäjä";
      detailArtist.disabled = locked;
      detailArtist.title = locked
        ? LOCKED_HINT
        : "Esittäjä, esim. Reino Nordin. Tyhjä palauttaa tiedostosta luetun esittäjän.";
    }
    if (detailName) {
      detailName.value = tab.title_override || tab.title || "";
      detailName.placeholder = tab.original_title || "Kappaleen nimi";
      detailName.disabled = locked;
      detailName.title = locked
        ? LOCKED_HINT
        : "Kappaleen nimi, esim. Xsuaalisuuteen (Official audio). Tyhjä palauttaa tiedostosta luetun nimen.";
    }
    if (detailTuning) {
      detailTuning.value = tab.tuning_override || "";
      detailTuning.placeholder = tab.tuning_label
        ? `Viritys: ${tab.tuning_label}`
        : "Viritys (esim. Drop D · DADGBE)";
      detailTuning.disabled = locked;
      detailTuning.title = locked
        ? LOCKED_HINT
        : "Kappaleen viritys, esim. Drop D · DADGBE. Tyhjä palauttaa tiedostosta luetun virityksen.";
    }

    if (detailLocked) {
      detailLocked.checked = locked;
      detailLocked.title = locked
        ? "Poista rasti ja tallenna avataksesi lukituksen. Lukittuna esittäjä, nimi, viritys, arkistointi, TAB BPM, SYNC, SIIRTO, audion liityntä ja poisto ovat vain luku -tilassa."
        : "Lukitse: esittäjä, nimi, viritys, arkistointi, TAB BPM, SYNC, SIIRTO, audion liityntä ja poisto ovat vain luku -tilassa.";
    }
    if (detailArchived) {
      detailArchived.checked = Boolean(tab.archived);
      detailArchived.disabled = locked;
    }
    renderDetailMeta(tab);
    setDetailStatus(locked ? LOCKED_HINT : "");
    detailDialog.hidden = false;
    document.body.classList.add("modal-open");
    if (locked) {
      if (detailLocked) detailLocked.focus();
    } else if (detailArtist) {
      detailArtist.focus();
      detailArtist.select();
    }
  }

  function closeDetailDialog() {
    if (!detailDialog) return;
    detailDialog.hidden = true;
    detailTab = null;
    setDetailStatus("");
  }

  async function saveDetail(event) {
    event.preventDefault();
    if (!detailTab) return;
    const tab = detailTab;
    const locked = Boolean(tab.locked);
    // A locked tab can only be unlocked from here (same rule as the server).
    if (locked && detailLocked && detailLocked.checked) {
      setDetailStatus(LOCKED_HINT, true);
      return;
    }
    const artist = detailArtist ? detailArtist.value.trim() : "";
    const original = String(tab.original_artist || "");
    const patch = locked
      ? { locked: false }
      : {
          // An artist that still matches the tab file stays unset, so the
          // stored data does not pretend to be an override.
          artist: artist && artist !== original ? artist : "",
          title: detailName ? detailName.value.trim() : "",
          tuning: detailTuning ? detailTuning.value.trim() : "",
          locked: detailLocked ? detailLocked.checked : false,
          archived: detailArchived ? detailArchived.checked : false,
        };
    if (detailSave) detailSave.disabled = true;
    setDetailStatus("Tallennetaan…");
    const updated = await saveLibraryMeta(tab, patch);
    if (detailSave) detailSave.disabled = false;
    if (!updated) {
      setDetailStatus("Tallennus epäonnistui.", true);
      return;
    }
    closeDetailDialog();
    setLibraryStatus("Tallennettu.");
  }
  // === /TIEDOT =========================================================


  function renderLibrary() {
    if (!libraryEl) return;
    const active = sortLibraryTabs(
      (Array.isArray(libraryTabs) ? libraryTabs : []).filter((tab) => !tab.archived)
    );
    const archived = sortLibraryTabs(
      (Array.isArray(libraryTabs) ? libraryTabs : []).filter((tab) => tab.archived)
    );
    if (showArchive && archived.length === 0) showArchive = false;
    if (libraryCount) {
      libraryCount.textContent = showArchive
        ? `${archived.length} arkistossa`
        : `${active.length} kappaletta`;
    }
    libraryEl.textContent = "";
    const visible = showArchive ? archived : active;
    for (const tab of visible) libraryEl.append(renderLibraryRow(tab));
    if (visible.length === 0) {
      const empty = document.createElement("p");
      empty.className = "muted library-empty";
      empty.textContent = showArchive
        ? "Arkisto on tyhjä."
        : "Kirjasto on tyhjä.";
      libraryEl.append(empty);
    }
    if (archived.length || showArchive) {
      const bar = document.createElement("div");
      bar.className = "library-archive-bar";
      const toggle = libraryButton(
        showArchive ? "TAKAISIN KIRJASTOON" : `ARKISTO (${archived.length})`,
        "library-archive-link",
        showArchive
          ? "Palaa pääkirjastoon."
          : "Näytä arkistoidut kappaleet ja palauta ne tarvittaessa."
      );
      toggle.addEventListener("click", () => {
        showArchive = !showArchive;
        renderLibrary();
      });
      bar.append(toggle);
      libraryEl.append(bar);
    }
    libraryEl.hidden = false;
  }

  async function selectTab(tabId) {
    await loadTab(tabId);
    closeSearch();
    if (viewerSection) {
      viewerSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  async function saveLibraryMeta(tab, patch) {
    const data = new FormData();
    if (Object.prototype.hasOwnProperty.call(patch, "title")) {
      data.append("title", String(patch.title || ""));
    }
    if (Object.prototype.hasOwnProperty.call(patch, "artist")) {
      // v2.03: an empty artist restores the generated one on the server.
      data.append("artist", String(patch.artist || ""));
    }
    if (Object.prototype.hasOwnProperty.call(patch, "locked")) {
      data.append("locked", patch.locked ? "true" : "false");
    }
    if (Object.prototype.hasOwnProperty.call(patch, "archived")) {
      data.append("archived", patch.archived ? "true" : "false");
    }
    if (Object.prototype.hasOwnProperty.call(patch, "tuning")) {
      const value = String(patch.tuning || "").trim();
      if (value) {
        data.append("tuning", value);
      } else {
        data.append("tuning_clear", "true");
      }
    }
    try {
      const response = await fetch(`/api/tabs/${tab.id}/library`, {
        method: "POST",
        body: data,
      });
      if (!response.ok) {
        setLibraryStatus(await readError(response), true);
        return null;
      }
      const updated = await response.json();
      await loadLibrary();
      if (activeTab && activeTab.id === tab.id) {
        activeTab.title = updated.title;
        activeTab.title_override = updated.title_override;
        activeTab.artist = updated.artist;
        activeTab.artist_override = updated.artist_override;
        activeTab.original_artist = updated.original_artist;
        activeTab.channel = updated.channel;
        activeTab.locked = updated.locked;
        activeTab.archived = updated.archived;
        activeTab.tuning = updated.tuning;
        activeTab.meta = activeTab.meta || {};
        activeTab.meta.tuning_override = updated.tuning_override;
        activeTab.meta.tuning_label = updated.tuning_label;
        applyLockState();
        renderTabMeta(activeTab);
      }
      setLibraryStatus("");
      return updated;
    } catch (error) {
      console.error(error);
      setLibraryStatus("Tallennus epäonnistui.", true);
      return null;
    }
  }

  async function loadLibrary() {
    if (!libraryEl) return;
    try {
      const response = await fetch("/api/tabs?limit=200", { cache: "no-store" });
      if (!response.ok) return;
      libraryTabs = await response.json();
      renderLibrary();
    } catch (error) {
      console.error(error);
    }
  }

  function openSearch() {
    if (!searchModal) return;
    // The panel opens at the LIBRARY button's height instead of jumping to
    // the middle of the screen. Since v2.05 the topbar button is the only
    // entry point (the in-card duplicate was removed).
    const anchor = openSearchTopButton;
    if (anchor) {
      const rect = anchor.getBoundingClientRect();
      const top = Math.max(8, Math.round(rect.top));
      searchModal.style.setProperty("--modal-top", `${top}px`);
    }
    searchModal.hidden = false;
    document.body.classList.add("modal-open");
    showArchive = false;
    setLibraryStatus("");
    loadLibrary();
    if (urlInput) urlInput.focus();
  }

  function closeSearch() {
    if (!searchModal) return;
    searchModal.hidden = true;
    closeDetailDialog();
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
    cancelCountIn();
    activeTab = null;
    applyLockState();
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
    if (tabIsLocked(activeTab)) {
      setAttachStatus(LOCKED_HINT);
      return;
    }
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
      if (attachAudioButton) attachAudioButton.disabled = tabIsLocked(activeTab);
    }
  }

  async function applyTempo() {
    if (!activeTab || !activeTab.id) {
      setBpmStatus("Avaa tabi ensin.", true);
      return;
    }
    if (tabIsLocked(activeTab)) {
      setBpmStatus(LOCKED_HINT, true);
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
      if (bpmButton) bpmButton.disabled = tabIsLocked(activeTab);
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
  if (detailForm) detailForm.addEventListener("submit", saveDetail);
  if (detailCancel) detailCancel.addEventListener("click", closeDetailDialog);
  if (detailDialog) {
    detailDialog.addEventListener("click", (event) => {
      if (event.target === detailDialog) closeDetailDialog();
    });
  }
  // Sanat (v2.06): the editor and its overlay are wired here, outside the
  // playback chain; watchLyrics() only observes existing UI text.
  if (lyricsButton) lyricsButton.addEventListener("click", openLyricsDialog);
  if (lyricsForm) lyricsForm.addEventListener("submit", saveLyrics);
  if (lyricsClose) lyricsClose.addEventListener("click", closeLyricsDialog);
  // Lukitus (v2.18): rasti tallentaa nykyiset rivit ja lukitsee sidecarin.
  if (lyricsLockInput) {
    lyricsLockInput.addEventListener("change", toggleLyricsLock);
  }
  if (lyricsFillButton) {
    lyricsFillButton.addEventListener("click", fillLyricsFromSelection);
  }
  // Playback for placing lyrics (v2.12): the same calls the transport and
  // the remote already use. Nothing here changes them.
  if (lyricsPlayButton) {
    lyricsPlayButton.addEventListener("click", () => handlePlayButton());
  }
  if (lyricsStartButton) {
    lyricsStartButton.addEventListener("click", () => seekTo(0));
  }
  if (lyricsBackButton) {
    lyricsBackButton.addEventListener("click", () => seekBy(-5));
  }
  if (lyricsForwardButton) {
    lyricsForwardButton.addEventListener("click", () => seekBy(5));
  }
  if (lyricsHandle) {
    lyricsHandle.addEventListener("pointerdown", startLyricsDrag);
    window.addEventListener("pointermove", moveLyricsDrag);
    window.addEventListener("pointerup", endLyricsDrag);
    window.addEventListener("pointercancel", endLyricsDrag);
  }
  for (const grip of lyricsResizeGrips) {
    grip.addEventListener("pointerdown", startLyricsResize);
  }
  if (lyricsResizeGrips.length) {
    window.addEventListener("pointermove", moveLyricsResize);
    window.addEventListener("pointerup", endLyricsResize);
    window.addEventListener("pointercancel", endLyricsResize);
  }
  if (lyricsSplitter) {
    // Splitter: bar list ↔ lyric field (v2.13). DOM only.
    lyricsSplitter.addEventListener("pointerdown", startLyricsSplit);
    window.addEventListener("pointermove", moveLyricsSplit);
    window.addEventListener("pointerup", endLyricsSplit);
    window.addEventListener("pointercancel", endLyricsSplit);
    lyricsSplitter.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
      event.preventDefault();
      const current = lyricsBars
        ? lyricsBars.getBoundingClientRect().height
        : LYRICS_BARS_DEFAULT;
      setLyricsBarsHeight(current + (event.key === "ArrowDown" ? 24 : -24));
      saveLyricsPanelPosition();
    });
  }
  window.addEventListener("resize", () => {
    // Keep the floating editor inside the viewport after a resize/fullscreen.
    if (lyricsDialog && !lyricsDialog.hidden) {
      if (lyricsDialog.style.width || lyricsDialog.style.height) {
        sizeLyricsPanel(lyricsDialog.offsetWidth, lyricsDialog.offsetHeight);
      }
      placeLyricsPanel(lyricsDialog.offsetLeft, lyricsDialog.offsetTop);
      if (lyricsBars) {
        setLyricsBarsHeight(lyricsBars.getBoundingClientRect().height);
      }
    }
  });
  if (lyricsInput) {
    lyricsInput.addEventListener("input", () => {
      lyricsDirty = true;
      lyricsLineSelection = null;
      markLyricsBars();
    });
    // v2.17: Ctrl+Enter writes the selection into the anchor bar.
    lyricsInput.addEventListener("keydown", handleLyricsAssignKey);
  }
  if (lyricsNotesInput) {
    // v2.20: a note edit counts as unsaved work, so a late load cannot
    // overwrite it before TALLENNA.
    lyricsNotesInput.addEventListener("input", () => {
      lyricsDirty = true;
    });
  }
  watchLyrics();
  if (playButton) playButton.addEventListener("click", handlePlayButton);
  if (countInToggle) {
    countInToggle.addEventListener("change", () =>
      setCountInEnabled(countInToggle.checked)
    );
  }
  setCountInEnabled(readCountInEnabled(), { persist: false });
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
      countInSkipped = true;
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
  if (seekBack) {
    seekBack.addEventListener("click", () => {
      countInSkipped = true;
      seekBy(-5);
    });
  }
  if (seekForward) {
    seekForward.addEventListener("click", () => {
      countInSkipped = true;
      seekBy(5);
    });
  }
  if (sectionButton) {
    sectionButton.addEventListener("click", generateSection);
  }
  if (attachAudioButton) {
    attachAudioButton.addEventListener("click", attachAudio);
  }
  if (variantButton) {
    variantButton.addEventListener("click", openVariantDialog);
  }
  if (variantRestoreButton) {
    variantRestoreButton.addEventListener("click", restoreVariants);
  }
  if (variantConfirm) variantConfirm.addEventListener("click", finalizeVariant);
  if (variantCancel) variantCancel.addEventListener("click", closeVariantDialog);
  if (variantDialog) {
    variantDialog.addEventListener("click", (event) => {
      if (event.target === variantDialog) closeVariantDialog();
    });
  }
  if (rateSlider) {
    rateSlider.addEventListener("input", () => {
      // v1.96: 1 % steps; 95–105 % snaps to exactly 100 % so the neutral
      // practice speed is easy to hit with a mouse (no 0.1 % precision).
      // Compare whole percents to avoid float edge cases at 0.95 / 1.05.
      const value = Number(rateSlider.value);
      const percent = Math.round(value * 100);
      const snapped = Math.abs(percent - 100) <= 5 ? 1 : value;
      if (snapped !== value) rateSlider.value = String(snapped);
      setPlaybackRate(snapped);
    });
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
  if (alignButton) {
    alignButton.addEventListener("click", () => {
      if (alignArmed) disarmAlign();
      else armAlign();
    });
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
    if (event.key === "Escape" && variantDialog && !variantDialog.hidden) {
      closeVariantDialog();
      return;
    }
    if (event.key === "Escape" && searchModal && !searchModal.hidden) {
      if (deleteDialog && !deleteDialog.hidden) {
        cancelDelete();
      } else if (detailDialog && !detailDialog.hidden) {
        closeDetailDialog();
      } else {
        closeSearch();
      }
      return;
    }
    if (event.key === "Escape" && lyricsDialog && !lyricsDialog.hidden) {
      closeLyricsDialog();
      return;
    }
    if (event.key === "Escape" && countInActive) {
      // Esc during the countdown cancels it; the next PLAY starts it again.
      cancelCountIn();
      return;
    }
    const tag = event.target && event.target.tagName;
    const interactive = ["INPUT", "SELECT", "TEXTAREA", "BUTTON"].includes(
      tag
    );
    if (!interactive && viewerSection && !viewerSection.hidden) {
      if (event.key === " ") {
        event.preventDefault();
        handlePlayButton();
        return;
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        countInSkipped = true;
        seekBy(-5);
        return;
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        countInSkipped = true;
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
    audio.addEventListener("play", () => {
      setPlayLabel(true);
      if (alignArmed) disarmAlign();
    });
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
    await loadRuntimeSettings();
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



