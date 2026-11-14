/* PianoCapture - 88-key falling-note view for a transcribed piano fragment.
 * No dependencies. The audio is the reference clock: every note is drawn at
 * (note.start - audio.currentTime), so speed changes and seeking come for free.
 */
(() => {
  "use strict";

  const FIRST_MIDI = 21; // A0
  const LAST_MIDI = 108; // C8
  const BLACK_PITCHES = new Set([1, 3, 6, 8, 10]);
  const VISIBLE_SECONDS = 2.8;
  const KEYBOARD_RATIO = 0.24;
  const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

  const $ = (id) => document.getElementById(id);

  const sourceInput = $("source-url");
  const analyzeButton = $("analyze");
  const startInput = $("window-start");
  const endInput = $("window-end");
  const useSuggestionButton = $("use-suggestion");
  const processButton = $("process");
  const statusEl = $("status");
  const suggestionEl = $("suggestion");
  const progressWrap = $("progress-wrap");
  const progressBar = $("progress-bar");
  const recentCard = $("recent-card");
  const recentEl = $("recent");

  const player = $("player");
  const canvas = $("keys");
  const emptyEl = $("empty");
  const titleEl = $("piece-title");
  const metaEl = $("piece-meta");
  const playButton = $("play");
  const timeCurrent = $("time-current");
  const timeTotal = $("time-total");
  const seekInput = $("seek");
  const speedInput = $("speed");
  const speedReadout = $("speed-readout");
  const loopInput = $("loop");
  const synthInput = $("synth");
  const cycleInput = $("cycle");
  const cycleInfo = $("cycle-info");
  const cycleLengthInput = $("cycle-length");
  const cycleHalfButton = $("cycle-half");
  const cycleDoubleButton = $("cycle-double");
  const backingInput = $("backing");
  const backingHint = $("backing-hint");
  const downloadAudio = $("download-audio");
  const downloadMidi = $("download-midi");
  const downloadGuide = $("download-guide");
  const playOrgButton = $("play-org");
  const playMidButton = $("play-mid");
  const lanRow = $("lan-row");
  const lanUrl = $("lan-url");
  const lanQr = $("lan-qr");
  const phoneQr = $("phone-qr");
  const pieceQr = $("piece-qr");
  const showLeftInput = $("show-left");
  const showRightInput = $("show-right");
  const splitInput = $("split");
  const splitName = $("split-name");
  const audio = $("audio");

  const ctx2d = canvas.getContext("2d");

  const state = {
    piece: null,
    notes: [],
    duration: 0,
    cycle: null,
    cycleOn: false,
    cycleLength: 0,
    keyRange: { lo: FIRST_MIDI, hi: LAST_MIDI },
    suggestion: null,
    source: null,
    playing: false,
    speed: 1,
    split: 60,
    showLeft: true,
    showRight: true,
    loop: true,
    synth: false,
    backing: true,
    lastSynth: -1,
    voices: 0,
    voicesReset: 0,
    busy: false,
    cssWidth: 0,
    cssHeight: 0,
  };

  // --- layout -----------------------------------------------------------
  const keys = (() => {
    const whites = [];
    for (let midi = FIRST_MIDI; midi <= LAST_MIDI; midi += 1) {
      if (!BLACK_PITCHES.has(midi % 12)) whites.push(midi);
    }
    const whiteIndex = new Map(whites.map((midi, index) => [midi, index]));
    const blackWidth = 0.62;
    return Array.from({ length: LAST_MIDI - FIRST_MIDI + 1 }, (_, offset) => {
      const midi = FIRST_MIDI + offset;
      const black = BLACK_PITCHES.has(midi % 12);
      if (black) {
        const before = whiteIndex.get(midi - 1) ?? 0;
        return { midi, black, x: before + 1 - blackWidth / 2, w: blackWidth };
      }
      return { midi, black, x: whiteIndex.get(midi) ?? 0, w: 1 };
    });
  })();

  // --- small helpers ----------------------------------------------------
  function noteName(midi) {
    const name = NOTE_NAMES[((midi % 12) + 12) % 12];
    const octave = Math.floor(midi / 12) - 1;
    return `${name}${octave}`;
  }

  function formatTime(seconds) {
    const value = Math.max(0, Number(seconds) || 0);
    const minutes = Math.floor(value / 60);
    const rest = value - minutes * 60;
    return `${minutes}:${rest.toFixed(1).padStart(4, "0")}`;
  }

  function clamp(value, low, high) {
    return Math.min(Math.max(value, low), high);
  }

  function hand(note) {
    return note.pitch < state.split ? "left" : "right";
  }

  function isVisible(note) {
    const side = hand(note);
    return side === "left" ? state.showLeft : state.showRight;
  }

  function currentTime() {
    const value = Number(audio.currentTime);
    return Number.isFinite(value) ? value : 0;
  }

  function setStatus(text, kind) {
    statusEl.textContent = text || "";
    statusEl.classList.toggle("is-error", kind === "error");
    statusEl.classList.toggle("is-ok", kind === "ok");
  }

  function setProgress(value, stage) {
    const visible = Number(value) > 0.001 || Boolean(stage);
    progressWrap.hidden = !visible;
    progressBar.style.width = `${Math.round(clamp(Number(value) || 0, 0, 1) * 100)}%`;
    if (stage) setStatus(stage);
  }

  function setBusy(busy) {
    state.busy = busy;
    analyzeButton.disabled = busy;
    processButton.disabled = busy;
    useSuggestionButton.disabled = busy;
  }

  async function readError(response) {
    try {
      const payload = await response.json();
      if (payload && typeof payload.detail === "string") return payload.detail;
      return `HTTP ${response.status}`;
    } catch (error) {
      return `HTTP ${response.status}`;
    }
  }

  async function waitJob(jobId) {
    for (;;) {
      const response = await fetch(`/api/piano/jobs/${jobId}`, { cache: "no-store" });
      if (!response.ok) throw new Error(await readError(response));
      const job = await response.json();
      setProgress(job.progress, job.stage);
      if (job.status === "ready") return job.result;
      if (job.status === "failed") throw new Error(job.error || "Tuntematon virhe.");
      await new Promise((resolve) => window.setTimeout(resolve, 500));
    }
  }

  async function startJob(path, body) {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error(await readError(response));
    const job = await response.json();
    return waitJob(job.id);
  }

  // --- analysis + processing -------------------------------------------
  async function analyze() {
    const url = sourceInput.value.trim();
    if (!url) {
      setStatus("Anna YouTube-linkki.", "error");
      return;
    }
    setBusy(true);
    setProgress(0.02, "Ladataan…");
    try {
      const result = await startJob("/api/piano/analyze", { url });
      state.source = result.source;
      state.suggestion = result.suggestion;
      const start = Math.max(0, Number(result.suggestion.start) || 0);
      const end = Math.max(start + 3, Number(result.suggestion.end) || start + 30);
      startInput.value = start.toFixed(1);
      endInput.value = end.toFixed(1);
      suggestionEl.hidden = false;
      suggestionEl.textContent = `${result.suggestion.reason} Varmuus ${Math.round(
        (Number(result.suggestion.confidence) || 0) * 100
      )} %.`;
      useSuggestionButton.hidden = false;
      const title = result.source.title || "YouTube";
      const artist = result.source.artist ? `${result.source.artist} — ` : "";
      setStatus(`Ehdotus valmis: ${artist}${title}. Tarkista rajat ja käsittele pätkä.`, "ok");
      setProgress(1);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error), "error");
      setProgress(0);
    } finally {
      setBusy(false);
    }
  }

  function useSuggestion() {
    if (!state.suggestion) return;
    const start = Math.max(0, Number(state.suggestion.start) || 0);
    const end = Math.max(start + 3, Number(state.suggestion.end) || start + 30);
    startInput.value = start.toFixed(1);
    endInput.value = end.toFixed(1);
  }

  async function processWindow() {
    const url = sourceInput.value.trim();
    if (!url) {
      setStatus("Anna YouTube-linkki.", "error");
      return;
    }
    const start = Math.max(0, Number(String(startInput.value).replace(",", ".")) || 0);
    const end = Number(String(endInput.value).replace(",", ".")) || 0;
    if (!(end > start)) {
      setStatus("Lopun pitää olla alun jälkeen.", "error");
      return;
    }
    if (end - start < 3) {
      setStatus("Pätkä on liian lyhyt (vähintään 3 s).", "error");
      return;
    }
    setBusy(true);
    setProgress(0.02, "Ladataan…");
    try {
      const result = await startJob("/api/piano/process", { url, start, end });
      setProgress(1);
      await loadPiece(result.piece_id);
      player.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error), "error");
      setProgress(0);
    } finally {
      setBusy(false);
    }
  }

  // --- piece + player ---------------------------------------------------
  async function loadPiece(pieceId) {
    setStatus("Ladataan pätkää…");
    const response = await fetch(`/api/piano/pieces/${pieceId}`, { cache: "no-store" });
    if (!response.ok) throw new Error(await readError(response));
    const piece = await response.json();

    pause();
    state.piece = piece;
    state.notes = Array.isArray(piece.notes) ? piece.notes : [];
    state.duration = Number(piece.window && piece.window.duration) || 0;
    state.lastSynth = -1;
    state.cycle = piece.cycle || null;
    state.cycleOn = Boolean(
      state.cycle && Number(state.cycle.confidence) >= 0.55
    );
    state.cycleLength = state.cycle
      ? clamp(Number(state.cycle.length) || 8, 1.5, Math.max(1.5, state.duration))
      : Math.min(8, Math.max(1.5, state.duration));
    if (cycleInput) cycleInput.checked = state.cycleOn;
    if (cycleLengthInput) cycleLengthInput.value = state.cycleLength.toFixed(1);

    const source = piece.source || {};
    const artist = source.artist ? `${source.artist} — ` : "";
    titleEl.textContent = `${artist}${source.title || "Piano"}`;
    const start = Number(piece.window && piece.window.start) || 0;
    const end = Number(piece.window && piece.window.end) || 0;
    const cycleText = state.cycle
      ? ` · kierto ${Number(state.cycle.length).toFixed(1)} s × ${Number(
          state.cycle.repeats
        ).toFixed(1)}`
      : "";
    metaEl.textContent = `${formatTime(start)}–${formatTime(end)} · ${
      state.notes.length
    } nuottia${cycleText} · transkriboitu automaattisesti`;

    audio.src = `/api/piano/pieces/${pieceId}/audio?v=${Date.now()}`;
    audio.load();
    audio.muted = !state.backing;
    audio.playbackRate = state.speed;
    if (downloadAudio) {
      downloadAudio.href = `/api/piano/pieces/${pieceId}/audio.mp3`;
      downloadAudio.setAttribute("download", `pianocapture-${pieceId}.mp3`);
    }
    if (downloadMidi) {
      downloadMidi.href = `/api/piano/pieces/${pieceId}/midi`;
      downloadMidi.setAttribute("download", `pianocapture-${pieceId}.mid`);
    }
    if (downloadGuide) {
      downloadGuide.href = `/api/piano/pieces/${pieceId}/guide.mp3`;
      downloadGuide.setAttribute(
        "download",
        `pianocapture-${pieceId}-guide.mp3`
      );
    }
    if (phoneQr && pieceQr) {
      pieceQr.onerror = () => {
        phoneQr.hidden = true;
      };
      pieceQr.src = `/api/piano/pieces/${pieceId}/qr.svg?t=${Date.now()}`;
      phoneQr.hidden = false;
    }
    fitKeyRange();
    seekInput.max = String(Math.max(0.1, loopEnd()));
    seekInput.value = "0";
    timeTotal.textContent = formatTime(loopEnd());
    timeCurrent.textContent = formatTime(0);
    updateCycleInfo();
    emptyEl.hidden = state.notes.length > 0;
    player.hidden = false;
    resizeCanvas();
    setStatus(
      state.notes.length
        ? `Valmis: ${state.notes.length} nuottia. Space = PLAY/PAUSE.`
        : "Pätkä valmis, mutta pianoa ei tunnistettu tästä kohdasta.",
      state.notes.length ? "ok" : "error"
    );
    await refreshRecent();
  }

  function play() {
    if (!state.piece) return;
    ensureAudioContext();
    state.lastSynth = currentTime() - 0.02;
    const promise = audio.play();
    if (promise && typeof promise.catch === "function") {
      promise.catch((error) => {
        setStatus(
          `Äänen toisto ei alkanut: ${error instanceof Error ? error.message : error}`,
          "error"
        );
      });
    }
  }

  function pause() {
    audio.pause();
    state.lastSynth = -1;
    setPlayLabel(false);
  }

  function togglePlay() {
    if (!state.piece) return;
    if (audio.paused) play();
    else pause();
  }

  function setPlayLabel(playing) {
    state.playing = playing;
    playButton.textContent = playing ? "PAUSE" : "PLAY";
    playButton.dataset.state = playing ? "playing" : "paused";
  }

  function seekTo(seconds) {
    if (!state.piece) return;
    const value = clamp(Number(seconds) || 0, 0, state.duration || 0);
    audio.currentTime = value;
    timeCurrent.textContent = formatTime(value);
    seekInput.value = String(value);
    state.lastSynth = value - 0.02;
  }

  // --- backing (v0.3) ---------------------------------------------------
  // "Taustaääni" on: the clip plays under the falling notes. Off: the clip is
  // muted but still runs the clock, so the notes keep moving and the user can
  // play their own piano along. The choice is remembered in this browser.
  function readBacking() {
    try {
      const stored = localStorage.getItem("pianocap:backing");
      return stored === null ? true : stored === "1";
    } catch (error) {
      return true;
    }
  }

  function applyBacking() {
    state.backing = Boolean(backingInput && backingInput.checked);
    audio.muted = !state.backing;
    updateBackingHint();
    syncPlayMode();
    try {
      localStorage.setItem("pianocap:backing", state.backing ? "1" : "0");
    } catch (error) {
      /* storage disabled */
    }
  }

  function updateBackingHint() {
    if (!backingHint) return;
    if (state.backing) {
      backingHint.textContent = "";
    } else if (state.synth) {
      backingHint.textContent = "Tausta pois – kuulet vain ohjeen.";
    } else {
      backingHint.textContent = "Tausta pois – soita itse mukana.";
    }
  }

  // --- play source: ORG / MID (v0.5.1) ---------------------------------
  // The choice sits next to PLAY: ORG plays the recording, MID plays the
  // transcription (backing muted, piano synth on). Switching while playing
  // swaps the source at the same position, so A/B is instant.
  function syncPlayMode() {
    const org = state.backing && !state.synth;
    const mid = !state.backing && state.synth;
    if (playOrgButton) {
      playOrgButton.setAttribute("aria-pressed", org ? "true" : "false");
    }
    if (playMidButton) {
      playMidButton.setAttribute("aria-pressed", mid ? "true" : "false");
    }
  }

  function setPlayMode(mode) {
    const mid = mode === "mid";
    if (backingInput) {
      backingInput.checked = !mid;
      applyBacking();
    }
    if (synthInput) {
      synthInput.checked = mid;
      state.synth = mid;
      if (mid) ensureAudioContext();
    }
    updateBackingHint();
    syncPlayMode();
  }

  // --- cycle (v0.2) -----------------------------------------------------
  // A short piano figure usually repeats. KIERTO shows and loops just one
  // cycle, so the whole intro can be learned from a few seconds of notes.
  function loopEnd() {
    if (!state.cycleOn || !state.duration) return state.duration;
    return Math.min(state.cycleLength || state.duration, state.duration);
  }

  function updateCycleInfo() {
    if (!cycleInfo) return;
    if (!state.duration || !state.cycleOn) {
      cycleInfo.textContent = "";
      return;
    }
    const repeats = state.duration / Math.max(0.1, loopEnd());
    cycleInfo.textContent = `${loopEnd().toFixed(1)} s × ${repeats.toFixed(1)}`;
  }

  function applyCycle(restart) {
    if (!state.duration) return;
    state.cycleOn = Boolean(cycleInput && cycleInput.checked);
    const fallback = state.cycle
      ? Number(state.cycle.length)
      : Math.min(8, state.duration);
    const typed = Number(String(cycleLengthInput.value).replace(",", "."));
    state.cycleLength = clamp(
      Number.isFinite(typed) && typed > 0 ? typed : fallback,
      1.5,
      Math.max(1.5, state.duration)
    );
    if (cycleLengthInput) cycleLengthInput.value = state.cycleLength.toFixed(1);
    const end = loopEnd();
    seekInput.max = String(Math.max(0.1, end));
    timeTotal.textContent = formatTime(end);
    updateCycleInfo();
    fitKeyRange();
    if (state.piece && (restart || currentTime() >= end)) seekTo(0);
    draw();
  }

  function scaleCycle(factor) {
    if (!state.duration) return;
    const base = state.cycleLength || state.duration;
    const next = clamp(base * factor, 1.5, Math.max(1.5, state.duration));
    if (cycleInput) cycleInput.checked = true;
    if (cycleLengthInput) cycleLengthInput.value = next.toFixed(1);
    applyCycle(true);
  }

  // --- phone/tablet keyboard fit (v0.4) --------------------------------
  // On a narrow screen the full 88 keys would be ~4 px each. Show only the
  // pitch range this fragment (or the current cycle) uses, snapped outward to
  // white keys. A wide screen keeps all 88 for orientation.
  function fitKeyRange() {
    if (window.innerWidth >= 1100 || !state.notes.length) {
      state.keyRange = { lo: FIRST_MIDI, hi: LAST_MIDI };
      return;
    }
    const end = state.cycleOn ? loopEnd() : state.duration || Infinity;
    let lo = LAST_MIDI;
    let hi = FIRST_MIDI;
    for (const note of state.notes) {
      if (note.start >= end) continue;
      lo = Math.min(lo, note.pitch);
      hi = Math.max(hi, note.pitch);
    }
    if (hi < lo) {
      state.keyRange = { lo: FIRST_MIDI, hi: LAST_MIDI };
      return;
    }
    lo = Math.max(FIRST_MIDI, lo - 2);
    hi = Math.min(LAST_MIDI, hi + 2);
    while (lo > FIRST_MIDI && BLACK_PITCHES.has(lo % 12)) lo -= 1;
    while (hi < LAST_MIDI && BLACK_PITCHES.has(hi % 12)) hi += 1;
    // Keep at least two octaves: less looks like a toy keyboard.
    while (hi - lo < 24) {
      if (lo > FIRST_MIDI) lo -= 1;
      else if (hi < LAST_MIDI) hi += 1;
      else break;
    }
    state.keyRange = { lo, hi };
  }

  // --- synth ------------------------------------------------------------
  let audioCtx = null;
  let guideGain = null;

  function ensureAudioContext() {
    if (audioCtx) {
      if (audioCtx.state === "suspended") {
        audioCtx.resume().catch(() => {});
      }
      return audioCtx;
    }
    const Ctor = window.AudioContext || window.webkitAudioContext;
    if (!Ctor) return null;
    try {
      audioCtx = new Ctor();
      guideGain = audioCtx.createGain();
      guideGain.gain.value = 0.9;
      const limiter = audioCtx.createDynamicsCompressor();
      limiter.threshold.value = -18;
      limiter.knee.value = 12;
      limiter.ratio.value = 8;
      guideGain.connect(limiter).connect(audioCtx.destination);
      audioCtx.resume().catch(() => {});
    } catch (error) {
      audioCtx = null;
      guideGain = null;
    }
    return audioCtx;
  }

  function synthNote(note) {
    if (!audioCtx || !guideGain || audioCtx.state !== "running") return;
    const now = audioCtx.currentTime;
    if (state.voices > 36) return;
    const frequency = 440 * 2 ** ((note.pitch - 69) / 12);
    const duration = clamp(note.end - note.start, 0.12, 4);
    const velocity = clamp((note.velocity || 90) / 127, 0.2, 1);
    const attackEnd = now + Math.min(0.01, duration * 0.2);
    const decayEnd = Math.min(now + 0.28, now + duration * 0.6);
    const releaseEnd = now + duration;

    const envelope = audioCtx.createGain();
    const gain = envelope.gain;
    gain.setValueAtTime(0.0001, now);
    gain.exponentialRampToValueAtTime(0.1 * velocity, attackEnd);
    gain.exponentialRampToValueAtTime(0.032 * velocity, decayEnd);
    gain.exponentialRampToValueAtTime(0.02 * velocity, releaseEnd);
    gain.exponentialRampToValueAtTime(0.0001, releaseEnd + 0.04);
    envelope.connect(guideGain);

    // Harmonic stack: a sine plus quieter octave/twelfth/fifteenth partials.
    let last = null;
    for (const [ratio, level] of [[1, 1], [2, 0.4], [3, 0.16], [4, 0.07]]) {
      const oscillator = audioCtx.createOscillator();
      const partial = audioCtx.createGain();
      oscillator.type = "sine";
      oscillator.frequency.value = frequency * ratio;
      partial.gain.value = level;
      oscillator.connect(partial).connect(envelope);
      oscillator.start(now);
      oscillator.stop(now + duration + 0.05);
      last = oscillator;
    }
    state.voices += 1;
    if (last) {
      last.onended = () => {
        state.voices = Math.max(0, state.voices - 1);
      };
    }
  }

  function pumpSynth(now) {
    if (!state.synth || audio.paused) return;
    if (state.voicesReset > now) return;
    state.voicesReset = now + 1;
    state.voices = Math.max(0, state.voices);
    const from = state.lastSynth;
    const to = now + 0.04;
    const end = loopEnd();
    if (from < 0) {
      state.lastSynth = to;
      return;
    }
    for (const note of state.notes) {
      if (!isVisible(note)) continue;
      if (note.start >= end) continue;
      if (note.start > from && note.start <= to) synthNote(note);
    }
    state.lastSynth = to;
  }

  // --- canvas -----------------------------------------------------------
  function resizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    state.cssWidth = Math.max(1, rect.width);
    state.cssHeight = Math.max(1, rect.height);
    canvas.width = Math.round(state.cssWidth * dpr);
    canvas.height = Math.round(state.cssHeight * dpr);
    ctx2d.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function roundRect(x, y, width, height, radius) {
    const r = Math.min(radius, width / 2, height / 2);
    ctx2d.beginPath();
    ctx2d.moveTo(x + r, y);
    ctx2d.arcTo(x + width, y, x + width, y + height, r);
    ctx2d.arcTo(x + width, y + height, x, y + height, r);
    ctx2d.arcTo(x, y + height, x, y, r);
    ctx2d.arcTo(x, y, x + width, y, r);
    ctx2d.closePath();
  }

  function draw() {
    const width = state.cssWidth;
    const height = state.cssHeight;
    if (!width || !height) return;
    const keyboardHeight = clamp(height * KEYBOARD_RATIO, 64, 132);
    const top = height - keyboardHeight;
    // A phone/tablet shows only the pitch range this fragment actually uses,
    // so the keys stay wide enough to read. A wide screen keeps all 88.
    const range = state.keyRange || { lo: FIRST_MIDI, hi: LAST_MIDI };
    const visibleKeys = keys.filter(
      (key) => key.midi >= range.lo && key.midi <= range.hi
    );
    const whiteKeys = visibleKeys.filter((key) => !key.black);
    const whiteWidth = width / Math.max(1, whiteKeys.length);
    const whiteOffset = whiteKeys.length ? whiteKeys[0].x : 0;
    const keyByMidi = new Map(visibleKeys.map((key) => [key.midi, key]));
    const keyX = (key) => (key.x - whiteOffset) * whiteWidth;
    const pixelsPerSecond = top / VISIBLE_SECONDS;
    const t = state.piece ? currentTime() : 0;
    // In KIERTO only the first cycle is drawn, so the sheet is short.
    const endT = state.cycleOn ? loopEnd() : Infinity;

    ctx2d.clearRect(0, 0, width, height);

    // subtle lane guides every octave
    ctx2d.save();
    ctx2d.strokeStyle = "rgba(255,255,255,0.05)";
    ctx2d.lineWidth = 1;
    for (let midi = Math.ceil(range.lo / 12) * 12; midi <= range.hi; midi += 12) {
      const key = keyByMidi.get(midi);
      if (!key) continue;
      const x = Math.round(keyX(key)) + 0.5;
      ctx2d.beginPath();
      ctx2d.moveTo(x, 0);
      ctx2d.lineTo(x, top);
      ctx2d.stroke();
    }
    ctx2d.restore();

    // notes
    const activeKeys = new Set();
    for (const note of state.notes) {
      if (!isVisible(note)) continue;
      if (note.start >= endT) continue;
      const key = keyByMidi.get(note.pitch);
      if (!key) continue;
      const noteEnd = Math.min(note.end, endT);
      const active = note.start <= t && t < noteEnd;
      if (active) activeKeys.add(note.pitch);
      const keyWidth = key.w * whiteWidth;
      const blockWidth = Math.max(3, keyWidth * (key.black ? 0.92 : 0.84));
      const blockX = keyX(key) + (keyWidth - blockWidth) / 2;
      const yBottom = top - (note.start - t) * pixelsPerSecond;
      const yTop = top - (noteEnd - t) * pixelsPerSecond;
      const visibleTop = Math.max(0, Math.min(yTop, yBottom));
      const visibleBottom = Math.min(top, Math.max(yTop, yBottom));
      if (visibleBottom <= visibleTop) continue;
      const color = hand(note) === "left" ? "#6aa9ff" : "#f0b35a";
      ctx2d.save();
      ctx2d.globalAlpha = active ? 1 : 0.82;
      ctx2d.fillStyle = color;
      roundRect(
        blockX,
        visibleTop,
        blockWidth,
        Math.max(3, visibleBottom - visibleTop),
        4
      );
      ctx2d.fill();
      if (active) {
        ctx2d.globalAlpha = 0.35;
        ctx2d.fillStyle = "#ffffff";
        ctx2d.fill();
      }
      ctx2d.restore();
    }

    // keyboard
    for (const key of whiteKeys) {
      const keyWidth = key.w * whiteWidth;
      const x = keyX(key);
      const active = activeKeys.has(key.midi);
      const color = active
        ? hand({ pitch: key.midi }) === "left"
          ? "#6aa9ff"
          : "#f0b35a"
        : "#eef1f6";
      ctx2d.fillStyle = color;
      ctx2d.fillRect(x, top, keyWidth - 1, keyboardHeight);
      ctx2d.strokeStyle = "rgba(10,12,16,0.9)";
      ctx2d.lineWidth = 1;
      ctx2d.strokeRect(x + 0.5, top + 0.5, keyWidth - 1, keyboardHeight - 1);
      if (whiteWidth > 13 && key.midi % 12 === 0) {
        ctx2d.fillStyle = active ? "#14100a" : "#8b94a2";
        ctx2d.font = `600 ${Math.min(10, whiteWidth * 0.42)}px system-ui, sans-serif`;
        ctx2d.textAlign = "center";
        ctx2d.fillText(noteName(key.midi), x + keyWidth / 2, top + keyboardHeight - 6);
      }
    }
    for (const key of visibleKeys) {
      if (!key.black) continue;
      const keyWidth = key.w * whiteWidth;
      const x = keyX(key);
      const blackHeight = keyboardHeight * 0.62;
      const active = activeKeys.has(key.midi);
      const color = active
        ? hand({ pitch: key.midi }) === "left"
          ? "#6aa9ff"
          : "#f0b35a"
        : "#12161d";
      ctx2d.fillStyle = color;
      roundRect(x, top, keyWidth, blackHeight, 3);
      ctx2d.fill();
      ctx2d.strokeStyle = "rgba(0,0,0,0.85)";
      ctx2d.lineWidth = 1;
      ctx2d.stroke();
    }

    // active note names just above the keyboard
    if (activeKeys.size) {
      ctx2d.save();
      ctx2d.textAlign = "center";
      ctx2d.font = "700 11px system-ui, sans-serif";
      for (const pitch of activeKeys) {
        const key = keyByMidi.get(pitch);
        if (!key) continue;
        const keyWidth = key.w * whiteWidth;
        const x = keyX(key) + keyWidth / 2;
        ctx2d.fillStyle = "rgba(10,12,16,0.55)";
        const label = noteName(pitch);
        const textWidth = ctx2d.measureText(label).width + 8;
        roundRect(x - textWidth / 2, top - 20, textWidth, 16, 5);
        ctx2d.fill();
        ctx2d.fillStyle = "#f2f4f8";
        ctx2d.fillText(label, x, top - 8);
      }
      ctx2d.restore();
    }

    // playhead
    ctx2d.save();
    ctx2d.strokeStyle = "rgba(240,179,90,0.9)";
    ctx2d.lineWidth = 2;
    ctx2d.beginPath();
    ctx2d.moveTo(0, top + 0.5);
    ctx2d.lineTo(width, top + 0.5);
    ctx2d.stroke();
    ctx2d.restore();
  }

  // --- loop -------------------------------------------------------------
  function frame() {
    if (!player.hidden && state.piece) {
      const now = currentTime();
      const end = loopEnd();
      if (
        state.playing &&
        (state.loop || state.cycleOn) &&
        end > 0 &&
        now >= end - 0.03
      ) {
        seekTo(0);
        if (audio.paused) play();
      }
      pumpSynth(now);
      timeCurrent.textContent = formatTime(now);
      if (!seekDragging) {
        seekInput.value = String(clamp(now, 0, end || 0));
      }
      draw();
    }
    window.requestAnimationFrame(frame);
  }

  // --- recent pieces ----------------------------------------------------
  async function refreshRecent() {
    try {
      const response = await fetch("/api/piano/pieces?limit=8", { cache: "no-store" });
      if (!response.ok) return;
      const items = await response.json();
      recentEl.textContent = "";
      if (!Array.isArray(items) || !items.length) {
        recentCard.hidden = true;
        return;
      }
      for (const item of items) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "ghost";
        const label = `${item.artist ? item.artist + " — " : ""}${item.title || "Piano"}`;
        button.textContent = label;
        const meta = document.createElement("span");
        meta.className = "recent-meta";
        const start = Number(item.window && item.window.start) || 0;
        const end = Number(item.window && item.window.end) || 0;
        meta.textContent = `${formatTime(start)}–${formatTime(end)} · ${
          item.note_count || 0
        } nuottia`;
        button.appendChild(meta);
        button.addEventListener("click", () => {
          loadPiece(item.id)
            .then(() =>
              player.scrollIntoView({ behavior: "smooth", block: "start" })
            )
            .catch((error) =>
              setStatus(error instanceof Error ? error.message : String(error), "error")
            );
        });
        recentEl.appendChild(button);
      }
      recentCard.hidden = false;
    } catch (error) {
      /* recent list is a convenience only */
    }
  }

  // --- phone/tablet (v0.4) ----------------------------------------------
  // The laptop can sit in another room: the phone in front of the piano opens
  // the same page over the LAN. The setup card shows that address and a QR.
  async function loadLanInfo() {
    if (!lanRow) return;
    try {
      const response = await fetch("/api/piano/lan", { cache: "no-store" });
      if (!response.ok) return;
      const info = await response.json();
      if (!info || !info.url) return;
      if (lanUrl) {
        lanUrl.href = info.url;
        lanUrl.textContent = info.url;
      }
      if (lanQr) {
        lanQr.src = `${info.qr}?t=${Date.now()}`;
        lanQr.hidden = false;
      }
      lanRow.hidden = false;
    } catch (error) {
      /* LAN info is a convenience only */
    }
  }

  // --- wiring -----------------------------------------------------------
  let seekDragging = false;

  analyzeButton.addEventListener("click", analyze);
  useSuggestionButton.addEventListener("click", useSuggestion);
  processButton.addEventListener("click", processWindow);
  playButton.addEventListener("click", togglePlay);
  audio.addEventListener("play", () => setPlayLabel(true));
  audio.addEventListener("pause", () => setPlayLabel(false));
  audio.addEventListener("ended", () => {
    setPlayLabel(false);
    if (state.loop) {
      seekTo(0);
      play();
    }
  });
  audio.addEventListener("loadedmetadata", () => {
    if (Number.isFinite(audio.duration) && audio.duration > 0) {
      state.duration = audio.duration;
      applyCycle(false);
    }
  });

  seekInput.addEventListener("input", () => {
    seekDragging = true;
    seekTo(Number(seekInput.value));
  });
  const finishSeek = () => {
    seekDragging = false;
  };
  seekInput.addEventListener("change", finishSeek);
  seekInput.addEventListener("pointerup", finishSeek);

  speedInput.addEventListener("input", () => {
    state.speed = clamp(Number(speedInput.value) || 1, 0.5, 1);
    audio.playbackRate = state.speed;
    speedReadout.textContent = `${Math.round(state.speed * 100)} %`;
  });

  loopInput.addEventListener("change", () => {
    state.loop = loopInput.checked;
  });
  synthInput.addEventListener("change", () => {
    state.synth = synthInput.checked;
    if (state.synth) ensureAudioContext();
    updateBackingHint();
    syncPlayMode();
  });
  if (playOrgButton) {
    playOrgButton.addEventListener("click", () => setPlayMode("org"));
  }
  if (playMidButton) {
    playMidButton.addEventListener("click", () => setPlayMode("mid"));
  }
  if (cycleInput) {
    cycleInput.addEventListener("change", () => applyCycle(true));
  }
  if (cycleLengthInput) {
    cycleLengthInput.addEventListener("change", () => applyCycle(true));
  }
  if (cycleHalfButton) {
    cycleHalfButton.addEventListener("click", () => scaleCycle(0.5));
  }
  if (cycleDoubleButton) {
    cycleDoubleButton.addEventListener("click", () => scaleCycle(2));
  }
  if (backingInput) {
    backingInput.addEventListener("change", applyBacking);
  }
  showLeftInput.addEventListener("change", () => {
    state.showLeft = showLeftInput.checked;
  });
  showRightInput.addEventListener("change", () => {
    state.showRight = showRightInput.checked;
  });

  function applySplit() {
    state.split = clamp(Math.round(Number(splitInput.value) || 60), FIRST_MIDI, LAST_MIDI);
    splitInput.value = String(state.split);
    splitName.textContent = noteName(state.split);
  }
  splitInput.addEventListener("change", applySplit);

  window.addEventListener("keydown", (event) => {
    const tag = event.target && event.target.tagName;
    const typing = ["INPUT", "TEXTAREA", "SELECT"].includes(tag);
    if (typing) return;
    if (event.code === "Space") {
      event.preventDefault();
      togglePlay();
      return;
    }
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      seekTo(currentTime() - 5);
      return;
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      seekTo(currentTime() + 5);
      return;
    }
    if (event.key === "Home") {
      event.preventDefault();
      seekTo(0);
    }
  });

  const resizeObserver =
    typeof ResizeObserver === "function"
      ? new ResizeObserver(() => {
          resizeCanvas();
          fitKeyRange();
          draw();
        })
      : null;
  if (resizeObserver) resizeObserver.observe(canvas);
  window.addEventListener("resize", () => {
    resizeCanvas();
    fitKeyRange();
    draw();
  });

  applySplit();
  if (cycleInput) cycleInput.checked = false;
  if (backingInput) backingInput.checked = readBacking();
  applyBacking();
  syncPlayMode();
  resizeCanvas();
  draw();
  window.requestAnimationFrame(frame);
  refreshRecent();
  loadLanInfo();

  // A phone can be linked straight to one piece: /?piece=<id> (the QR in the
  // player head uses this).
  let initialPiece = "";
  try {
    initialPiece = new URLSearchParams(window.location.search).get("piece") || "";
  } catch (error) {
    initialPiece = "";
  }
  if (initialPiece) {
    loadPiece(initialPiece)
      .then(() => player.scrollIntoView({ block: "start" }))
      .catch((error) =>
        setStatus(
          error instanceof Error ? error.message : String(error),
          "error"
        )
      );
  }
})();
