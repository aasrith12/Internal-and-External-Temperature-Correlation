from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "thermocouple_relationship_comparison"
OUTPUT_DIR.mkdir(exist_ok=True)


COMPARISONS = [
    {
        "temperature": "30C",
        "relationship": "Thermocouple vs IdentiCool",
        "metrics_file": BASE_DIR
        / "thermocouple_identicool_results"
        / "30C_thermocouple_identicool_model_metrics.csv",
    },
    {
        "temperature": "30C",
        "relationship": "Thermocouple vs Wireless",
        "metrics_file": BASE_DIR
        / "thermocouple_wireless_results"
        / "30C_thermocouple_wireless_model_metrics.csv",
    },
    {
        "temperature": "37C",
        "relationship": "Thermocouple vs IdentiCool",
        "metrics_file": BASE_DIR
        / "thermocouple_identicool_results"
        / "37C_thermocouple_identicool_model_metrics.csv",
    },
    {
        "temperature": "37C",
        "relationship": "Thermocouple vs Wireless",
        "metrics_file": BASE_DIR
        / "thermocouple_wireless_results"
        / "37C_thermocouple_wireless_model_metrics.csv",
    },
]


def load_metrics():
    rows = []
    for item in COMPARISONS:
        metrics = pd.read_csv(item["metrics_file"])
        for _, row in metrics.iterrows():
            rows.append(
                {
                    "Temperature": item["temperature"],
                    "Relationship": item["relationship"],
                    "Model": row["Model"],
                    "R2": row["R2"],
                    "RMSE": row["RMSE"],
                    "MAE": row["MAE"],
                    "Pearson_r": row["Pearson_r"],
                }
            )
    return pd.DataFrame(rows)


def best_by_relationship(metrics):
    ranked = metrics.sort_values(
        ["Temperature", "Relationship", "R2", "Pearson_r", "RMSE"],
        ascending=[True, True, False, False, True],
    )
    return ranked.groupby(["Temperature", "Relationship"], as_index=False).head(1)


def winners_by_temperature(best_rows):
    ranked = best_rows.sort_values(
        ["Temperature", "R2", "Pearson_r", "RMSE"],
        ascending=[True, False, False, True],
    )
    return ranked.groupby("Temperature", as_index=False).head(1)


def plot_best_metric(metric_name, best_rows, ylabel, filename):
    fig, ax = plt.subplots(figsize=(9, 6))
    pivot = best_rows.pivot(index="Temperature", columns="Relationship", values=metric_name)
    pivot.plot(kind="bar", ax=ax)
    ax.set_title(f"Best Model Comparison - {metric_name}")
    ax.set_xlabel("Temperature group")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(title="Relationship")

    for container in ax.containers:
        ax.bar_label(container, fmt="%.3f", padding=3)

    fig.tight_layout()
    path = OUTPUT_DIR / filename
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_all_model_r2(metrics):
    for temperature in sorted(metrics["Temperature"].unique()):
        subset = metrics[metrics["Temperature"] == temperature]
        pivot = subset.pivot(index="Model", columns="Relationship", values="R2")
        fig, ax = plt.subplots(figsize=(11, 6))
        pivot.plot(kind="bar", ax=ax)
        ax.set_title(f"{temperature} - R2 Across All Models")
        ax.set_xlabel("Model")
        ax.set_ylabel("R2")
        ax.grid(axis="y", alpha=0.25)
        ax.legend(title="Relationship")
        ax.tick_params(axis="x", rotation=25)

        for container in ax.containers:
            ax.bar_label(container, fmt="%.3f", padding=3, fontsize=8)

        fig.tight_layout()
        path = OUTPUT_DIR / f"{temperature}_all_models_r2_comparison.png"
        fig.savefig(path, dpi=180)
        plt.close(fig)


def write_summary(best_rows, winners):
    lines = []
    lines.append("Thermocouple Relationship Reliability Comparison")
    lines.append("")
    lines.append("Ranking basis: higher R2 first, then higher Pearson r, then lower RMSE.")
    lines.append("")

    for temperature in sorted(best_rows["Temperature"].unique()):
        lines.append(f"{temperature}")
        temp_best = best_rows[best_rows["Temperature"] == temperature].sort_values("R2", ascending=False)
        for _, row in temp_best.iterrows():
            lines.append(
                f"- {row['Relationship']}: best model {row['Model']}, "
                f"R2={row['R2']:.4f}, Pearson r={row['Pearson_r']:.4f}, "
                f"RMSE={row['RMSE']:.4f} C, MAE={row['MAE']:.4f} C"
            )
        winner = winners[winners["Temperature"] == temperature].iloc[0]
        lines.append(f"Best/reliable choice: {winner['Relationship']} using {winner['Model']}.")
        lines.append("")

    overall = best_rows.groupby("Relationship")[["R2", "Pearson_r", "RMSE", "MAE"]].mean()
    overall = overall.sort_values(["R2", "Pearson_r", "RMSE"], ascending=[False, False, True])
    lines.append("Average of each relationship's best models across 30C and 37C")
    lines.append(overall.round(4).to_string())
    lines.append("")
    lines.append(f"Overall stronger relationship: {overall.index[0]}.")

    (OUTPUT_DIR / "comparison_summary.txt").write_text("\n".join(lines), encoding="utf-8")


def main():
    metrics = load_metrics()
    best_rows = best_by_relationship(metrics)
    winners = winners_by_temperature(best_rows)

    metrics.to_csv(OUTPUT_DIR / "all_model_metrics_combined.csv", index=False)
    best_rows.to_csv(OUTPUT_DIR / "best_model_per_relationship.csv", index=False)
    winners.to_csv(OUTPUT_DIR / "best_relationship_by_temperature.csv", index=False)

    plot_best_metric("R2", best_rows, "R2, higher is better", "best_model_r2_comparison.png")
    plot_best_metric("Pearson_r", best_rows, "Pearson r, higher is better", "best_model_pearson_comparison.png")
    plot_best_metric("RMSE", best_rows, "RMSE in C, lower is better", "best_model_rmse_comparison.png")
    plot_all_model_r2(metrics)
    write_summary(best_rows, winners)

    print("Wrote thermocouple relationship comparison results")
    for _, row in winners.iterrows():
        print(
            f"{row['Temperature']}: {row['Relationship']} "
            f"({row['Model']}, R2={row['R2']:.4f}, Pearson r={row['Pearson_r']:.4f})"
        )


if __name__ == "__main__":
    main()
