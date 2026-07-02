# Internal and External Temperature Correlation

This repository contains temperature monitoring workbooks, split sensor workbooks, Python analysis scripts, generated plots, a presentation deck, and a local live dashboard for comparing internal and external temperature sensors.

The core question: can a non-invasive ambient sensor (Wireless) reliably stand in for a direct core-temperature probe (Thermocouple), or does an internal reference probe (IdentiCool) need to be used instead?

## Project structure

```text
.
├── Temperature Monitoring Data.xlsx
├── Temperature sensors data.xlsx
├── Temperature Monitoring Data - split sheets/
├── Temperature_Correlation_Presentation.html   # slide-deck results walkthrough (open in a browser)
├── Run Dashboard.bat                            # double-click to launch the live dashboard
├── WIREFRAME.md                                 # original dashboard wireframe/design notes
├── dashboard/                                    # local live dashboard (server + UI)
│   ├── server.py
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── Temperature sensors data - split sheets/
│   ├── analyze_sensor_correlations.py
│   ├── analyze_thermocouple_wireless_correlations.py
│   ├── analyze_thermocouple_identicool_correlations.py
│   ├── compare_thermocouple_relationships.py
│   ├── analyze_lagged_thermocouple_wireless.py
│   ├── analyze_exponential_thermal_models.py
│   ├── correlation_model_results/
│   ├── thermocouple_wireless_results/
│   ├── thermocouple_identicool_results/
│   ├── thermocouple_relationship_comparison/
│   ├── lagged_thermocouple_wireless_results/
│   └── exponential_thermal_model_results/
```

## Requirements

Use Python 3.10 or newer.

Install the required packages:

```bash
pip install pandas openpyxl matplotlib scikit-learn numpy
```

No extra packages are needed for the dashboard server — it's built on the Python standard library only.

## Running the scripts

Open a terminal in the repository root, then move into the sensor folder:

```bash
cd "Temperature sensors data - split sheets"
```

Run each stage in order (later scripts depend on the output of earlier ones):

```bash
python analyze_sensor_correlations.py                    # baseline: all three sensors aligned
python analyze_thermocouple_identicool_correlations.py   # Thermocouple vs IdentiCool
python analyze_thermocouple_wireless_correlations.py     # Thermocouple vs Wireless, same instant
python compare_thermocouple_relationships.py             # head-to-head reliability verdict
python analyze_lagged_thermocouple_wireless.py           # Thermocouple vs Wireless, 10/20/30 min lag
python analyze_exponential_thermal_models.py             # Newton's Cooling physics-model sanity check
```

