const SENSOR_ROOT = "Temperature sensors data - split sheets";
let cacheBust = Date.now();
let comparisonRows = [];

const RESULT_FOLDERS = [
  "correlation_model_results",
  "thermocouple_identicool_results",
  "thermocouple_wireless_results",
  "thermocouple_relationship_comparison",
  "lagged_thermocouple_wireless_results",
  "exponential_thermal_model_results",
];

// One upload slot per required sensor workbook — keeps uploads segregated by
// sensor so the analysis scripts always see one clean file per input.
const UPLOAD_SLOTS = [
  { key: "identicool1", label: "IdentiCool Temperature Sensor 1", filename: "IdentiCool Temperature Sensor 1.xlsx" },
  { key: "identicool2", label: "IdentiCool Temperature Sensor 2", filename: "IdentiCool Temperature Sensor 2.xlsx" },
  { key: "thermo30", label: "Thermocouple TA 30C", filename: "Thermocouple TA 30C.xlsx" },
  { key: "thermo37", label: "Thermocouple TA 37C", filename: "Thermocouple TA 37C.xlsx" },
  { key: "wireless1", label: "Wireless Temperature Sensor 1", filename: "Wireless Temperature Sensor 1.xlsx" },
  { key: "wireless2", label: "Wireless Temperature Sensor 2", filename: "Wireless Temperature Sensor 2.xlsx" },
];

function imgUrl(relPath) {
  return encodeURI("/" + SENSOR_ROOT + "/" + relPath) + "?t=" + cacheBust;
}

function csvPath(relPath) {
  return SENSOR_ROOT + "/" + relPath;
}

async function fetchJSON(url, opts) {
  const res = await fetch(url, opts);
  return res.json();
}

async function fetchCSV(relPath) {
  const data = await fetchJSON("/api/csv?path=" + encodeURIComponent(csvPath(relPath)));
  if (data.error) throw new Error(data.error);
  data.rows.forEach((r) => {
    ["R2", "RMSE", "MAE", "Pearson_r"].forEach((k) => {
      if (r[k] !== undefined) r[k] = parseFloat(r[k]);
    });
  });
  return data.rows;
}

function fmt(n, digits = 3) {
  if (n === undefined || n === null || Number.isNaN(n)) return "&mdash;";
  return n.toFixed(digits);
}

function fmtC(n) {
  return fmt(n, 2) + "&deg;C";
}

// ---- generic 6-model results table --------------------------------------
function buildModelTableHTML(rows) {
  let bestIdx = 0;
  rows.forEach((r, i) => {
    if (r.R2 > rows[bestIdx].R2) bestIdx = i;
  });
  let html = "<table><tr><th>Model</th><th>R&sup2;</th><th>Pearson r</th><th>RMSE</th><th>MAE</th></tr>";
  rows.forEach((r, i) => {
    const winner = i === bestIdx ? " winner" : "";
    const r2cls = r.R2 < 0 ? " neg" : "";
    html += `<tr class="${winner.trim()}"><td>${r.Model}</td><td class="${r2cls.trim()}">${fmt(r.R2)}</td><td>${fmt(r.Pearson_r)}</td><td>${fmtC(r.RMSE)}</td><td>${fmtC(r.MAE)}</td></tr>`;
  });
  html += "</table>";
  return { html, best: rows[bestIdx] };
}

async function renderModelTable(containerId, relPath) {
  const el = document.getElementById(containerId);
  el.innerHTML = "<p class='subtitle'>Loading&hellip;</p>";
  try {
    const rows = await fetchCSV(relPath);
    const { html } = buildModelTableHTML(rows);
    el.innerHTML = html;
  } catch (e) {
    el.innerHTML = `<p class="callout warn">Could not load ${relPath}: ${e.message}. Run the analysis scripts first.</p>`;
  }
}

// ---- tabs -----------------------------------------------------------------
function initTabs() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
    });
  });
}

