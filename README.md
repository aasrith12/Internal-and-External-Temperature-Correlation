# 🌡️ Temperature Intelligence & Pallet Atlas

**From raw sensor readings to predictive models and interactive pallet insights.**

A data analysis and visualization project exploring how internal and external temperature measurements relate, how thermal response changes over time, and how observed pallet measurements compare with Monte Carlo simulations.

🐍 Python · 📊 Statistical modeling · 🎲 Monte Carlo analysis · 🧊 Interactive 3D visualization · 🌐 Offline web interface

## 🎯 Project brief

**Objective:** assess whether non-invasive wireless readings can help estimate internal temperature, then make box-level pallet results easy to explore and trace back to source data.

The work covers data cleaning, sensor alignment, regression benchmarking, lag analysis, thermal modeling, simulation comparisons, and browser-based reporting. Deliverables include reproducible Python scripts, source workbooks, cleaned CSVs, charts, two presentation decks, a local dashboard, and the offline Pallet Atlas.

## ✨ What you can explore

| Component | Capabilities |
| --- | --- |
| **Sensor correlation analysis** | Compare Thermocouple, IdentiCool, and Wireless readings at 30°C and 37°C across six regression models. |
| **Time-lag and thermal models** | Evaluate earlier wireless readings at 10/20/30-minute lags and a Newton’s Law of Cooling model. |
| **Live dashboard** | Browse metrics and plots, check datasets, upload readings, and rerun the sensor pipeline. |
| **Pallet analysis** | Clean state-space and Monte Carlo workbooks; compare box and layer trends, threshold crossings, rankings, and simulation intervals. |
| **Pallet Atlas** | Rotate and zoom a 20-box pallet, separate layers, select boxes and hours, and inspect individual reports. |
| **Data & alignment view** | Inspect source readings, simulations, geometry checks, and downloadable snapshots with SHA-256 fingerprints. |
| **Presentation decks** | Walk through sensor correlation and pallet temperature results in the browser. |

## 🖼️ Preview

![Pallet Atlas interactive dashboard](pallet%20webpage/preview.png)

## 🚀 Quick start

### Explore Pallet Atlas — no installation needed

Open [`pallet webpage/index.html`](pallet%20webpage/index.html) from your local checkout in a modern browser. It runs offline with bundled data and no external JavaScript or font dependencies.

Drag to rotate, scroll to zoom, and click a box to inspect its results. Switch hours or separate layers to explore hidden positions. Open **Data & alignment** to review the underlying records.

See the [Pallet Atlas guide](pallet%20webpage/README.md) for controls, audit details, and data interpretation. GitHub displays HTML source; download or clone the repository to use the pages.

### Run the sensor dashboard

Use **Python 3.10+**. From the repository root:

```bash
python -m pip install pandas openpyxl matplotlib scikit-learn numpy
python dashboard/server.py
```

Open **http://127.0.0.1:8765/dashboard/index.html** and keep the terminal open. On Windows, you can also double-click [`Run Dashboard.bat`](Run%20Dashboard.bat).

The server uses Python’s standard library and listens on your own machine at `127.0.0.1`. Analysis reruns require the packages above.

### View the presentations

Open either file locally in your browser:

- [Sensor Correlation Presentation](Temperature_Correlation_Presentation.html)
- [Pallet Temperature Risk Presentation](Pallet_Temperature_Risk_Presentation.html)

## 🗂️ Repository map

| Location | Contents |
| --- | --- |
| `Temperature Monitoring Data.xlsx` / `Temperature sensors data.xlsx` | Original monitoring and sensor workbooks. |
| `Temperature Monitoring Data - split sheets/` | Split monitoring datasets. |
| `Temperature sensors data - split sheets/` | Sensor inputs, six analysis scripts, and generated result folders. |
| `dashboard/` | Local Python server and dashboard HTML, CSS, and JavaScript. |
| `New folder/` | Pallet source workbooks, cleaning scripts, cleaned data, and state-space/Monte Carlo results. |
| `pallet webpage/` | Pallet Atlas, data alignment page, audited data snapshot, source downloads, and browser checks. |
| `*_Presentation.html` | Browser presentation decks. |
| `WIREFRAME.md` | Original dashboard design notes. |

Keep the existing folder names when running scripts; the pipelines reference these paths.

## 🔬 Reproduce the analyses

### 1. Sensor pipeline

From the repository root, run these stages in order, or select **Run All Analyses** in the dashboard:

```bash
cd "Temperature sensors data - split sheets"
python analyze_sensor_correlations.py
python analyze_thermocouple_identicool_correlations.py
python analyze_thermocouple_wireless_correlations.py
python compare_thermocouple_relationships.py
python analyze_lagged_thermocouple_wireless.py
python analyze_exponential_thermal_models.py
cd ..
```

