from pathlib import Path
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "lagged_thermocouple_wireless_results"
OUTPUT_DIR.mkdir(exist_ok=True)

RANDOM_STATE = 42
LAGS_MINUTES = [10, 20, 30]


GROUPS = [
    {
        "key": "30C",
        "title": "30C Lagged Wireless Sensor 1 to Thermocouple",
        "wireless_file": "Wireless Temperature Sensor 1.xlsx",
        "wireless_name": "Wireless Temperature Sensor 1",
        "thermocouple_file": "Thermocouple TA 30C.xlsx",
        "thermocouple_name": "Thermocouple TA 30C",
        "sensor_cols": (0, 1),
    },
    {
        "key": "37C",
        "title": "37C Lagged Wireless Sensor 2 to Thermocouple",
        "wireless_file": "Wireless Temperature Sensor 2.xlsx",
        "wireless_name": "Wireless Temperature Sensor 2",
        "thermocouple_file": "Thermocouple TA 37C.xlsx",
        "thermocouple_name": "Thermocouple TA 37C",
        "sensor_cols": (5, 6),
    },
]


MODELS = {
    "Linear Regression": LinearRegression(),
    "Ridge Regression": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
    "Random Forest": RandomForestRegressor(
        n_estimators=300,
        min_samples_leaf=3,
        random_state=RANDOM_STATE,
    ),
    "Gradient Boosting": GradientBoostingRegressor(random_state=RANDOM_STATE),
    "KNN Regression": make_pipeline(StandardScaler(), KNeighborsRegressor(n_neighbors=5)),
    "SVR": make_pipeline(StandardScaler(), SVR(kernel="rbf", C=10.0, epsilon=0.1)),
}


def time_to_minutes(value):
    if pd.isna(value):
        return np.nan
    if isinstance(value, pd.Timestamp):
        return value.hour * 60 + value.minute + value.second / 60
    if isinstance(value, pd.Timedelta):
        return value.total_seconds() / 60
    if hasattr(value, "hour") and hasattr(value, "minute"):
        return value.hour * 60 + value.minute + getattr(value, "second", 0) / 60

    text = str(value).strip()
    if not text:
        return np.nan
    parts = text.split(":")
    try:
        if len(parts) == 2:
            hours, minutes = parts
            seconds = 0
        elif len(parts) == 3:
            hours, minutes, seconds = parts
        else:
            return np.nan
        return int(hours) * 60 + int(minutes) + int(seconds) / 60
    except ValueError:
        return np.nan


def load_wireless(filename, label, cols):
    raw = pd.read_excel(BASE_DIR / filename, header=None)
    time_col, temp_col = cols
    data = raw.iloc[6:, [time_col, temp_col]].copy()
    data.columns = ["minute_of_day", label]
    data["minute_of_day"] = data["minute_of_day"].apply(time_to_minutes)
    data[label] = pd.to_numeric(data[label], errors="coerce")
    return data.dropna().sort_values("minute_of_day")


def load_thermocouple(filename, label):
    raw = pd.read_excel(BASE_DIR / filename, header=None)
    data = raw.iloc[1:].copy()
    data["minute_of_day"] = data.iloc[:, 2].apply(time_to_minutes)
    probe_columns = [3, 5, 7, 9]
    probes = data.iloc[:, probe_columns].apply(pd.to_numeric, errors="coerce")
    data[label] = probes.mean(axis=1)
    return data[["minute_of_day", label]].dropna().sort_values("minute_of_day")


def nearest_lagged_feature(core_df, ambient_df, ambient_name, lag_minutes):
    feature_name = f"{ambient_name} lag {lag_minutes}min"
    left = core_df[["minute_of_day"]].copy()
    left["lookup_minute"] = left["minute_of_day"] - lag_minutes

    right = ambient_df[["minute_of_day", ambient_name]].copy()
    right = right.rename(columns={"minute_of_day": "lookup_minute", ambient_name: feature_name})

    matched = pd.merge_asof(
        left.sort_values("lookup_minute"),
        right.sort_values("lookup_minute"),
        on="lookup_minute",
        direction="nearest",
        tolerance=1.5,
    )
    return matched.sort_values("minute_of_day")[["minute_of_day", feature_name]]