// ---- images -----------------------------------------------------------------
function setStaticImages() {
  const map = {
    "img-overview-30": "correlation_model_results/30C_aligned_temperature_trends.png",
    "img-overview-37": "correlation_model_results/37C_aligned_temperature_trends.png",
    "img-overview-r2": "thermocouple_relationship_comparison/best_model_r2_comparison.png",
    "img-overview-pearson": "thermocouple_relationship_comparison/best_model_pearson_comparison.png",

    "img-t30-trends": "correlation_model_results/30C_aligned_temperature_trends.png",
    "img-t30-corr": "correlation_model_results/30C_correlation_matrix.png",
    "img-t30-identicool": "thermocouple_identicool_results/30C_thermocouple_identicool_model_results.png",
    "img-t30-wireless": "thermocouple_wireless_results/30C_thermocouple_wireless_model_results.png",

    "img-t37-trends": "correlation_model_results/37C_aligned_temperature_trends.png",
    "img-t37-corr": "correlation_model_results/37C_correlation_matrix.png",
    "img-t37-identicool": "thermocouple_identicool_results/37C_thermocouple_identicool_model_results.png",
    "img-t37-wireless": "thermocouple_wireless_results/37C_thermocouple_wireless_model_results.png",

    "img-cmp-r2": "thermocouple_relationship_comparison/best_model_r2_comparison.png",
    "img-cmp-pearson": "thermocouple_relationship_comparison/best_model_pearson_comparison.png",
    "img-cmp-rmse": "thermocouple_relationship_comparison/best_model_rmse_comparison.png",

    "img-lag-30": "lagged_thermocouple_wireless_results/30C_lagged_model_results.png",
    "img-lag-37": "lagged_thermocouple_wireless_results/37C_lagged_model_results.png",
    "img-phys-30": "exponential_thermal_model_results/30C_exponential_thermal_fit.png",
    "img-phys-37": "exponential_thermal_model_results/37C_exponential_thermal_fit.png",
  };
  Object.entries(map).forEach(([id, rel]) => {
    const el = document.getElementById(id);
    if (el) el.src = imgUrl(rel);
  });
}

// ---- overview ---------------------------------------------------------------
async function loadOverview() {
  const cardsEl = document.getElementById("overviewCards");
  try {
    const [byTemp, combined] = await Promise.all([
      fetchCSV("thermocouple_relationship_comparison/best_relationship_by_temperature.csv"),
      fetchCSV("thermocouple_relationship_comparison/all_model_metrics_combined.csv"),
    ]);
    const row30 = byTemp.find((r) => r.Temperature === "30C");
    const row37 = byTemp.find((r) => r.Temperature === "37C");
    const overall = computeOverallVerdict(combined);

    cardsEl.innerHTML = `
      <div class="card">
        <div class="card-label">Best 30&deg;C Match</div>
        <div class="card-value">${row30 ? row30.Relationship : "&mdash;"}</div>
        <div class="card-sub">${row30 ? row30.Model + " &middot; R&sup2; " + fmt(row30.R2) : ""}</div>
      </div>
      <div class="card aqua">
        <div class="card-label">Best 37&deg;C Match</div>
        <div class="card-value">${row37 ? row37.Relationship : "&mdash;"}</div>
        <div class="card-sub">${row37 ? row37.Model + " &middot; R&sup2; " + fmt(row37.R2) : ""}</div>
      </div>
      <div class="card violet">
        <div class="card-label">Overall Most Reliable</div>
        <div class="card-value">${overall.name}</div>
        <div class="card-sub">Avg R&sup2; ${fmt(overall.avgR2)} across both temperatures</div>
      </div>`;
  } catch (e) {
    cardsEl.innerHTML = `<p class="callout warn">Results not found yet &mdash; run the analysis scripts first.</p>`;
  }
}

function computeOverallVerdict(rows) {
  const byRel = {};
  rows.forEach((r) => {
    byRel[r.Relationship] = byRel[r.Relationship] || {};
    const cur = byRel[r.Relationship][r.Temperature];
    if (!cur || r.R2 > cur.R2) byRel[r.Relationship][r.Temperature] = r;
  });
  let best = null;
  Object.entries(byRel).forEach(([name, byTempObj]) => {
    const vals = Object.values(byTempObj);
    const avgR2 = vals.reduce((s, r) => s + r.R2, 0) / vals.length;
    if (!best || avgR2 > best.avgR2) best = { name, avgR2 };
  });
  return best || { name: "&mdash;", avgR2: NaN };
}

