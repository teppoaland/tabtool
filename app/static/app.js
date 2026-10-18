/* TabTool TV view – Phase 2: generate, render and play tabs. */
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
  const exportLinks = Array.from(
    document.querySelectorAll(".exports a[data-format]")
  );

  let api = null;
  let activeTab = null;
  let stream = null;
  let submitting = false;

  function setPlayLabel(playing) {
    if (!playButton) return;
    playButton.textContent = playing ? "PAUSE" : "PLAY";
    playButton.dataset.state = playing ? "playing" : "paused";
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
      return Number.isFinite(audio.duration) ? audio.duration * 1000 : 0;
    },
    playbackRate: 1,
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

  function syncPosition() {
    if (!api || !api.player || !Number.isFinite(audio.currentTime)) return;
    const output = api.player.output;
    if (output && typeof output.updatePosition === "function") {
      output.updatePosition(audio.currentTime * 1000);
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
        display: { scale: 1 },
        player: {
          playerMode: alphaTab.PlayerMode.EnabledExternalMedia,
          enableCursor: true,
          enableUserInteraction: true,
        },
      });
    } catch (error) {
      console.error("alphaTab init failed", error);
      api = null;
      return null;
    }

    api.playerStateChanged.on((args) => {
      // PlayerState.Playing === 1; the UMD bundle does not always expose
      // the enum on the global object.
      setPlayLabel(Number(args.state) === 1);
    });
    api.error.on((error) => console.error("alphaTab", error));
    api.scoreLoaded.on(() => {
      const output = api.player && api.player.output;
      if (output) output.handler = mediaHandler;
    });

    const output = api.player && api.player.output;
    if (output) {
      output.handler = mediaHandler;
    }
    return api;
  }

  function togglePlayback() {
    if (api && activeTab) {
      api.playPause();
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
        `${Math.round(Number(tab.bpm) || 0)} BPM`,
        `${tab.measure_count} bars`,
        `${tab.note_count} notes`,
      ];
      if (meta.tuning) parts.push(String(meta.tuning));
      metaEl.textContent = parts.join(" · ");
    }
    for (const link of exportLinks) {
      link.href = `/api/tabs/${tab.id}/export/${link.dataset.format}`;
    }
  }

  async function loadTab(tabId) {
    try {
      const response = await fetch(`/api/tabs/${tabId}`, { cache: "no-store" });
      if (!response.ok) return;
      const tab = await response.json();
      activeTab = tab;
      try {
        localStorage.setItem("tabtool:lastTab", tab.id);
      } catch (error) {
        /* storage disabled */
      }

      renderTabMeta(tab);
      if (viewerSection) viewerSection.hidden = false;
      audio.src = `/api/tabs/${tab.id}/audio`;
      audio.load();

      const score = await fetch(`/api/tabs/${tab.id}/score/gp5`, {
        cache: "no-store",
      });
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

  async function loadLibrary() {
    if (!libraryEl) return;
    try {
      const response = await fetch("/api/tabs", { cache: "no-store" });
      if (!response.ok) return;
      const tabs = await response.json();
      libraryEl.textContent = "";
      for (const tab of tabs.slice(0, 8)) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "library-item";
        button.textContent = tab.artist
          ? `${tab.artist} — ${tab.title}`
          : tab.title;
        button.addEventListener("click", () => loadTab(tab.id));
        libraryEl.append(button);
      }
      libraryEl.hidden = tabs.length === 0;
    } catch (error) {
      console.error(error);
    }
  }

  function collectOptions() {
    const options = {};
    if (tuningSelect) options.tuning = tuningSelect.value;
    if (gridSelect) options.grid = Number(gridSelect.value);
    if (quickCheckbox && quickCheckbox.checked) options.separate = false;
    return options;
  }

  async function submitJob(event) {
    event.preventDefault();
    if (submitting) return;

    const file = fileInput && fileInput.files ? fileInput.files[0] : null;
    const url = urlInput ? urlInput.value.trim() : "";
    if (!file && !url) {
      setStatus("failed", "Valitse tiedosto tai liitä YouTube-linkki.");
      return;
    }

    const data = new FormData();
    if (file) data.append("file", file);
    if (url) data.append("youtube_url", url);
    data.append("options", JSON.stringify(collectOptions()));
    if (regenerateCheckbox && regenerateCheckbox.checked) {
      data.append("regenerate", "true");
    }

    submitting = true;
    if (generateButton) generateButton.disabled = true;
    setStatus("queued", "");
    setProgress(0, false);

    try {
      const response = await fetch("/api/jobs", { method: "POST", body: data });
      if (!response.ok) {
        setStatus("failed", await readError(response));
        setProgress(1, true);
        return;
      }
      const job = await response.json();
      renderJob(job);
      if (job.status === "ready" && job.tab_id) {
        await loadTab(job.tab_id);
        loadLibrary();
      } else {
        subscribe(job.id);
      }
    } catch (error) {
      setStatus("failed", error instanceof Error ? error.message : String(error));
    } finally {
      submitting = false;
      if (generateButton) generateButton.disabled = false;
    }
  }

  function subscribe(jobId) {
    if (stream) stream.close();
    stream = new EventSource(`/api/jobs/${jobId}/events`);
    stream.onmessage = (event) => {
      let job;
      try {
        job = JSON.parse(event.data);
      } catch (error) {
        return;
      }
      renderJob(job);
      if (job.status === "ready" || job.status === "failed") {
        if (stream) stream.close();
        stream = null;
        if (job.status === "ready" && job.tab_id) {
          loadTab(job.tab_id);
          loadLibrary();
        }
      }
    };
    stream.onerror = () => {
      /* EventSource reconnects automatically; the job row keeps the state. */
    };
  }

  if (form) form.addEventListener("submit", submitJob);
  if (playButton) playButton.addEventListener("click", togglePlayback);
  if (audio) {
    audio.addEventListener("play", () => setPlayLabel(true));
    audio.addEventListener("pause", () => setPlayLabel(false));
    audio.addEventListener("seeked", syncPosition);
    window.setInterval(() => {
      if (!audio.paused) syncPosition();
    }, 50);
  }

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



