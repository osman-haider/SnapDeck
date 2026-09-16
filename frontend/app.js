// SnapDeck frontend — plain JS, no build step, no framework.
// Talks to the FastAPI backend at window.SNAPDECK_API_BASE (set in index.html).
//
// Uses ?? rather than || so an intentional empty string ("" — same-origin,
// the normal case when the backend serves this file itself) isn't overridden.
const API_BASE = window.SNAPDECK_API_BASE ?? "http://127.0.0.1:8000";

// --------------------------------------------------------------------- //
// State
// --------------------------------------------------------------------- //
// Kept as ordered arrays (not plain objects) so field/chart-point *names*
// remain editable in the UI without losing track of which row is which.
const state = {
  fields: [], // [{ key: string, value: string }]
  chart: [], // [{ label: string, value: string }]
  hasGeneratedOnce: false,
};

// --------------------------------------------------------------------- //
// Element refs
// --------------------------------------------------------------------- //
const el = {
  tabButtons: document.querySelectorAll(".tab-btn"),
  tabPanels: {
    sample: document.getElementById("tab-sample"),
    csv: document.getElementById("tab-csv"),
    sheet: document.getElementById("tab-sheet"),
  },
  csvFileInput: document.getElementById("csv-file-input"),
  loadCsvBtn: document.getElementById("load-csv-btn"),
  sheetUrlInput: document.getElementById("sheet-url-input"),
  loadSheetBtn: document.getElementById("load-sheet-btn"),
  sourceStatus: document.getElementById("source-status"),

  fieldsTable: document.getElementById("fields-table"),
  addFieldBtn: document.getElementById("add-field-btn"),

  chartTable: document.getElementById("chart-table"),
  addChartRowBtn: document.getElementById("add-chart-row-btn"),

  includeChartCheckbox: document.getElementById("include-chart-checkbox"),
  chartTitleRow: document.getElementById("chart-title-row"),
  chartTitleInput: document.getElementById("chart-title-input"),
  customTemplateInput: document.getElementById("custom-template-input"),
  generateBtn: document.getElementById("generate-btn"),

  previewEmpty: document.getElementById("preview-empty"),
  previewContent: document.getElementById("preview-content"),
  previewTitle: document.getElementById("preview-title"),
  previewSubtitle: document.getElementById("preview-subtitle"),
  previewMetrics: document.getElementById("preview-metrics"),
  previewChartCard: document.getElementById("preview-chart-card"),
  previewChartImage: document.getElementById("preview-chart-image"),
  previewInsight: document.getElementById("preview-insight"),
  previewWarnings: document.getElementById("preview-warnings"),
  downloadLink: document.getElementById("download-link"),
};

// --------------------------------------------------------------------- //
// Small helpers
// --------------------------------------------------------------------- //

function setStatus(targetEl, message, kind = "info") {
  if (!message) {
    targetEl.textContent = "";
    targetEl.className = "mt-3 text-sm";
    return;
  }
  const colors = {
    info: "text-slate-500",
    success: "text-emerald-600",
    error: "text-red-600",
    warning: "text-amber-600",
  };
  targetEl.className = `mt-3 text-sm ${colors[kind] || colors.info}`;
  targetEl.textContent = message;
}

function objectToPairs(obj) {
  return Object.entries(obj || {}).map(([key, value]) => ({ key, value: String(value) }));
}

function pairsToFieldsObject(pairs) {
  const out = {};
  for (const { key, value } of pairs) {
    const trimmedKey = (key || "").trim();
    if (trimmedKey) out[trimmedKey] = value;
  }
  return out;
}

function pairsToChartArray(pairs) {
  const out = [];
  for (const { label, value } of pairs) {
    const trimmedLabel = (label || "").trim();
    const numeric = Number(value);
    if (trimmedLabel && value !== "" && !Number.isNaN(numeric)) {
      out.push({ label: trimmedLabel, value: numeric });
    }
  }
  return out;
}

// --------------------------------------------------------------------- //
// Tabs
// --------------------------------------------------------------------- //

el.tabButtons.forEach((button) => {
  button.addEventListener("click", () => {
    el.tabButtons.forEach((b) => b.classList.remove("tab-btn-active"));
    button.classList.add("tab-btn-active");
    Object.entries(el.tabPanels).forEach(([name, panel]) => {
      panel.classList.toggle("hidden", name !== button.dataset.tab);
    });
    setStatus(el.sourceStatus, "");
  });
});

// --------------------------------------------------------------------- //
// Fields table (editable key/value rows)
// --------------------------------------------------------------------- //