// ---- comparison tab -----------------------------------------------------------------
async function loadComparison() {
  const tableEl = document.getElementById("table-comparison");
  const verdictEl = document.getElementById("comparisonVerdict");
  try {
    comparisonRows = await fetchCSV("thermocouple_relationship_comparison/all_model_metrics_combined.csv");
    const relSel = document.getElementById("filterRel");
    const rels = [...new Set(comparisonRows.map((r) => r.Relationship))];
    relSel.innerHTML = '<option value="all">All</option>' + rels.map((r) => `<option value="${r}">${r}</option>`).join("");
    renderComparisonTable();
    const overall = computeOverallVerdict(comparisonRows);
    verdictEl.innerHTML = `Overall stronger relationship: <strong>${overall.name}</strong> (average R&sup2; = ${fmt(overall.avgR2)} across 30&deg;C and 37&deg;C).`;
  } catch (e) {
    tableEl.innerHTML = `<p class="callout warn">Comparison results not found yet &mdash; run the analysis scripts first.</p>`;
    verdictEl.textContent = "";
  }
}

function renderComparisonTable() {
  const tempFilter = document.getElementById("filterTemp").value;
  const relFilter = document.getElementById("filterRel").value;
  const tableEl = document.getElementById("table-comparison");

  let rows = comparisonRows.filter(
    (r) => (tempFilter === "all" || r.Temperature === tempFilter) && (relFilter === "all" || r.Relationship === relFilter)
  );

  // group by Temperature + Relationship, mark the best-R2 row in each group
  const groups = {};
  rows.forEach((r) => {
    const key = r.Temperature + "|" + r.Relationship;
    groups[key] = groups[key] || [];
    groups[key].push(r);
  });

  let html = "<table><tr><th>Temperature</th><th>Relationship</th><th>Model</th><th>R&sup2;</th><th>Pearson r</th><th>RMSE</th><th>MAE</th></tr>";
  Object.entries(groups).forEach(([key, groupRows]) => {
    let bestIdx = 0;
    groupRows.forEach((r, i) => { if (r.R2 > groupRows[bestIdx].R2) bestIdx = i; });
    groupRows.forEach((r, i) => {
      const winner = i === bestIdx ? " winner" : "";
      const r2cls = r.R2 < 0 ? " neg" : "";
      html += `<tr class="${winner.trim()}"><td>${r.Temperature}</td><td>${r.Relationship}</td><td>${r.Model}</td><td class="${r2cls.trim()}">${fmt(r.R2)}</td><td>${fmt(r.Pearson_r)}</td><td>${fmtC(r.RMSE)}</td><td>${fmtC(r.MAE)}</td></tr>`;
    });
  });
  html += "</table>";
  tableEl.innerHTML = html;
}

// ---- dataset management -----------------------------------------------------------------
async function loadDatasetStatus() {
  const data = await fetchJSON("/api/dataset-status");
  const pill = document.getElementById("datasetPill");
  const allFound = data.files.every((f) => f.found);
  pill.className = "pill " + (allFound ? "ok" : "bad");
  pill.innerHTML = `<span class="dot"></span> ${allFound ? "All datasets found" : data.files.filter((f) => !f.found).length + " file(s) missing"}`;

  const tableEl = document.getElementById("datasetTable");
  let html = "<table class='status-table'><tr><th>File</th><th>Status</th><th>Last updated</th></tr>";
  data.files.forEach((f) => {
    html += `<tr><td>${f.name}</td><td class="${f.found ? "status-found" : "status-missing"}">${f.found ? "Found" : "Missing"}</td><td>${f.modified || "&mdash;"}</td></tr>`;
  });
  html += "</table>";
  tableEl.innerHTML = html;
}

function populateFolderSelect() {
  const sel = document.getElementById("folderSelect");
  sel.innerHTML = RESULT_FOLDERS.map((f) => `<option value="${f}">${f}</option>`).join("");
}

