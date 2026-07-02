from pathlib import Path
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import minimize, minimize_scalar
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "exponential_thermal_model_results"
OUTPUT_DIR.mkdir(exist_ok=True)


GROUPS = [
    {
        "key": "30C",
        "title": "30C Wireless Sensor 1 to Thermocouple",
        "wireless_file": "Wireless Temperature Sensor 1.xlsx",
        "wireless_name": "Wireless Temperature Sensor 1",
        "thermocouple_file": "Thermocouple TA 30C.xlsx",
        "thermocouple_name": "Thermocouple TA 30C",
        "sensor_cols": (0, 1),
    },
    {
        "key": "37C",
        "title": "37C Wireless Sensor 2 to Thermocouple",
        "wireless_file": "Wireless Temperature Sensor 2.xlsx",
        "wireless_name": "Wireless Temperature Sensor 2",
        "thermocouple_file": "Thermocouple TA 37C.xlsx",
        "thermocouple_name": "Thermocouple TA 37C",
        "sensor_cols": (5, 6),
    },
]


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


def align_environment_to_core(core_df, ambient_df, ambient_name):
    ambient = ambient_df.rename(columns={ambient_name: "ambient_temperature"})
    core = core_df.rename(columns={core_df.columns[1]: "core_temperature"})
    aligned = pd.merge_asof(
        core.sort_values("minute_of_day"),
        ambient.sort_values("minute_of_day"),
        on="minute_of_day",
        direction="backward",
        tolerance=12,
    )
    return aligned.dropna().sort_values("minute_of_day")


def load_group_data(group):
    ambient = load_wireless(group["wireless_file"], group["wireless_name"], group["sensor_cols"])
    core = load_thermocouple(group["thermocouple_file"], group["thermocouple_name"])
    return align_environment_to_core(core, ambient, group["wireless_name"])


def newton_step(core_previous, ambient_previous, dt_minutes, k_per_minute, ambient_bias=0.0):
    effective_ambient = ambient_previous + ambient_bias
    return effective_ambient + (core_previous - effective_ambient) * np.exp(-k_per_minute * dt_minutes)


def one_step_predictions(df, k_per_minute, ambient_bias=0.0):
    dt = df["minute_of_day"].diff().to_numpy()[1:]
    previous_core = df["core_temperature"].to_numpy()[:-1]
    previous_ambient = df["ambient_temperature"].to_numpy()[:-1]
    actual = df["core_temperature"].to_numpy()[1:]
    predicted = newton_step(previous_core, previous_ambient, dt, k_per_minute, ambient_bias)
    return actual, predicted


def recursive_predictions(df, k_per_minute, ambient_bias=0.0):
    times = df["minute_of_day"].to_numpy()
    ambient = df["ambient_temperature"].to_numpy()
    actual = df["core_temperature"].to_numpy()
    predicted = np.empty_like(actual, dtype=float)
    predicted[0] = actual[0]

    for index in range(1, len(actual)):
        dt = times[index] - times[index - 1]
        predicted[index] = newton_step(
            predicted[index - 1],
            ambient[index - 1],
            dt,
            k_per_minute,
            ambient_bias,
        )

    return actual[1:], predicted[1:]


def metrics(y_true, y_pred):
    return {
        "R2": r2_score(y_true, y_pred),
        "RMSE": math.sqrt(mean_squared_error(y_true, y_pred)),
        "MAE": mean_absolute_error(y_true, y_pred),
        "Pearson_r": pd.Series(y_true).corr(pd.Series(y_pred)),
    }


def fit_pure_newton(train_df):
    def objective(k):
        actual, predicted = one_step_predictions(train_df, k)
        return mean_squared_error(actual, predicted)

    result = minimize_scalar(objective, bounds=(0.0001, 1.0), method="bounded")
    return {"k": result.x, "ambient_bias": 0.0}


def fit_biased_newton(train_df):
    def objective(params):
        k, ambient_bias = params
        actual, predicted = one_step_predictions(train_df, k, ambient_bias)
        return mean_squared_error(actual, predicted)

    result = minimize(
        objective,
        x0=np.array([0.05, 0.0]),
        bounds=[(0.0001, 1.0), (-20.0, 20.0)],
        method="L-BFGS-B",
    )
    return {"k": result.x[0], "ambient_bias": result.x[1]}


