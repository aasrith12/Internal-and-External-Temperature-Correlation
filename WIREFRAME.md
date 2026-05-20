# Temperature Correlation Dashboard Wireframe

This wireframe describes a simple dashboard for viewing the temperature sensor datasets, ML model results, and reliability comparison outputs.

## Main dashboard

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Internal and External Temperature Correlation                                │
│ [Dataset Status] [Run Analysis] [Export Results]                            │
├──────────────────────────────────────────────────────────────────────────────┤
│ Summary Cards                                                                │
│ ┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐ │
│ │ Best 30C Match       │ │ Best 37C Match       │ │ Overall Reliable     │ │
│ │ Thermocouple vs      │ │ Thermocouple vs      │ │ Thermocouple vs      │ │
│ │ IdentiCool           │ │ IdentiCool           │ │ IdentiCool           │ │
│ │ R2: 0.4342           │ │ R2: 0.6952           │ │ Avg R2: 0.5647       │ │
│ └──────────────────────┘ └──────────────────────┘ └──────────────────────┘ │
├──────────────────────────────────────────────────────────────────────────────┤
│ Temperature Group Tabs                                                       │
│ [30C] [37C] [All Comparisons]                                                │
├──────────────────────────────────────────────────────────────────────────────┤
│ Selected Group: 30C                                                          │
│                                                                              │
│ ┌────────────────────────────────────┐ ┌───────────────────────────────────┐ │
│ │ Aligned Temperature Trends         │ │ Correlation Matrix                │ │
│ │                                    │ │                                   │ │
│ │ [line chart: thermocouple,         │ │ [heatmap: sensor correlation]     │ │
│ │  IdentiCool, wireless]             │ │                                   │ │
│ └────────────────────────────────────┘ └───────────────────────────────────┘ │
│                                                                              │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ ML Model Correlation Results                                             │ │
│ │ [scatter plots per model with R2, RMSE, MAE, Pearson r annotations]       │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Reliability comparison view

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Relationship Reliability Comparison                                          │
├──────────────────────────────────────────────────────────────────────────────┤
│ Filters                                                                      │
│ Temperature: [30C ▼] [37C ▼] [Both ▼]     Metric: [R2 ▼] [Pearson ▼] [RMSE ▼]│
├──────────────────────────────────────────────────────────────────────────────┤
│ Best Model Comparison                                                        │
│ ┌────────────────────────────────────┐ ┌───────────────────────────────────┐ │
│ │ Thermocouple vs IdentiCool         │ │ Thermocouple vs Wireless          │ │
│ │ Best Model: Ridge / SVR            │ │ Best Model: Ridge / SVR           │ │
│ │ R2, Pearson r, RMSE, MAE           │ │ R2, Pearson r, RMSE, MAE          │ │
│ └────────────────────────────────────┘ └───────────────────────────────────┘ │
│                                                                              │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ Comparison Charts                                                        │ │
│ │ [bar chart: R2] [bar chart: Pearson r] [bar chart: RMSE]                 │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ Final Decision                                                           │ │
│ │ Thermocouple vs IdentiCool is the stronger relationship for both groups. │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Dataset management view

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Dataset Management                                                           │
├──────────────────────────────────────────────────────────────────────────────┤
│ Required Files                                                               │
│ ┌──────────────────────────────────────┐ ┌────────────┐ ┌────────────────┐ │
│ │ File                                 │ │ Status     │ │ Last Updated   │ │
│ ├──────────────────────────────────────┤ ├────────────┤ ├────────────────┤ │
│ │ IdentiCool Temperature Sensor 1.xlsx │ │ Found      │ │ date/time      │ │
│ │ IdentiCool Temperature Sensor 2.xlsx │ │ Found      │ │ date/time      │ │
│ │ Thermocouple TA 30C.xlsx             │ │ Found      │ │ date/time      │ │
│ │ Thermocouple TA 37C.xlsx             │ │ Found      │ │ date/time      │ │
│ │ Wireless Temperature Sensor 1.xlsx   │ │ Found      │ │ date/time      │ │
│ │ Wireless Temperature Sensor 2.xlsx   │ │ Found      │ │ date/time      │ │
│ └──────────────────────────────────────┘ └────────────┘ └────────────────┘ │
├──────────────────────────────────────────────────────────────────────────────┤
│ Actions                                                                      │
│ [Validate Files] [Run All Scripts] [Open Results Folder]                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Result folders

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Results Explorer                                                             │
├──────────────────────────────────────────────────────────────────────────────┤
│ [correlation_model_results]                                                  │
│   - Full three-sensor model plots and metrics                                │
│                                                                              │
│ [thermocouple_wireless_results]                                              │
│   - Thermocouple vs wireless plots and metrics                               │
│                                                                              │
│ [thermocouple_identicool_results]                                            │
│   - Thermocouple vs IdentiCool plots and metrics                             │
│                                                                              │
│ [thermocouple_relationship_comparison]                                       │
│   - Best relationship comparison plots and summary files                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Suggested navigation

```text
Dashboard
├── Overview
├── 30C Analysis
├── 37C Analysis
├── Relationship Comparison
├── Dataset Management
└── Results Explorer
```

## Primary user flow

1. Open dashboard.
2. Check dataset status.
3. Run all analysis scripts.
4. View 30C and 37C model plots.
5. Open relationship comparison.
6. Use the final reliability result for reporting.