// ---- results explorer -----------------------------------------------------------------
async function loadExplorer() {
  const listEl = document.getElementById("explorerList");
  const data = await fetchJSON("/api/results-index");
  let html = "";
  Object.entries(data.folders).forEach(([folder, files]) => {
    html += `<details class="folder"><summary>${folder} (${files.length} file${files.length === 1 ? "" : "s"})</summary><ul>`;
    if (files.length === 0) {
      html += `<li><span class="muted">No files yet &mdash; run the analysis scripts.</span></li>`;
    } else {
      files.forEach((f) => {
        html += `<li><a href="/${encodeURI(f.relpath)}" target="_blank">${f.name}</a><span class="muted">${f.modified}</span></li>`;
      });
    }
    html += "</ul></details>";
  });
  listEl.innerHTML = html;
}

// ---- run analysis -----------------------------------------------------------------
function showRunLog() {
  document.getElementById("runLog").classList.add("show");
}
function hideRunLog() {
  document.getElementById("runLog").classList.remove("show");
}

async function runAllScripts() {
  const buttons = [document.getElementById("runAllBtn"), document.getElementById("dsRunAllBtn")];
  buttons.forEach((b) => (b.disabled = true));
  const logBody = document.getElementById("runLogBody");
  logBody.innerHTML = "<p>Running analysis scripts, this can take a minute&hellip;</p>";
  showRunLog();
  try {
    const data = await fetchJSON("/api/run-all", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    logBody.innerHTML = data.results
      .map(
        (r) => `<div class="log-item ${r.ok ? "ok" : "fail"}">
          <div class="name">${r.script} (${r.duration}s)</div>
          ${r.ok ? "" : `<pre>${(r.stderr || "").slice(0, 600)}</pre>`}
        </div>`
      )
      .join("");
    cacheBust = Date.now();
    await refreshAllData();
  } catch (e) {
    logBody.innerHTML = `<p class="callout warn">Run failed: ${e.message}</p>`;
  } finally {
    buttons.forEach((b) => (b.disabled = false));
  }
}

async function openFolder() {
  const folder = document.getElementById("folderSelect").value;
  const res = await fetchJSON("/api/open-folder", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ folder }),
  });
  if (!res.ok) alert("Could not open folder: " + (res.error || "unknown error"));
}

// ---- top-level refresh -----------------------------------------------------------------
async function refreshAllData() {
  setStaticImages();
  await Promise.all([
    loadOverview(),
    loadDatasetStatus(),
    loadExplorer(),
    loadComparison(),
    renderModelTable("table-t30-identicool", "thermocouple_identicool_results/30C_thermocouple_identicool_model_metrics.csv"),
    renderModelTable("table-t30-wireless", "thermocouple_wireless_results/30C_thermocouple_wireless_model_metrics.csv"),
    renderModelTable("table-t37-identicool", "thermocouple_identicool_results/37C_thermocouple_identicool_model_metrics.csv"),
    renderModelTable("table-t37-wireless", "thermocouple_wireless_results/37C_thermocouple_wireless_model_metrics.csv"),
    renderModelTable("table-lag-30", "lagged_thermocouple_wireless_results/30C_lagged_model_metrics.csv"),
    renderModelTable("table-lag-37", "lagged_thermocouple_wireless_results/37C_lagged_model_metrics.csv"),
    renderPhysicsTable(),
  ]);
}

