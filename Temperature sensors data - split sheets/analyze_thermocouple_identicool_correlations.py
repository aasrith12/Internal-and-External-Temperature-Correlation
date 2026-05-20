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
OUTPUT_DIR = BASE_DIR / "thermocouple_identicool_results"
OUTPUT_DIR.mkdir(exist_ok=True)

RANDOM_STATE = 42


GROUPS = [
    {
        "key": "30C",
        "title": "30C Thermocouple vs IdentiCool Sensor 1",
        "identicool_file": "IdentiCool Temperature Sensor 1.xlsx",
        "identicool_name": "IdentiCool Temperature Sensor 1",
        "thermocouple_file": "Thermocouple TA 30C.xlsx",
        "thermocouple_name": "Thermocouple TA 30C",
        "sensor_cols": (0, 1),
    },
    {
        "key": "37C",
        "title": "37C Thermocouple vs IdentiCool Sensor 2",
        "identicool_file": "IdentiCool Temperature Sensor 2.xlsx",
        "identicool_name": "IdentiCool Temperature Sensor 2",
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


def load_identicool(filename, label, cols):
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


def merge_by_nearest_time(left, right, tolerance_minutes=1.5):
    merged = pd.merge_asof(
        left.sort_values("minute_of_day"),
        right.sort_values("minute_of_day"),
        on="minute_of_day",
        direction="nearest",
        tolerance=tolerance_minutes,
    )
    return merged.dropna()


def load_group_data(group):
    identicool = load_identicool(
        group["identicool_file"],
        group["identicool_name"],
        group["sensor_cols"],
    )
    thermocouple = load_thermocouple(group["thermocouple_file"], group["thermocouple_name"])
    return merge_by_nearest_time(identicool, thermocouple)


def model_metrics(y_true, y_pred):
    return {
        "R2": r2_score(y_true, y_pred),
        "RMSE": math.sqrt(mean_squared_error(y_true, y_pred)),
        "MAE": mean_absolute_error(y_true, y_pred),
        "Pearson_r": pd.Series(y_true).corr(pd.Series(y_pred)),
    }


def plot_correlation(df, group):
    corr = df[[group["thermocouple_name"], group["identicool_name"]]].corr()
    fig, ax = plt.subplots(figsize=(7, 5))
    image = ax.imshow(corr, vmin=-1, vmax=1, cmap="coolwarm")
    labels = [group["thermocouple_name"], group["identicool_name"]]
    ax.set_xticks(range(2), labels, rotation=20, ha="right")
    ax.set_yticks(range(2), labels)
    ax.set_title(f"{group['title']} - Pearson Correlation")

    for row in range(2):
        for col in range(2):
            ax.text(col, row, f"{corr.iloc[row, col]:.3f}", ha="center", va="center")

    fig.colorbar(image, ax=ax, label="Pearson correlation")
    fig.tight_layout()
    path = OUTPUT_DIR / f"{group['key']}_thermocouple_identicool_correlation.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_time_series(df, group):
    fig, ax = plt.subplots(figsize=(13, 6))
    ax.plot(df["minute_of_day"], df[group["thermocouple_name"]], marker="o", label=group["thermocouple_name"])
    ax.plot(df["minute_of_day"], df[group["identicool_name"]], marker="o", label=group["identicool_name"])
    ax.set_title(f"{group['title']} - Aligned Temperature Readings")
    ax.set_xlabel("Minute of day")
    ax.set_ylabel("Temperature (C)")
    ax.legend()
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    path = OUTPUT_DIR / f"{group['key']}_thermocouple_identicool_trends.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_model_results(group, metrics_rows, predictions):
    model_names = list(predictions.keys())
    cols = 3
    rows = math.ceil(len(model_names) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(16, 9), squeeze=False)
    fig.suptitle(
        f"{group['title']} - Predicting IdentiCool Sensor from Thermocouple",
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
        ax.set_xlabel("Actual IdentiCool temperature (C)")
        ax.set_ylabel("Predicted IdentiCool temperature (C)")
        ax.grid(True, alpha=0.25)

    for ax in axes.ravel()[len(model_names) :]:
        ax.axis("off")

    fig.tight_layout(rect=(0, 0, 1, 0.95))
    path = OUTPUT_DIR / f"{group['key']}_thermocouple_identicool_model_results.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def run_group(group):
    df = load_group_data(group)
    df.to_csv(OUTPUT_DIR / f"{group['key']}_thermocouple_identicool_aligned_data.csv", index=False)

    x = df[[group["thermocouple_name"]]]
    y = df[group["identicool_name"]]
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.25,
        random_state=RANDOM_STATE,
    )

    metrics_by_model = {}
    predictions = {}
    for model_name, model in MODELS.items():
        model.fit(x_train, y_train)
        y_pred = model.predict(x_test)
        metrics_by_model[model_name] = model_metrics(y_test.to_numpy(), y_pred)
        predictions[model_name] = {"y_test": y_test.to_numpy(), "y_pred": y_pred}

    metrics_frame = pd.DataFrame.from_dict(metrics_by_model, orient="index")
    metrics_frame.index.name = "Model"
    metrics_frame.to_csv(OUTPUT_DIR / f"{group['key']}_thermocouple_identicool_model_metrics.csv")

    return {
        "group": group["title"],
        "rows": len(df),
        "best_model": metrics_frame["R2"].idxmax(),
        "best_r2": metrics_frame["R2"].max(),
        "plots": [
            plot_correlation(df, group),
            plot_time_series(df, group),
            plot_model_results(group, metrics_by_model, predictions),
        ],
        "metrics": metrics_frame,
    }


def main():
    summaries = [run_group(group) for group in GROUPS]

    with (OUTPUT_DIR / "summary.txt").open("w", encoding="utf-8") as handle:
        for summary in summaries:
            handle.write(f"{summary['group']}\n")
            handle.write(f"Aligned rows: {summary['rows']}\n")
            handle.write(f"Best model by R2: {summary['best_model']} ({summary['best_r2']:.4f})\n")
            handle.write(summary["metrics"].round(4).to_string())
            handle.write("\n\n")

    for summary in summaries:
        print(f"{summary['group']}: {summary['rows']} aligned rows")
        print(f"  Best model: {summary['best_model']} (R2={summary['best_r2']:.4f})")
        for plot in summary["plots"]:
            print(f"  Wrote {plot.name}")


if __name__ == "__main__":
    main()