def fit_models(train_df):
    return {
        "Pure Newton Cooling": fit_pure_newton(train_df),
        "Newton Cooling + Ambient Offset": fit_biased_newton(train_df),
    }


def plot_model_fit(group, test_df, fitted_models, recursive_results):
    fig, axes = plt.subplots(len(fitted_models), 1, figsize=(13, 9), sharex=True)
    if len(fitted_models) == 1:
        axes = [axes]

    for ax, (model_name, params) in zip(axes, fitted_models.items()):
        actual, predicted = recursive_results[model_name]
        plot_times = test_df["minute_of_day"].to_numpy()[1:]
        metric_values = metrics(actual, predicted)
        tau = 1 / params["k"]

        ax.plot(plot_times, actual, label="Actual thermocouple core", linewidth=2)
        ax.plot(plot_times, predicted, label="Predicted core", linewidth=2)
        ax.plot(
            test_df["minute_of_day"],
            test_df["ambient_temperature"],
            label="Wireless ambient",
            alpha=0.45,
            linestyle="--",
        )
        annotation = (
            f"{model_name}\n"
            f"dT/dt = k(Tenv - Tcore)\n"
            f"k = {params['k']:.4f} per min\n"
            f"thermal time constant = {tau:.1f} min\n"
            f"ambient offset = {params['ambient_bias']:.2f} C\n"
            f"R2 = {metric_values['R2']:.3f}\n"
            f"RMSE = {metric_values['RMSE']:.3f} C\n"
            f"Pearson r = {metric_values['Pearson_r']:.3f}"
        )
        ax.text(
            0.02,
            0.97,
            annotation,
            transform=ax.transAxes,
            va="top",
            ha="left",
            bbox={"facecolor": "white", "alpha": 0.86, "edgecolor": "#777777"},
        )
        ax.set_title(model_name)
        ax.set_ylabel("Temperature (C)")
        ax.legend(loc="lower right")
        ax.grid(True, alpha=0.25)

    axes[-1].set_xlabel("Minute of day")
    fig.suptitle(f"{group['title']} - Exponential Thermal Model Fit", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    path = OUTPUT_DIR / f"{group['key']}_exponential_thermal_fit.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_actual_vs_predicted(group, fitted_models, recursive_results):
    fig, axes = plt.subplots(1, len(fitted_models), figsize=(14, 6), squeeze=False)

    for ax, (model_name, params) in zip(axes.ravel(), fitted_models.items()):
        actual, predicted = recursive_results[model_name]
        metric_values = metrics(actual, predicted)
        ax.scatter(actual, predicted, s=34, alpha=0.8, edgecolor="white", linewidth=0.5)
        low = min(actual.min(), predicted.min())
        high = max(actual.max(), predicted.max())
        ax.plot([low, high], [low, high], color="black", linewidth=1.2, linestyle="--")
        ax.set_title(model_name)
        ax.set_xlabel("Actual thermocouple temperature (C)")
        ax.set_ylabel("Predicted thermocouple temperature (C)")
        ax.grid(True, alpha=0.25)
        ax.text(
            0.04,
            0.96,
            (
                f"k = {params['k']:.4f} per min\n"
                f"tau = {1 / params['k']:.1f} min\n"
                f"R2 = {metric_values['R2']:.3f}\n"
                f"RMSE = {metric_values['RMSE']:.3f} C\n"
                f"MAE = {metric_values['MAE']:.3f} C"
            ),
            transform=ax.transAxes,
            va="top",
            ha="left",
            bbox={"facecolor": "white", "alpha": 0.86, "edgecolor": "#777777"},
        )

    fig.suptitle(f"{group['title']} - Actual vs Predicted Core Temperature", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    path = OUTPUT_DIR / f"{group['key']}_exponential_actual_vs_predicted.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_temperature_derivative(group, df, fitted_models):
    dt = df["minute_of_day"].diff().to_numpy()[1:]
    d_core_dt = np.diff(df["core_temperature"].to_numpy()) / dt
    delta_temp = df["ambient_temperature"].to_numpy()[:-1] - df["core_temperature"].to_numpy()[:-1]

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(delta_temp, d_core_dt, s=25, alpha=0.7, label="Observed dTcore/dt")
    x_line = np.linspace(delta_temp.min(), delta_temp.max(), 100)
    for model_name, params in fitted_models.items():
        ax.plot(x_line, params["k"] * (x_line + params["ambient_bias"]), label=model_name)

    ax.set_title(f"{group['title']} - Newton Cooling Relationship")
    ax.set_xlabel("Tenv - Tcore (C)")
    ax.set_ylabel("dTcore/dt (C per minute)")
    ax.legend()
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    path = OUTPUT_DIR / f"{group['key']}_newton_derivative_relationship.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def run_group(group):
    df = load_group_data(group)
    split_index = int(len(df) * 0.75)
    train_df = df.iloc[:split_index].copy()
    test_df = df.iloc[split_index:].copy()

    fitted_models = fit_models(train_df)
    rows = []
    recursive_results = {}
    one_step_results = {}

    for model_name, params in fitted_models.items():
        one_actual, one_predicted = one_step_predictions(test_df, params["k"], params["ambient_bias"])
        rec_actual, rec_predicted = recursive_predictions(test_df, params["k"], params["ambient_bias"])
        one_step_results[model_name] = (one_actual, one_predicted)
        recursive_results[model_name] = (rec_actual, rec_predicted)

        one_metrics = metrics(one_actual, one_predicted)
        rec_metrics = metrics(rec_actual, rec_predicted)
        rows.append(
            {
                "Model": model_name,
                "k_per_minute": params["k"],
                "thermal_time_constant_minutes": 1 / params["k"],
                "ambient_offset_C": params["ambient_bias"],
                "OneStep_R2": one_metrics["R2"],
                "OneStep_RMSE": one_metrics["RMSE"],
                "OneStep_MAE": one_metrics["MAE"],
                "OneStep_Pearson_r": one_metrics["Pearson_r"],
                "Recursive_R2": rec_metrics["R2"],
                "Recursive_RMSE": rec_metrics["RMSE"],
                "Recursive_MAE": rec_metrics["MAE"],
                "Recursive_Pearson_r": rec_metrics["Pearson_r"],
            }
        )

    metrics_frame = pd.DataFrame(rows)
    metrics_frame.to_csv(OUTPUT_DIR / f"{group['key']}_exponential_thermal_metrics.csv", index=False)
    df.to_csv(OUTPUT_DIR / f"{group['key']}_exponential_aligned_data.csv", index=False)

    best_row = metrics_frame.sort_values("Recursive_R2", ascending=False).iloc[0]
    plots = [
        plot_model_fit(group, test_df, fitted_models, recursive_results),
        plot_actual_vs_predicted(group, fitted_models, recursive_results),
        plot_temperature_derivative(group, df, fitted_models),
    ]
    return {
        "group": group["title"],
        "rows": len(df),
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "best_model": best_row["Model"],
        "best_recursive_r2": best_row["Recursive_R2"],
        "metrics": metrics_frame,
        "plots": plots,
    }


def main():
    summaries = [run_group(group) for group in GROUPS]

    with (OUTPUT_DIR / "summary.txt").open("w", encoding="utf-8") as handle:
        handle.write("Exponential thermal model setup\n")
        handle.write("Scientific model: dTcore/dt = k(Tenv - Tcore)\n")
        handle.write("Ambient/external input: wireless temperature sensor.\n")
        handle.write("Core/internal target: thermocouple temperature.\n")
        handle.write("Evaluation reports recursive test simulation as the main score.\n\n")

        for summary in summaries:
            handle.write(f"{summary['group']}\n")
            handle.write(f"Rows: {summary['rows']} total, {summary['train_rows']} train, {summary['test_rows']} test\n")
            handle.write(
                f"Best model by recursive R2: {summary['best_model']} "
                f"({summary['best_recursive_r2']:.4f})\n"
            )
            handle.write(summary["metrics"].round(4).to_string(index=False))
            handle.write("\n\n")

    for summary in summaries:
        print(f"{summary['group']}: {summary['rows']} aligned rows")
        print(f"  Best model: {summary['best_model']} (Recursive R2={summary['best_recursive_r2']:.4f})")
        for plot in summary["plots"]:
            print(f"  Wrote {plot.name}")


if __name__ == "__main__":
    main()
