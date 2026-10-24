/* AI TabTool settings view (v2.02).
 *
 * The values, bounds and defaults come from /api/settings (app/settings.py),
 * so this page never hard-codes a default. Saving posts only the fields that
 * are on the page; the server validates every value again and returns the
 * stored result.
 */
(() => {
  "use strict";

  const byId = (id) => document.getElementById(id);

  const groupsEl = byId("settings-groups");
  const formEl = byId("settings-form");
  const statusEl = byId("settings-status");
  const saveButton = byId("settings-save");
  const reloadButton = byId("settings-reload");

  let groups = [];
  let fields = [];
  const controls = new Map();

  function setStatus(text, isError) {
    if (!statusEl) return;
    statusEl.textContent = text || "";
    statusEl.classList.toggle("is-error", Boolean(isError));
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

  function formatDefault(field) {
    if (field.kind === "bool") return field.default ? "päällä" : "poissa";
    if (field.kind === "choice") {
      const option = (field.options || []).find(
        (item) => item.value === field.default
      );
      return option ? option.label : String(field.default);
    }
    const unit = field.unit ? ` ${field.unit}` : "";
    return `${field.default}${unit}`;
  }

  // Every control exposes read() and write() so saving stays a plain loop.
  function buildControl(field) {
    if (field.kind === "bool") {
      const input = document.createElement("input");
      input.type = "checkbox";
      input.id = `set-${field.key}`;
      return {
        element: input,
        read: () => Boolean(input.checked),
        write: (value) => {
          input.checked = value !== false;
        },
      };
    }
    if (field.kind === "choice") {
      const select = document.createElement("select");
      select.id = `set-${field.key}`;
      for (const option of field.options || []) {
        const item = document.createElement("option");
        item.value = option.value;
        item.textContent = option.label;
        select.append(item);
      }
      return {
        element: select,
        read: () => select.value,
        write: (value) => {
          select.value = String(value);
        },
      };
    }
    const input = document.createElement("input");
    input.type = "number";
    input.id = `set-${field.key}`;
    if (field.min !== undefined) input.min = String(field.min);
    if (field.max !== undefined) input.max = String(field.max);
    input.step = String(field.step || 1);
    return {
      element: input,
      read: () => {
        const number = Number(input.value);
        return Number.isFinite(number) ? number : field.default;
      },
      write: (value) => {
        input.value = String(value);
      },
    };
  }


  function buildRow(field) {
    const row = document.createElement("div");
    row.className = "settings-row";
    row.dataset.setting = field.key;

    const label = document.createElement("label");
    label.className = "settings-label";
    label.htmlFor = `set-${field.key}`;
    const name = document.createElement("span");
    name.className = "settings-name";
    name.textContent = field.label;
    const help = document.createElement("span");
    help.className = "settings-help";
    help.textContent = field.help || "";
    label.append(name, help);

    const control = buildControl(field);
    const box = document.createElement("span");
    box.className = "settings-control";
    box.append(control.element);
    if (field.kind === "bool") {
      // The checkbox means "shown" for a function and "on" for a default.
      const state = document.createElement("span");
      state.className = "settings-switch-label";
      state.textContent = field.group === "ui" ? "Näytä" : "Päällä";
      box.append(state);
    }
    if (field.unit) {
      const unit = document.createElement("span");
      unit.className = "settings-unit";
      unit.textContent = field.unit;
      box.append(unit);
    }
    const reset = document.createElement("button");
    reset.type = "button";
    reset.className = "ghost small";
    reset.textContent = "OLETUS";
    reset.title = `Palauta oletus: ${formatDefault(field)}`;
    reset.addEventListener("click", () => {
      control.write(field.default);
      setStatus(
        `${field.label}: oletus ${formatDefault(field)}. Muista tallentaa.`
      );
    });
    box.append(reset);

    const hint = document.createElement("span");
    hint.className = "settings-default";
    hint.textContent = `Oletus: ${formatDefault(field)}`;

    row.append(label, box, hint);
    controls.set(field.key, control);
    return row;
  }

  function applyValues(values) {
    for (const [key, control] of controls) {
      if (!values || !Object.prototype.hasOwnProperty.call(values, key)) continue;
      control.write(values[key]);
    }
  }

  function render(values) {
    if (!groupsEl) return;
    controls.clear();
    groupsEl.textContent = "";
    for (const group of groups) {
      const section = document.createElement("section");
      section.className = "settings-group";
      const heading = document.createElement("h2");
      heading.textContent = group.label;
      section.append(heading);
      for (const field of fields.filter((item) => item.group === group.key)) {
        section.append(buildRow(field));
      }
      groupsEl.append(section);
    }
    applyValues(values);
  }

  async function load() {
    setStatus("");
    try {
      const response = await fetch("/api/settings", { cache: "no-store" });
      if (!response.ok) {
        setStatus(await readError(response), true);
        return;
      }
      const data = await response.json();
      groups = Array.isArray(data.groups) ? data.groups : [];
      fields = Array.isArray(data.fields) ? data.fields : [];
      render(data.values || {});
    } catch (error) {
      setStatus("Asetuksia ei saatu ladattua.", true);
    }
  }

  async function save(event) {
    event.preventDefault();
    if (!fields.length) return;
    const payload = {};
    for (const [key, control] of controls) payload[key] = control.read();
    if (saveButton) saveButton.disabled = true;
    setStatus("Tallennetaan…");
    try {
      const response = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        cache: "no-store",
      });
      if (!response.ok) {
        setStatus(await readError(response), true);
        return;
      }
      const data = await response.json();
      applyValues(data.values || {});
      setStatus("Tallennettu.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error), true);
    } finally {
      if (saveButton) saveButton.disabled = false;
    }
  }

  if (formEl) formEl.addEventListener("submit", save);
  if (reloadButton) reloadButton.addEventListener("click", () => load());

  load();
})();