async function renderPhysicsTable() {
  const el = document.getElementById("table-physics");
  el.innerHTML = "<p class='subtitle'>Loading&hellip;</p>";
  try {
    const [r30, r37] = await Promise.all([
      fetchCSV("exponential_thermal_model_results/30C_exponential_thermal_metrics.csv"),
      fetchCSV("exponential_thermal_model_results/37C_exponential_thermal_metrics.csv"),
    ]);
    let html = "<table><tr><th>Condition</th><th>Model</th><th>One-step R&sup2;</th><th>Recursive R&sup2;</th><th>Recursive RMSE</th></tr>";
    const addRows = (label, rows) => {
      rows.forEach((r) => {
        const oneStep = parseFloat(r.OneStep_R2);
        const rec = parseFloat(r.Recursive_R2);
        const rmse = parseFloat(r.Recursive_RMSE);
        const cls = rec < 0 ? " neg" : "";
        html += `<tr><td>${label}</td><td>${r.Model}</td><td>${fmt(oneStep)}</td><td class="${cls.trim()}">${fmt(rec)}</td><td>${fmtC(rmse)}</td></tr>`;
      });
    };
    addRows("30&deg;C", r30);
    addRows("37&deg;C", r37);
    html += "</table>";
    el.innerHTML = html;
  } catch (e) {
    el.innerHTML = `<p class="callout warn">Physics model results not found yet &mdash; run the analysis scripts first.</p>`;
  }
}

// ---- upload modal -----------------------------------------------------------------
function arrayBufferToBase64(buffer) {
  let binary = "";
  const bytes = new Uint8Array(buffer);
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

function renderUploadGrid() {
  const grid = document.getElementById("uploadGrid");
  grid.innerHTML = UPLOAD_SLOTS.map(
    (slot) => `
    <div class="upload-slot" id="slot-${slot.key}">
      <div class="slot-label">${slot.label}</div>
      <div class="slot-filename">${slot.filename}</div>
      <input type="file" accept=".xlsx,.xls,.csv" data-slot="${slot.key}">
      <div class="slot-status" id="slot-status-${slot.key}">No file selected</div>
    </div>`
  ).join("");
  grid.querySelectorAll('input[type="file"]').forEach((input) => {
    input.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (file) handleUpload(e.target.dataset.slot, file);
    });
  });
}

async function handleUpload(slotKey, file) {
  const statusEl = document.getElementById("slot-status-" + slotKey);
  statusEl.className = "slot-status pending";
  statusEl.textContent = "Uploading " + file.name + "…";
  try {
    const buffer = await file.arrayBuffer();
    const base64 = arrayBufferToBase64(buffer);
    const res = await fetchJSON("/api/upload", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slot: slotKey, filename: file.name, data: base64 }),
    });
    if (!res.ok) {
      statusEl.className = "slot-status err";
      statusEl.textContent = res.error || "Upload failed.";
      return;
    }
    if (res.replaced) {
      statusEl.className = "slot-status ok";
      statusEl.textContent = "Replaced " + res.replaced + " — ready to run.";
      loadDatasetStatus();
    } else {
      statusEl.className = "slot-status pending";
      statusEl.textContent = res.note || "Saved, but not yet usable in the analysis.";
    }
  } catch (e) {
    statusEl.className = "slot-status err";
    statusEl.textContent = "Upload failed: " + e.message;
  }
}

function openUploadModal() {
  renderUploadGrid();
  document.getElementById("uploadModal").classList.add("show");
}
function closeUploadModal() {
  document.getElementById("uploadModal").classList.remove("show");
}

// ---- init -----------------------------------------------------------------
function init() {
  initTabs();
  populateFolderSelect();
  document.getElementById("runAllBtn").addEventListener("click", runAllScripts);
  document.getElementById("dsRunAllBtn").addEventListener("click", runAllScripts);
  document.getElementById("dsRefreshBtn").addEventListener("click", loadDatasetStatus);
  document.getElementById("refreshBtn").addEventListener("click", refreshAllData);
  document.getElementById("dsOpenResultsBtn").addEventListener("click", openFolder);
  document.getElementById("closeLogBtn").addEventListener("click", hideRunLog);
  document.getElementById("filterTemp").addEventListener("change", renderComparisonTable);
  document.getElementById("filterRel").addEventListener("change", renderComparisonTable);
  document.getElementById("uploadBtn").addEventListener("click", openUploadModal);
  document.getElementById("dsUploadBtn").addEventListener("click", openUploadModal);
  document.getElementById("closeUploadModal").addEventListener("click", closeUploadModal);
  document.getElementById("uploadModal").addEventListener("click", (e) => {
    if (e.target.id === "uploadModal") closeUploadModal();
  });
  refreshAllData();
}

document.addEventListener("DOMContentLoaded", init);
