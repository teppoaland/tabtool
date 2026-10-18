/* TabTool TV view – Phase 0 shell. */
(() => {
  "use strict";

  const statusEl = document.getElementById("api-status");
  const detailEl = document.getElementById("api-detail");
  const versionEl = document.getElementById("version-tag");

  if (!statusEl || !detailEl) return;

  async function loadStatus() {
    try {
      const response = await fetch("/api/health", { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      statusEl.textContent = "Online";
      statusEl.classList.remove("status-error");
      statusEl.classList.add("status-ok");
      detailEl.textContent = `${data.app} v${data.version}`;
      if (versionEl && data.version) {
        versionEl.textContent = `v${data.version}`;
      }
    } catch (error) {
      statusEl.textContent = "Offline";
      statusEl.classList.remove("status-ok");
      statusEl.classList.add("status-error");
      detailEl.textContent = error instanceof Error ? error.message : String(error);
    }
  }

  loadStatus();
})();