Each script writes its own result folder (CSV metrics + PNG plots + a `summary.txt`), matching the list under [Project structure](#project-structure).

The dashboard (below) can also run all six scripts for you, in the correct order, from a button in the browser.

## Live dashboard

A local, no-install dashboard that shows every result above as a live, filterable UI instead of static files.

**To launch it:** double-click `Run Dashboard.bat` at the project root. It starts a local server and opens the dashboard in your browser automatically.

Or manually:

```bash
python dashboard/server.py
```

then open `http://127.0.0.1:8765/dashboard/index.html`. Leave the terminal/console window open while using the dashboard — closing it stops the server. The server only listens on `127.0.0.1` (your own machine), it is not exposed to the network.

What's in it:

- **Overview** — live summary cards (best 30&deg;C match, best 37&deg;C match, overall most reliable relationship), computed from the current result files, not hardcoded.
- **30&deg;C / 37&deg;C Analysis** — aligned trends, correlation matrix, and a live 6-model results table (winning model highlighted) for both IdentiCool and Wireless.
- **Relationship Comparison** — the reliability bar charts plus a filterable table (filter by temperature and/or relationship).
- **Lag & Physics** — the time-lag follow-up and the Newton's Cooling physics-model check.
- **Dataset Management** — live Found/Missing status and last-modified time for the six required source workbooks, plus buttons to validate files, run all scripts, and open a results folder.
- **Results Explorer** — every file currently on disk in each result folder, clickable.
- **Run All Analyses** — re-runs all six scripts in the correct order and refreshes every chart/table with the new results. Takes roughly 20-30 seconds.
- **Upload Data** — replace the source workbooks with new sensor readings without touching the file system by hand. See [Uploading new data](#uploading-new-data) below.

## Presentation deck

`Temperature_Correlation_Presentation.html` is a self-contained, 22-slide walkthrough of the full analysis, written for a non-technical audience — it explains what each sensor measures, what R&sup2;/Pearson r/RMSE/MAE mean in plain language, why six different models are tested, and walks through every result with the winning model highlighted against the other five. Double-click it to open in a browser; no server required. Use the arrow keys or the on-screen buttons to navigate, and the "Fullscreen" button when presenting. `Ctrl+P` (Landscape) exports it to PDF as a backup.

## Uploading new data

From the dashboard, click **Upload Data** (top bar, or in Dataset Management) to open the upload modal. Rules enforced there:

- Upload one file **per sensor** — six separate slots (IdentiCool 1/2, Thermocouple 30C/37C, Wireless 1/2), never a combined workbook.
- Each file should contain only that sensor's own data (a single sheet/page), so the scripts can read it unambiguously.
- Accepted formats: `.xlsx`, `.xls`, `.csv`.

Current behavior:

- **`.xlsx` uploads go live immediately** — they replace the matching required workbook, and "Run All Analyses" trains on the new data right away.
- **`.xls`/`.csv` uploads are saved but not auto-converted yet** — they're staged in `Temperature sensors data - split sheets/_pending_uploads/` for manual conversion to `.xlsx` before they can be used. See [Roadmap](#roadmap--whats-next).

You can also update datasets the manual way: replace the six `.xlsx` files in `Temperature sensors data - split sheets/` directly, keeping the same filenames and the sheet format described in the scripts (IdentiCool/Wireless: 30C data in columns A:B, 37C data in columns F:G; Thermocouple: a `Time` column plus the four numeric probe columns), then rerun the scripts.

## Viewing results

Each result folder contains:

- `summary.txt` or `comparison_summary.txt` with the main model results.
- `.csv` files containing cleaned aligned data and model metrics.
- `.png` plots showing correlations, aligned temperature trends, and model prediction results.

Important comparison outputs:

```text
Temperature sensors data - split sheets/thermocouple_relationship_comparison/comparison_summary.txt
Temperature sensors data - split sheets/thermocouple_relationship_comparison/best_relationship_by_temperature.csv
Temperature sensors data - split sheets/thermocouple_relationship_comparison/best_model_r2_comparison.png
Temperature sensors data - split sheets/thermocouple_relationship_comparison/best_model_pearson_comparison.png
Temperature sensors data - split sheets/lagged_thermocouple_wireless_results/summary.txt
Temperature sensors data - split sheets/exponential_thermal_model_results/summary.txt
```

## Current findings

**Same-instant comparison:** Thermocouple vs IdentiCool is more reliable than Thermocouple vs Wireless at both 30C and 37C.

- 30C: Thermocouple vs IdentiCool using Ridge Regression (R&sup2; = 0.434, Pearson r = 0.703).
- 37C: Thermocouple vs IdentiCool using SVR (R&sup2; = 0.695, Pearson r = 0.865).
- Same-instant Thermocouple vs Wireless is much weaker (R&sup2; = 0.042 at 30C, 0.484 at 37C).

**With a time lag, the picture changes.** Ambient heat takes time to reach core temperature. Re-testing Thermocouple vs Wireless using the wireless reading from 10/20/30 minutes earlier (instead of the same instant) beats IdentiCool outright:

- 30C: Gradient Boosting, R&sup2; = 0.721, Pearson r = 0.850 (vs 0.434 for IdentiCool).
- 37C: Gradient Boosting, R&sup2; = 0.827, Pearson r = 0.920 (vs 0.695 for IdentiCool) — the strongest result in the whole study.

A physics-based sanity check (Newton's Law of Cooling) supports this at 37C (recursive R&sup2; = 0.752) but breaks down at 30C (recursive R&sup2; = &minus;3.681), so the lag-regression model is the more dependable option for now.

**Practical takeaway:** for an immediate same-instant reading, use IdentiCool. If a 10-30 minute delay is acceptable, the non-invasive wireless sensor becomes the single best predictor overall.

## Roadmap / what's next

- **Automatic upload validation** — check that an uploaded `.xlsx` actually matches the expected column layout before treating it as live data, instead of trusting the format silently.
- **Automatic `.xls`/`.csv` conversion** — convert staged uploads into the required `.xlsx` layout automatically instead of requiring manual conversion.
- **Per-script rerun** — rerun a single analysis stage from the dashboard instead of only all-or-nothing.
- **Adjustable lag window** — expose the 10/20/30 minute lag choice as a control in the dashboard so different delays can be tested live, instead of being fixed in the script.
- **Investigate the 30C physics-model divergence** — the Newton's Cooling model fails to generalize at 30C; likely a fitting/data-volume issue worth digging into.
- **More 30C samples** — every pipeline scores lower at 30C than 37C; more data may close that gap.