Each stage writes CSV metrics, PNG plots, and text summaries to its corresponding result folder. The comparison stage depends on the preceding pairwise analyses.

### 2. Pallet pipeline

From the repository root:

```bash
python "New folder/clean_state_space_data.py"
python "New folder/clean_monte_carlo_data.py"
python "New folder/analyze_state_space_summaries.py"
python "New folder/analyze_monte_carlo_summaries.py"
python "New folder/analyze_state_space_vs_monte_carlo.py"
```

Outputs are saved under `New folder/state_space_summary_results/`, `monte_carlo_summary_results/`, and `state_space_vs_monte_carlo_results/`.

### 3. Refresh the offline Atlas

After regenerating the pallet results:

```bash
python "pallet webpage/build_data.py"
```

The builder audits source alignment before writing `data.js` and copying downloadable source snapshots. Reload the browser page afterward. This export reads existing results; it does not rerun the analyses.

Optional browser interaction checks require Node.js, `playwright-core`, and an available Playwright Chromium installation:

```bash
node "pallet webpage/verify.cjs"
```

The checker also accepts an installed `playwright-core` module path as its first argument.

## 📈 Results at a glance

### Sensor modeling

The saved analyses report these best model R² scores:

| Relationship | 30°C | 37°C |
| --- | ---: | ---: |
| Same-instant Thermocouple vs IdentiCool | 0.434 | 0.695 |
| Same-instant Thermocouple vs Wireless | 0.042 | 0.484 |
| Lagged Thermocouple vs Wireless | 0.721 | 0.827 |

IdentiCool provides the stronger same-instant relationship in these datasets. Adding earlier wireless readings improves the reported predictive fit, consistent with delayed thermal response. These results support further validation of lagged wireless estimation; they do not establish universal sensor interchangeability.

The recursive physics model reports R² = 0.752 at 37°C and −3.681 at 30°C, indicating poor generalization for the latter condition. Detailed metrics and plots are available in the sensor result folders.

### Pallet data coverage

- **20 boxes across four layers**, with observed summaries from hour 0 to 24 in two-hour increments.
- **1,170 observed readings** forming **260 box-hour summaries**.
- **50,000 saved simulation values**, with **500 simulations per box-hour** at hours 0, 6, 12, 18, and 24.
- Source audits check readings, simulation values, summary statistics, first crossings, and coordinates used in the heat maps.

## 🧭 Interpretation & known limits

- Pallet “risk” means the percentage of simulated values **≥ 4**. It is not a validated probability of spoilage. The pallet source unit is unconfirmed, so the Atlas does not label those values as Celsius.
- Simulation percentile intervals describe simulated values, not confidence intervals for an estimated mean. Simulations centered on observed averages do not provide independent validation.
- First observed crossing refers to any available trial reaching the threshold; the box mean may still be below it.
- Box centers use source coordinates in inches. Box dimensions and pallet geometry are inferred for visualization, not verified engineering dimensions.
- Recorded exposure counts for **L2B7** and **L2B9** differ from the nominal layout and remain flagged. A bottom boundary does not establish air exposure.

## 📥 Updating sensor data

Use **Upload Data** in the dashboard for the six sensor slots: IdentiCool 1/2, Thermocouple 30C/37C, and Wireless 1/2.

- `.xlsx` uploads replace the matching source workbook immediately.
- `.xls` and `.csv` uploads are staged in `Temperature sensors data - split sheets/_pending_uploads/` and require manual conversion before analysis.
- Preserve the expected workbook layout: IdentiCool/Wireless use columns A:B for 30°C and F:G for 37°C; Thermocouple inputs use a `Time` column and four numeric probe columns. Consult the readers in the analysis scripts for exact parsing requirements.

After replacing inputs, rerun the sensor analyses to update the dashboard results.

## 🛠️ Technology & skills demonstrated

**Data engineering:** Excel ingestion, cleaning, time alignment, CSV exports, and source traceability.
**Modeling:** regression comparison, correlation metrics, lagged features, thermal response, and Monte Carlo summary analysis.
**Visualization:** Matplotlib charts, HTML presentations, interactive canvas projection, and linked data views.
**Application development:** Python HTTP services, JavaScript interfaces, offline data packaging, and automated source checks.

## 🗺️ Next steps

- Validate uploaded workbook layouts and automate staged file conversion.
- Add individual analysis reruns and configurable lag windows.
- Investigate the 30°C thermal-model divergence and expand validation datasets.
- Confirm pallet measurement units, stacking geometry, and exposure definitions.
