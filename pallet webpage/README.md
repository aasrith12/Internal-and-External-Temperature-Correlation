# Pallet Atlas

Open `index.html` directly in a modern browser. The webpage runs offline; no installation or server is required.

## Explore

- Drag the pallet to rotate through 360 degrees; scroll to zoom.
- Click a box to see its report beside the visualization.
- Separate layers or filter a layer to reach hidden boxes. Box buttons provide another way to select any position.
- Change the selected hour to compare observed means and simulated threshold exceedance over time.
- Reset the camera to restore the starting view.
- Open **Data & alignment**, or use the report's **View this box’s data & alignment** link. The selected box and hour carry between pages. Inspect chart inputs, individual trials, all 500 saved simulations at an hour, top-down layouts, and downloadable source snapshots.

## Alignment audit

The audit verified 1,170 observed readings against the state-space workbook and 50,000 saved simulation values against the four Monte Carlo workbooks. It recalculated the 260 observed and 100 simulated box-hour summaries, checked first-trial crossing times, and matched geometry to the coordinates used by the heat maps.

Two recorded counts differ from the nominal packed layout: **L2B7 records 1 versus 2 outer vertical sides; L2B9 records 2 versus 1 outer vertical side**. Counts are retained and flagged, not overwritten. The actual stacking plan and source exposure definition need confirmation. Bottom-layer counts match only when the bottom boundary is included; contact with the pallet is not confirmed air exposure.

The inferred geometry uses nominal 23.5 × 16 inch footprints and 10 inch heights. A 1-inch boundary tolerance ignores the 47-versus-48-inch row offset when counting full outer sides. Small visible rendering gaps and layer separation do not create additional exposure. The 3D renderer and top-down diagrams use the same exported dimensions and source centers.

## Data and interpretation

The embedded `data.js` contains the existing results for 20 boxes, 260 observed box-hour summaries, and 100 Monte Carlo box-hour summaries (500 simulations each). Observations span 0–24 hours in two-hour increments; simulation summaries are available at hours 0, 6, 12, 18, and 24.

Box centers come from the source coordinates in inches. Layer 1 is highest (z=35); Layer 4 is lowest (z=5). Box dimensions, gaps, and wooden pallet geometry are inferred for presentation, not a verified engineering drawing.

Reported risk is the percentage of simulations with value >= 4. It is not a validated probability of spoilage. The source summaries do not establish the measurement unit, so values are shown without a Celsius claim. First observed crossing means any available trial crossed the threshold, not necessarily the box mean. Simulation percentile intervals describe simulated values, not confidence intervals for the mean. Simulations centered on observed averages are not independent validation.

## Refresh after rerunning the analyses

From the project root, run:

```powershell
python "pallet webpage/build_data.py"
```

Then reload the page. The builder reads the workbooks and existing CSVs in `New folder`; it does not rerun or modify the analyses. Refreshing requires Python with `openpyxl` installed. Checks must pass before a new data snapshot is written. Original source files remain unchanged.

## Files

- `index.html`, `styles.css`, `app.js`: interface and interactive 3D projection.
- `data.js`: offline dataset snapshot.
- `build_data.py`, `audit_data.py`: reproducible export and read-only source checks (uses `openpyxl`).
- `analysis-data.html`, `analysis-data.css`, `analysis-data.js`: source data, sample tables, geometry review and downloads.
- `sources/`: exact source workbook, CSV and plot copies with SHA-256 fingerprints in `data.js`.
- `preview.png`: desktop preview.
- `verify.cjs`: optional browser interaction checks; run with Node and an installed `playwright-core` module (or pass its absolute module path as the first argument).

The visualization projects 3D box geometry onto a canvas and uses the displayed faces for selection. It has no external JavaScript, font, or network dependencies.