function renderFieldsTable() {
  el.fieldsTable.innerHTML = "";
  state.fields.forEach((pair, index) => {
    const row = document.createElement("div");
    row.className = "field-row";

    const keyInput = document.createElement("input");
    keyInput.value = pair.key;
    keyInput.placeholder = "field_name";
    keyInput.addEventListener("input", (e) => {
      state.fields[index].key = e.target.value;
    });

    const valueInput = document.createElement("input");
    valueInput.value = pair.value;
    valueInput.placeholder = "value";
    valueInput.addEventListener("input", (e) => {
      state.fields[index].value = e.target.value;
    });

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "row-remove-btn";
    removeBtn.textContent = "Remove";
    removeBtn.addEventListener("click", () => {
      state.fields.splice(index, 1);
      renderFieldsTable();
    });

    row.append(keyInput, valueInput, removeBtn);
    el.fieldsTable.appendChild(row);
  });
}

el.addFieldBtn.addEventListener("click", () => {
  state.fields.push({ key: "", value: "" });
  renderFieldsTable();
});

// --------------------------------------------------------------------- //
// Chart data table (editable label/value rows)
// --------------------------------------------------------------------- //

function renderChartTable() {
  el.chartTable.innerHTML = "";
  if (state.chart.length === 0) {
    const empty = document.createElement("p");
    empty.className = "text-xs text-slate-400";
    empty.textContent = "No chart data yet — add a point, or load data that includes some.";
    el.chartTable.appendChild(empty);
  }
  state.chart.forEach((pair, index) => {
    const row = document.createElement("div");
    row.className = "chart-row";

    const labelInput = document.createElement("input");
    labelInput.value = pair.label;
    labelInput.placeholder = "label (e.g. APAC)";
    labelInput.addEventListener("input", (e) => {
      state.chart[index].label = e.target.value;
    });

    const valueInput = document.createElement("input");
    valueInput.type = "number";
    valueInput.value = pair.value;
    valueInput.placeholder = "value";
    valueInput.addEventListener("input", (e) => {
      state.chart[index].value = e.target.value;
    });

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "row-remove-btn";
    removeBtn.textContent = "Remove";
    removeBtn.addEventListener("click", () => {
      state.chart.splice(index, 1);
      renderChartTable();
    });

    row.append(labelInput, valueInput, removeBtn);
    el.chartTable.appendChild(row);
  });
}

el.addChartRowBtn.addEventListener("click", () => {
  state.chart.push({ label: "", value: "" });
  renderChartTable();
});

// --------------------------------------------------------------------- //
// Data source loading
// --------------------------------------------------------------------- //

async function loadSample() {
  setStatus(el.sourceStatus, "Loading sample data…");
  try {
    const response = await fetch(`${API_BASE}/api/sample`);
    if (!response.ok) throw new Error(`Server responded with ${response.status}`);
    const data = await response.json();
    state.fields = objectToPairs(data.fields);
    state.chart = (data.chart || []).map((point) => ({ label: point.label, value: String(point.value) }));
    renderFieldsTable();
    renderChartTable();
    setStatus(
      el.sourceStatus,
      `Loaded sample data: ${state.fields.length} fields, ${state.chart.length} chart points.`,
      "success"
    );
  } catch (err) {
    setStatus(
      el.sourceStatus,
      `Could not load the sample data (${err.message}). Is the backend running at ${API_BASE}?`,
      "error"
    );
  }
}

