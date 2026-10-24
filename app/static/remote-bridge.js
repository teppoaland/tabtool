/* AI TabTool remote bridge (v1.90) – phone commands for the TV view.
 *
 * Rule 07: this file never touches the playback chain. It only clicks the
 * existing transport controls and dispatches the same DOM events a user
 * would generate, so seekTo / mediaHandler / syncTimeMs and the audio
 * element's own state stay exactly as they are. The phone never sends or
 * receives audio; the TV keeps playing from its local audio file.
 */
(() => {
  "use strict";

  const POLL_MS = 500;
  const REPORT_MS = 1000;
  const WAIT_MS = 6000;
  const QUEUE_LIMIT = 20;

  let lastSeq = 0;
  let polling = false;
  let handling = false;

  const byId = (id) => document.getElementById(id);
  const sleep = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));

  function clamp(value, low, high) {
    const number = Number(value);
    if (!Number.isFinite(number)) return low;
    return Math.min(Math.max(number, low), high);
  }

  function audioEl() {
    const element = byId("audio");
    return element instanceof HTMLAudioElement ? element : null;
  }

  function playButton() {
    return byId("play-button");
  }

  function isPlaying() {
    const button = playButton();
    if (button && button.dataset.state) {
      return button.dataset.state === "playing";
    }
    const audio = audioEl();
    return Boolean(audio && !audio.paused && !audio.ended);
  }

  function readTabId() {
    try {
      return localStorage.getItem("tabtool:lastTab") || "";
    } catch (error) {
      return "";
    }
  }

  function readBar() {
    const readout = byId("bar-readout");
    if (!readout) return null;
    const match = /(\d+)/.exec(readout.textContent || "");
    return match ? Number(match[1]) : null;
  }

  function readRate() {
    const slider = byId("rate-slider");
    return slider ? Number(slider.value) || 1 : 1;
  }

  function readBpm() {
    const input = byId("bpm-input");
    const value = input ? Number(input.value) : NaN;
    return Number.isFinite(value) && value > 0 ? value : null;
  }

  // v2.02: the tracks shown in the tab. The phone lists the instruments and
  // toggles them by clicking the same chips the TV user would click, so the
  // track selection itself stays in app.js (rule 07: nothing here touches the
  // playback chain).
  function readTracks() {
    const host = byId("track-toggles");
    if (!host) return [];
    const chips = Array.from(host.querySelectorAll(".track-chip"));
    return chips
      .slice(0, 32)
      .map((chip) => ({
        index: Number(chip.dataset.trackIndex),
        name: String(chip.textContent || "").trim().slice(0, 40),
        visible: chip.getAttribute("aria-pressed") === "true",
      }))
      .filter(
        (track) =>
          Number.isInteger(track.index) &&
          track.index >= 0 &&
          track.index < 32
      );
  }

  function currentState() {
    const audio = audioEl();
    const titleEl = byId("tab-title");
    const viewer = byId("viewer-section");
    return {
      tab_id: readTabId(),
      title: titleEl ? (titleEl.textContent || "").trim() : "",
      playing: isPlaying(),
      position: audio && Number.isFinite(audio.currentTime) ? audio.currentTime : 0,
      duration: audio && Number.isFinite(audio.duration) ? audio.duration : 0,
      bar: readBar(),
      rate: readRate(),
      bpm: readBpm(),
      tracks: readTracks(),
      visible: Boolean(viewer && !viewer.hidden),
    };
  }

  async function reportState() {
    try {
      await fetch("/api/remote/state", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(currentState()),
        cache: "no-store",
      });
    } catch (error) {
      /* the phone shows the viewer as offline; nothing to do here */
    }
  }

  function setRange(id, value) {
    const element = byId(id);
    if (!element) return false;
    const low = Number(element.min) || 0;
    const high = Number(element.max) || 0;
    const max = high > low ? high : Math.max(low, Number(value) || 0);
    element.value = String(clamp(value, low, max));
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }

  async function waitFor(check, timeout = WAIT_MS) {
    const deadline = Date.now() + timeout;
    while (Date.now() < deadline) {
      const result = check();
      if (result) return result;
      await sleep(80);
    }
    return null;
  }

  async function waitForAudio(timeout = 3000) {
    const audio = audioEl();
    if (!audio || audio.readyState >= 1) return;
    await waitFor(() => {
      const element = audioEl();
      return element && element.readyState >= 1 ? element : null;
    }, timeout);
  }

  // Tab ids are validated on the server to [A-Za-z0-9._-], so the id can go
  // into the selector without escaping.
  async function selectTab(tabId) {
    if (!tabId) return false;
    if (readTabId() === tabId) return true;
    const modal = byId("search-modal");
    if (modal && modal.hidden) {
      const inner = byId("open-search");
      const top = byId("open-search-top");
      const opener = inner && inner.offsetParent ? inner : top;
      if (!opener) return false;
      opener.click();
    }
    const row = await waitFor(() => {
      const item = document.querySelector(
        `.library-item[data-tab-id="${tabId}"]`
      );
      return item ? item.querySelector(".library-open") : null;
    });
    if (!row) return false;
    row.click();
    await waitFor(() => (readTabId() === tabId ? true : null));
    await waitForAudio();
    return true;
  }

  async function runCommand(command) {
    const action = command.action;
    if (action === "select_tab") {
      return selectTab(String(command.value || ""));
    }
    if (action === "play" || action === "pause" || action === "toggle") {
      const button = playButton();
      if (!button || button.disabled) return false;
      const playing = isPlaying();
      if (action === "play" && playing) return true;
      if (action === "pause" && !playing) return true;
      // Clicking the real button keeps count-in and fullscreen behaviour
      // identical to a user pressing PLAY on the TV.
      button.click();
      return true;
    }
    if (action === "seek" || action === "seek_rel") {
      await waitForAudio();
      const audio = audioEl();
      const duration =
        audio && Number.isFinite(audio.duration) ? audio.duration : 0;
      const current = audio ? Number(audio.currentTime) || 0 : 0;
      const target =
        action === "seek" ? Number(command.value) : current + Number(command.value);
      return setRange("seek-slider", duration > 0 ? clamp(target, 0, duration) : target);
    }
    if (action === "rate") {
      const slider = byId("rate-slider");
      if (!slider) return false;
      const target = clamp(
        command.value,
        Number(slider.min) || 0.5,
        Number(slider.max) || 1.5
      );
      return setRange("rate-slider", target);
    }
    if (action === "track") {
      // Clicking the chip runs app.js's own toggleTrack(), so the stored
      // selection and the rendered score stay exactly as on the TV.
      const index = Number(command.value);
      if (!Number.isInteger(index) || index < 0) return false;
      const chip = document.querySelector(
        `#track-toggles .track-chip[data-track-index="${index}"]`
      );
      if (!chip || chip.disabled) return false;
      chip.click();
      reportState();
      return true;
    }
    return false;
  }

  const MAX_SEQ = 9007199254740991;

  // A newly opened TV page must not replay commands that were queued while it
  // was closed. Those belong to an earlier session and would move the
  // playback position, change the rate or select another tab at startup,
  // which looked like a different tab/audio offset on every start.
  async function primeSequence() {
    try {
      const response = await fetch(`/api/remote/commands?since=${MAX_SEQ}`, {
        cache: "no-store",
      });
      if (!response.ok) return;
      const data = await response.json();
      if (typeof data.seq === "number") lastSeq = data.seq;
    } catch (error) {
      /* polling retries later; a restarted server sends reset anyway */
    }
  }

  async function pollOnce() {
    try {
      const response = await fetch(`/api/remote/commands?since=${lastSeq}`, {
        cache: "no-store",
      });
      if (!response.ok) {
        await sleep(2000);
        return;
      }
      const data = await response.json();
      if (data.reset) lastSeq = Number(data.seq) || 0;
      const commands = Array.isArray(data.commands)
        ? data.commands.slice(-QUEUE_LIMIT)
        : [];
      for (const command of commands) {
        try {
          await runCommand(command);
        } catch (error) {
          console.warn("remote command failed", error);
        }
        lastSeq = Math.max(lastSeq, Number(command.seq) || 0);
      }
      // Commands dropped by the TTL or the queue size are skipped, not
      // replayed: a stale "play" must not start after a long pause.
      if (Number(data.seq) > lastSeq) lastSeq = Number(data.seq);
      if (commands.length) reportState();
    } catch (error) {
      await sleep(2000);
    }
  }

  async function loop() {
    while (true) {
      if (!document.hidden) await pollOnce();
      await sleep(POLL_MS);
    }
  }

  (async () => {
    await primeSequence();
    reportState();
    window.setInterval(reportState, REPORT_MS);
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) reportState();
    });
    loop();
  })();
})();
