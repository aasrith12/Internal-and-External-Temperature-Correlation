# Internal and External Temperature Correlation

This repository contains temperature monitoring workbooks, split sensor workbooks, Python analysis scripts, generated plots, and model result summaries for comparing internal and external temperature sensors.

## Project structure

```text
.
├── Temperature Monitoring Data.xlsx
├── Temperature sensors data.xlsx
├── Temperature Monitoring Data - split sheets/
├── Temperature sensors data - split sheets/
│   ├── analyze_sensor_correlations.py
│   ├── analyze_thermocouple_wireless_correlations.py
│   ├── analyze_thermocouple_identicool_correlations.py
│   ├── compare_thermocouple_relationships.py
│   ├── correlation_model_results/
│   ├── thermocouple_wireless_results/
│   ├── thermocouple_identicool_results/
│   └── thermocouple_relationship_comparison/
```

## Requirements

Use Python 3.10 or newer.

Install the required packages:

```bash
pip install pandas openpyxl matplotlib scikit-learn numpy
```

## Running the scripts

Open a terminal in the repository root, then move into the sensor folder:

```bash
cd "Temperature sensors data - split sheets"
```

Run the full three-sensor correlation analysis:

```bash
python analyze_sensor_correlations.py
```

This compares:

- IdentiCool Temperature Sensor 1, Thermocouple TA 30C, Wireless Temperature Sensor 1
- IdentiCool Temperature Sensor 2, Thermocouple TA 37C, Wireless Temperature Sensor 2

Results are written to:

```text
correlation_model_results/
```

Run thermocouple vs wireless only:

```bash
python analyze_thermocouple_wireless_correlations.py
```

Results are written to:

```text
thermocouple_wireless_results/
```

Run thermocouple vs IdentiCool only:

```bash
python analyze_thermocouple_identicool_correlations.py
```

Results are written to:

```text
thermocouple_identicool_results/
```

Compare which relationship is more reliable:

```bash
python compare_thermocouple_relationships.py
```

Results are written to:

```text
thermocouple_relationship_comparison/
```

## Updating the datasets

To update the analysis with new data:

1. Replace the Excel files in `Temperature sensors data - split sheets/` with updated files using the same filenames:
   - `IdentiCool Temperature Sensor 1.xlsx`
   - `IdentiCool Temperature Sensor 2.xlsx`
   - `Thermocouple TA 30C.xlsx`
   - `Thermocouple TA 37C.xlsx`
   - `Wireless Temperature Sensor 1.xlsx`
   - `Wireless Temperature Sensor 2.xlsx`

2. Keep the same sheet format:
   - IdentiCool and wireless files should have 30C data in columns A:B and 37C data in columns F:G.
   - Thermocouple files should have time in the `Time` column and numeric thermocouple readings in the four probe columns.

3. Rerun the scripts from `Temperature sensors data - split sheets/`.

Each script overwrites its own result folder with updated CSV summaries and PNG plots.

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
Temperature sensors data - split sheets/thermocouple_relationship_comparison/best_model_rmse_comparison.png
```

## Current conclusion

Based on the generated model results, Thermocouple vs IdentiCool is more reliable than Thermocouple vs Wireless for both 30C and 37C.

Best relationship by temperature:

- 30C: Thermocouple vs IdentiCool using Ridge Regression.
- 37C: Thermocouple vs IdentiCool using SVR.