async function loadCsv() {
  const file = el.csvFileInput.files[0];
  if (!file) {
    setStatus(el.sourceStatus, "Choose a CSV file first.", "error");
    return;
  }
  el.loadCsvBtn.disabled = true;
  setStatus(el.sourceStatus, "Parsing CSV…");
  try {
    const formData = new FormData();
    formData.append("source_type", "csv");
    formData.append("file", file);
    const response = await fetch(`${API_BASE}/api/parse`, { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Could not parse that CSV.");
    state.fields = objectToPairs(data.fields);
    state.chart = (data.chart || []).map((point) => ({ label: point.label, value: String(point.value) }));
    renderFieldsTable();
    renderChartTable();
    const warningNote = data.warnings?.length ? ` (${data.warnings.length} warning(s) — see console)` : "";
    if (data.warnings?.length) console.warn("SnapDeck parse warnings:", data.warnings);
    setStatus(
      el.sourceStatus,
      `Loaded ${state.fields.length} fields and ${state.chart.length} chart points from your CSV.${warningNote}`,
      "success"
    );
  } catch (err) {
    setStatus(el.sourceStatus, err.message, "error");
  } finally {
    el.loadCsvBtn.disabled = false;
  }
}

async function loadSheet() {
  const url = el.sheetUrlInput.value.trim();
  if (!url) {
    setStatus(el.sourceStatus, "Paste a Google Sheet URL first.", "error");
    return;
  }
  el.loadSheetBtn.disabled = true;
  setStatus(el.sourceStatus, "Fetching Google Sheet…");
  try {
    const formData = new FormData();
    formData.append("source_type", "sheet");
    formData.append("sheet_url", url);
    const response = await fetch(`${API_BASE}/api/parse`, { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Could not read that sheet.");
    state.fields = objectToPairs(data.fields);
    state.chart = (data.chart || []).map((point) => ({ label: point.label, value: String(point.value) }));
    renderFieldsTable();
    renderChartTable();
    setStatus(
      el.sourceStatus,
      `Loaded ${state.fields.length} fields and ${state.chart.length} chart points from the sheet.`,
      "success"
    );
  } catch (err) {
    setStatus(el.sourceStatus, err.message, "error");
  } finally {
    el.loadSheetBtn.disabled = false;
  }
}

el.loadCsvBtn.addEventListener("click", loadCsv);
el.loadSheetBtn.addEventListener("click", loadSheet);
el.sheetUrlInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") loadSheet();
});

// --------------------------------------------------------------------- //
// Chart toggle
// --------------------------------------------------------------------- //

el.includeChartCheckbox.addEventListener("change", () => {
  el.chartTitleRow.classList.toggle("hidden", !el.includeChartCheckbox.checked);
});

// --------------------------------------------------------------------- //
// Generate / Regenerate
// --------------------------------------------------------------------- //

function renderPreview(data) {
  el.previewEmpty.classList.add("hidden");
  el.previewContent.classList.remove("hidden");

  el.previewTitle.textContent = data.preview.title || "(no title field set)";
  el.previewSubtitle.textContent = data.preview.subtitle || "";

  el.previewMetrics.innerHTML = "";
  data.preview.metrics.forEach((metric) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="font-medium text-slate-900">${metric.label}:</span> ${metric.value}`;
    el.previewMetrics.appendChild(li);
  });

  if (data.preview.chart_image_base64) {
    el.previewChartCard.classList.remove("hidden");
    el.previewChartImage.src = `data:image/png;base64,${data.preview.chart_image_base64}`;
  } else {
    el.previewChartCard.classList.add("hidden");
    el.previewChartImage.removeAttribute("src");
  }

  el.previewInsight.textContent = data.preview.insight;

  if (data.warnings && data.warnings.length) {
    el.previewWarnings.classList.remove("hidden");
    el.previewWarnings.innerHTML = `<strong>Heads up:</strong> ${data.warnings.join(" ")}`;
  } else {
    el.previewWarnings.classList.add("hidden");
  }

  el.downloadLink.href = `${API_BASE}${data.download_url}`;
  el.downloadLink.setAttribute("download", data.filename);
}

async function generate() {
  const fieldsObj = pairsToFieldsObject(state.fields);
  const chartArr = pairsToChartArray(state.chart);
  const templateType = document.querySelector('input[name="template_type"]:checked').value;
  const includeChart = el.includeChartCheckbox.checked;
  const chartTitle = el.chartTitleInput.value.trim() || "Chart";
  const customTemplateFile = el.customTemplateInput.files[0];

  const formData = new FormData();
  formData.append("fields", JSON.stringify(fieldsObj));
  formData.append("chart", JSON.stringify(chartArr));
  formData.append("template_type", templateType);
  formData.append("include_chart", includeChart ? "true" : "false");
  formData.append("chart_title", chartTitle);
  if (customTemplateFile) formData.append("template_file", customTemplateFile);

  el.generateBtn.disabled = true;
  el.generateBtn.innerHTML = `<span class="spinner"></span> ${
    state.hasGeneratedOnce ? "Regenerating…" : "Generating…"
  }`;

  try {
    const response = await fetch(`${API_BASE}/api/render`, { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Something went wrong generating the file.");
    renderPreview(data);
    state.hasGeneratedOnce = true;
  } catch (err) {
    setStatus(el.sourceStatus, `Generate failed: ${err.message}`, "error");
  } finally {
    el.generateBtn.disabled = false;
    el.generateBtn.textContent = state.hasGeneratedOnce ? "Regenerate" : "Generate";
  }
}

el.generateBtn.addEventListener("click", generate);

// --------------------------------------------------------------------- //
// Init
// --------------------------------------------------------------------- //

loadSample();
