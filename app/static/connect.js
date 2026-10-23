/* AI TabTool phone pairing (v1.82).
 *
 * The QR is rendered by the server (segno) from the current LAN address, so
 * a dynamic router address works without changing any setting. The image is
 * refreshed when the page is opened again.
 */
(() => {
  "use strict";

  const qr = document.getElementById("connect-qr");
  const urlEl = document.getElementById("connect-url");
  const statusEl = document.getElementById("connect-status");
  const hintEl = document.getElementById("connect-hint");
  const versionEl = document.getElementById("version-tag");

  function setStatus(text, ok) {
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.classList.toggle("status-ok", Boolean(ok));
    statusEl.classList.toggle("status-error", !ok);
  }

  async function load() {
    try {
      const [health, info] = await Promise.all([
        fetch("/api/health", { cache: "no-store" }),
        fetch("/api/lan/info", { cache: "no-store" }),
      ]);
      if (!health.ok || !info.ok) throw new Error("offline");
      const healthData = await health.json();
      const lan = await info.json();
      if (versionEl) versionEl.textContent = `v${healthData.version}`;
      setStatus("Online", true);
      if (!lan.lan) {
        if (qr) qr.hidden = true;
        if (urlEl) urlEl.textContent = `127.0.0.1:${lan.port}`;
        if (hintEl) hintEl.textContent = "Käynnistä palvelin: start-lan.bat";
        return;
      }
      if (qr) {
        qr.hidden = false;
        qr.src = `/api/lan/qr.svg?t=${Date.now()}`;
      }
      if (urlEl) urlEl.textContent = lan.remote_url || "–";
      if (hintEl) {
        hintEl.textContent = lan.pin_required
          ? "QR-koodi pariuttaa puhelimen ilman PINin kirjoittamista."
          : "";
      }
    } catch (error) {
      setStatus("Offline", false);
      if (qr) qr.hidden = true;
      if (hintEl) hintEl.textContent = "Käynnistä palvelin: start-lan.bat";
    }
  }

  load();
})();