def load_lagged_group_data(group):
    ambient = load_wireless(group["wireless_file"], group["wireless_name"], group["sensor_cols"])
    core = load_thermocouple(group["thermocouple_file"], group["thermocouple_name"])
    core = core.sort_values("minute_of_day")

    merged = core.copy()
    for lag in LAGS_MINUTES:
        lagged = nearest_lagged_feature(core, ambient, group["wireless_name"], lag)
        merged = merged.merge(lagged, on="minute_of_day", how="left")

    return merged.dropna().sort_values("minute_of_day")


def model_metrics(y_true, y_pred):
    return {
        "R2": r2_score(y_true, y_pred),
        "RMSE": math.sqrt(mean_squared_error(y_true, y_pred)),
        "MAE": mean_absolute_error(y_true, y_pred),
        "Pearson_r": pd.Series(y_true).corr(pd.Series(y_pred)),
    }


def plot_lag_correlation(df, group, feature_cols):
    cols = [group["thermocouple_name"], *feature_cols]
    corr = df[cols].corr()

    fig, ax = plt.subplots(figsize=(9, 7))
    image = ax.imshow(corr, vmin=-1, vmax=1, cmap="coolwarm")
    ax.set_xticks(range(len(cols)), cols, rotation=25, ha="right")
    ax.set_yticks(range(len(cols)), cols)
    ax.set_title(f"{group['title']} - Lagged Pearson Correlation")

    for row in range(len(cols)):
        for col in range(len(cols)):
            ax.text(col, row, f"{corr.iloc[row, col]:.3f}", ha="center", va="center")

    fig.colorbar(image, ax=ax, label="Pearson correlation")
    fig.tight_layout()
    path = OUTPUT_DIR / f"{group['key']}_lagged_correlation_matrix.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_lagged_trends(df, group, feature_cols):
    fig, ax = plt.subplots(figsize=(13, 6))
    ax.plot(df["minute_of_day"], df[group["thermocouple_name"]], marker="o", label=group["thermocouple_name"])
    for feature in feature_cols:
        ax.plot(df["minute_of_day"], df[feature], marker="o", alpha=0.75, label=feature)

    ax.set_title(f"{group['title']} - Core Response with Lagged Ambient Inputs")
    ax.set_xlabel("Core reading minute of day")
    ax.set_ylabel("Temperature (C)")
    ax.legend()
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    path = OUTPUT_DIR / f"{group['key']}_lagged_temperature_trends.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_model_results(group, metrics_rows, predictions):
    model_names = list(predictions.keys())
    cols = 3
    rows = math.ceil(len(model_names) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(16, 9), squeeze=False)
    fig.suptitle(
        f"{group['title']} - Predicting Thermocouple from Wireless(t-10, t-20, t-30)",
        fontsize=14,
    )

    for ax, model_name in zip(axes.ravel(), model_names):
        pred = predictions[model_name]
        y_test = pred["y_test"]
        y_pred = pred["y_pred"]
        ax.scatter(y_test, y_pred, s=34, alpha=0.8, edgecolor="white", linewidth=0.5)

        low = min(y_test.min(), y_pred.min())
        high = max(y_test.max(), y_pred.max())
        ax.plot([low, high], [low, high], color="black", linewidth=1.2, linestyle="--")

        metrics = metrics_rows[model_name]
        annotation = (
            f"{model_name}\n"
            f"R2 = {metrics['R2']:.3f}\n"
            f"RMSE = {metrics['RMSE']:.3f} C\n"
            f"MAE = {metrics['MAE']:.3f} C\n"
            f"Pearson r = {metrics['Pearson_r']:.3f}"
        )
        ax.text(
            0.04,
            0.96,
            annotation,
            transform=ax.transAxes,
            va="top",
            ha="left",
            bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "#888888"},
        )
        ax.set_title(model_name)
        ax.set_xlabel("Actual thermocouple temperature (C)")
        ax.set_ylabel("Predicted thermocouple temperature (C)")
        ax.grid(True, alpha=0.25)

    for ax in axes.ravel()[len(model_names) :]:
        ax.axis("off")

    fig.tight_layout(rect=(0, 0, 1, 0.95))
    path = OUTPUT_DIR / f"{group['key']}_lagged_model_results.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_lag_importance(group, linear_model, feature_cols):
    coefficients = linear_model.coef_
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(feature_cols, coefficients)
    ax.axhline(0, color="black", linewidth=1)
    ax.set_title(f"{group['title']} - Linear Lag Coefficients")
    ax.set_xlabel("Lagged wireless feature")
    ax.set_ylabel("Coefficient")
    ax.tick_params(axis="x", rotation=20)
    ax.grid(axis="y", alpha=0.25)
    ax.bar_label(bars, fmt="%.3f", padding=3)
    fig.tight_layout()
    path = OUTPUT_DIR / f"{group['key']}_linear_lag_coefficients.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def run_group(group):
    df = load_lagged_group_data(group)
    feature_cols = [f"{group['wireless_name']} lag {lag}min" for lag in LAGS_MINUTES]
    df.to_csv(OUTPUT_DIR / f"{group['key']}_lagged_aligned_data.csv", index=False)

    x = df[feature_cols]
    y = df[group["thermocouple_name"]]
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.25,
        random_state=RANDOM_STATE,
    )

    metrics_by_model = {}
    predictions = {}
    fitted_linear = None
    for model_name, model in MODELS.items():
        model.fit(x_train, y_train)
        y_pred = model.predict(x_test)
        metrics_by_model[model_name] = model_metrics(y_test.to_numpy(), y_pred)
        predictions[model_name] = {"y_test": y_test.to_numpy(), "y_pred": y_pred}
        if model_name == "Linear Regression":
            fitted_linear = model

    metrics_frame = pd.DataFrame.from_dict(metrics_by_model, orient="index")
    metrics_frame.index.name = "Model"
    metrics_frame.to_csv(OUTPUT_DIR / f"{group['key']}_lagged_model_metrics.csv")

    return {
        "group": group["title"],
        "rows": len(df),
        "best_model": metrics_frame["R2"].idxmax(),
        "best_r2": metrics_frame["R2"].max(),
        "feature_cols": feature_cols,
        "plots": [
            plot_lag_correlation(df, group, feature_cols),
            plot_lagged_trends(df, group, feature_cols),
            plot_model_results(group, metrics_by_model, predictions),
            plot_lag_importance(group, fitted_linear, feature_cols),
        ],
        "metrics": metrics_frame,
    }


def main():
    summaries = [run_group(group) for group in GROUPS]

    with (OUTPUT_DIR / "summary.txt").open("w", encoding="utf-8") as handle:
        handle.write("Lagged regression setup\n")
        handle.write("Ambient/external input: wireless sensor at t-10, t-20, and t-30 minutes.\n")
        handle.write("Core/internal target: thermocouple temperature at time t.\n\n")
        for summary in summaries:
            handle.write(f"{summary['group']}\n")
            handle.write(f"Aligned lagged rows: {summary['rows']}\n")
            handle.write(f"Features: {', '.join(summary['feature_cols'])}\n")
            handle.write(f"Best model by R2: {summary['best_model']} ({summary['best_r2']:.4f})\n")
            handle.write(summary["metrics"].round(4).to_string())
            handle.write("\n\n")

    for summary in summaries:
        print(f"{summary['group']}: {summary['rows']} aligned lagged rows")
        print(f"  Best model: {summary['best_model']} (R2={summary['best_r2']:.4f})")
        for plot in summary["plots"]:
            print(f"  Wrote {plot.name}")


if __name__ == "__main__":
    main()
