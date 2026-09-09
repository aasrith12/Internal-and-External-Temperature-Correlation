from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "monte_carlo_combined_clean.csv"
OUTPUT_DIR = BASE_DIR / "monte_carlo_summary_results"
OUTPUT_DIR.mkdir(exist_ok=True)

RISK_THRESHOLD = 4.0


def load_data():
    return pd.read_csv(INPUT_FILE)


def write_summary_tables(df):
    box_hour = (
        df.groupby(["box_id", "layer", "box_number", "hour"])
        .agg(
            simulation_count=("simulated_value", "count"),
            mean_simulated_value=("simulated_value", "mean"),
            stdev_simulated_value=("simulated_value", "std"),
            min_simulated_value=("simulated_value", "min"),
            p05_simulated_value=("simulated_value", lambda s: s.quantile(0.05)),
            p50_simulated_value=("simulated_value", lambda s: s.quantile(0.50)),
            p95_simulated_value=("simulated_value", lambda s: s.quantile(0.95)),
            max_simulated_value=("simulated_value", "max"),
            risk_percent=("is_risky", lambda s: 100 * s.mean()),
            observed_average=("observed_average", "first"),
            observed_stdev=("observed_stdev", "first"),
        )
        .reset_index()
    )
    box_hour.to_csv(OUTPUT_DIR / "monte_carlo_box_hour_summary.csv", index=False)

    hour24 = box_hour[box_hour["hour"] == 24].copy()
    box_ranking = hour24.sort_values(
        ["risk_percent", "p95_simulated_value", "mean_simulated_value"],
        ascending=[False, False, False],
    )
    box_ranking.to_csv(OUTPUT_DIR / "monte_carlo_hour24_box_risk_ranking.csv", index=False)

    layer_hour = (
        df.groupby(["layer", "hour"])
        .agg(
            simulation_count=("simulated_value", "count"),
            mean_simulated_value=("simulated_value", "mean"),
            stdev_simulated_value=("simulated_value", "std"),
            min_simulated_value=("simulated_value", "min"),
            p05_simulated_value=("simulated_value", lambda s: s.quantile(0.05)),
            p50_simulated_value=("simulated_value", lambda s: s.quantile(0.50)),
            p95_simulated_value=("simulated_value", lambda s: s.quantile(0.95)),
            max_simulated_value=("simulated_value", "max"),
            risk_percent=("is_risky", lambda s: 100 * s.mean()),
        )
        .reset_index()
    )
    layer_hour.to_csv(OUTPUT_DIR / "monte_carlo_layer_hour_summary.csv", index=False)

    layer_ranking = (
        layer_hour[layer_hour["hour"] == 24]
        .copy()
        .sort_values(["risk_percent", "mean_simulated_value"], ascending=[False, False])
    )
    layer_ranking.to_csv(OUTPUT_DIR / "monte_carlo_hour24_layer_ranking.csv", index=False)

    crossing_rows = []
    for (box_id, layer, box_number), rows in box_hour.groupby(["box_id", "layer", "box_number"]):
        crossed = rows[rows["risk_percent"] > 0].sort_values("hour")
        crossing_rows.append(
            {
                "box_id": box_id,
                "layer": layer,
                "box_number": box_number,
                "first_risk_hour": None if crossed.empty else int(crossed.iloc[0]["hour"]),
                "risk_percent_at_24h": float(rows[rows["hour"] == 24]["risk_percent"].iloc[0]),
                "mean_simulated_value_at_24h": float(rows[rows["hour"] == 24]["mean_simulated_value"].iloc[0]),
                "p95_simulated_value_at_24h": float(rows[rows["hour"] == 24]["p95_simulated_value"].iloc[0]),
            }
        )
    first_crossing = pd.DataFrame(crossing_rows).sort_values(
        ["first_risk_hour", "risk_percent_at_24h", "p95_simulated_value_at_24h"],
        ascending=[True, False, False],
        na_position="last",
    )
    first_crossing.to_csv(OUTPUT_DIR / "monte_carlo_box_first_risk_crossing.csv", index=False)

    return box_hour, box_ranking, layer_hour, layer_ranking, first_crossing


def plot_layer_mean_trends(layer_hour):
    fig, ax = plt.subplots(figsize=(10, 6))
    for layer, rows in layer_hour.groupby("layer"):
        ax.plot(rows["hour"], rows["mean_simulated_value"], marker="o", linewidth=2, label=f"Layer {layer}")
    ax.axhline(RISK_THRESHOLD, color="black", linestyle="--", linewidth=1.2, label=f"Risk threshold {RISK_THRESHOLD:g}")
    ax.set_title("Monte Carlo Layer Mean Simulated Value Over Time")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Mean simulated value")
    ax.set_xticks(sorted(layer_hour["hour"].unique()))
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "monte_carlo_layer_mean_trends.png", dpi=180)
    plt.close(fig)


def plot_layer_risk_trends(layer_hour):
    fig, ax = plt.subplots(figsize=(10, 6))
    for layer, rows in layer_hour.groupby("layer"):
        ax.plot(rows["hour"], rows["risk_percent"], marker="o", linewidth=2, label=f"Layer {layer}")
    ax.set_title(f"Monte Carlo Risk Over Time by Layer (Value >= {RISK_THRESHOLD:g})")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Risk of loss (%)")
    ax.set_ylim(0, 105)
    ax.set_xticks(sorted(layer_hour["hour"].unique()))
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "monte_carlo_layer_risk_trends.png", dpi=180)
    plt.close(fig)


def plot_hour24_box_risk_ranking(box_ranking):
    rows = box_ranking.sort_values("risk_percent", ascending=True)
    colors = rows["layer"].map({1: "#2a78d6", 2: "#1baf7a", 3: "#eda100", 4: "#4a3aa7"})
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(rows["box_id"], rows["risk_percent"], color=colors)
    ax.set_title("Monte Carlo Box Risk Ranking at Hour 24")
    ax.set_xlabel("Risk of loss (%)")
    ax.set_ylabel("Box")
    ax.set_xlim(0, 105)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "monte_carlo_hour24_box_risk_ranking.png", dpi=180)
    plt.close(fig)


def plot_hour24_uncertainty(box_ranking):
    rows = box_ranking.sort_values("mean_simulated_value", ascending=True)
    xerr_lower = rows["mean_simulated_value"] - rows["p05_simulated_value"]
    xerr_upper = rows["p95_simulated_value"] - rows["mean_simulated_value"]
    colors = rows["layer"].map({1: "#2a78d6", 2: "#1baf7a", 3: "#eda100", 4: "#4a3aa7"})

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.errorbar(
        rows["mean_simulated_value"],
        rows["box_id"],
        xerr=[xerr_lower, xerr_upper],
        fmt="none",
        ecolor="#777777",
        elinewidth=1.4,
        capsize=3,
        zorder=1,
    )
    ax.scatter(rows["mean_simulated_value"], rows["box_id"], c=colors, s=52, zorder=2)
    ax.axvline(RISK_THRESHOLD, color="black", linestyle="--", linewidth=1.2)
    ax.set_title("Monte Carlo Hour-24 Uncertainty by Box")
    ax.set_xlabel("Simulated value: mean with 5th-95th percentile interval")
    ax.set_ylabel("Box")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "monte_carlo_hour24_box_uncertainty.png", dpi=180)
    plt.close(fig)


def plot_layer_heatmaps(box_hour):
    hour24 = box_hour[box_hour["hour"] == 24]
    state_space_path = BASE_DIR / "state_space_summary_results" / "box_hour_summary.csv"
    coords = pd.read_csv(state_space_path)[["box_id", "x_inches", "y_inches"]].drop_duplicates()
    hour24 = hour24.merge(coords, on="box_id", how="left")

    for layer, rows in hour24.groupby("layer"):
        fig, ax = plt.subplots(figsize=(7, 6))
        scatter = ax.scatter(
            rows["x_inches"],
            rows["y_inches"],
            c=rows["risk_percent"],
            s=420,
            cmap="Reds",
            vmin=0,
            vmax=100,
            edgecolor="black",
            linewidth=1,
        )
        for _, row in rows.iterrows():
            ax.text(row["x_inches"], row["y_inches"], row["box_id"], ha="center", va="center", fontsize=9, weight="bold")
        ax.set_title(f"Layer {layer} Monte Carlo Risk Heat Map at Hour 24")
        ax.set_xlabel("X coordinate (inches)")
        ax.set_ylabel("Y coordinate (inches)")
        ax.grid(True, alpha=0.2)
        fig.colorbar(scatter, ax=ax, label="Risk of loss (%) at hour 24")
        fig.tight_layout()
        fig.savefig(OUTPUT_DIR / f"monte_carlo_layer_{layer}_hour24_risk_heatmap.png", dpi=180)
        plt.close(fig)


def write_text_summary(layer_ranking, box_ranking, first_crossing):
    lines = [
        "Monte Carlo summary analysis",
        f"Risk threshold used: simulated value >= {RISK_THRESHOLD:g}",
        "",
        "Layer ranking by hour-24 risk:",
    ]
    for _, row in layer_ranking.iterrows():
        lines.append(
            f"- Layer {int(row['layer'])}: hour-24 risk={row['risk_percent']:.1f}%, "
            f"mean simulated value={row['mean_simulated_value']:.2f}, "
            f"95th percentile={row['p95_simulated_value']:.2f}"
        )

    lines.extend(["", "Highest-risk boxes at hour 24:"])
    for _, row in box_ranking.head(10).iterrows():
        lines.append(
            f"- {row['box_id']}: risk={row['risk_percent']:.1f}%, "
            f"mean={row['mean_simulated_value']:.2f}, p95={row['p95_simulated_value']:.2f}"
        )

    lines.extend(["", "Earliest boxes with any simulated risk:"])
    for _, row in first_crossing.head(10).iterrows():
        lines.append(
            f"- {row['box_id']}: first risk hour={row['first_risk_hour']}, "
            f"risk at 24h={row['risk_percent_at_24h']:.1f}%"
        )

    (OUTPUT_DIR / "summary.txt").write_text("\n".join(lines), encoding="utf-8")


def write_image_descriptions():
    descriptions = {
        "monte_carlo_layer_mean_trends.png": [
            "Data used: `monte_carlo_layer_hour_summary.csv`, generated by averaging all 500 Monte Carlo simulations per box-hour and then aggregating by layer and hour.",
            f"What it shows: a line chart of mean simulated value over time for Layers 1-4. The dashed horizontal line marks the risk threshold of {RISK_THRESHOLD:g}.",
            "How to read it: higher lines mean higher simulated temperature/loss values. A layer crossing the dashed line means the simulated layer average has entered the risk zone.",
            "Main result: Layer 1 is highest throughout the later time points. Layer 4 becomes second highest by hour 24. Layers 2 and 3 stay lower.",
        ],
        "monte_carlo_layer_risk_trends.png": [
            "Data used: `monte_carlo_layer_hour_summary.csv`, specifically the percentage of simulations where `simulated_value >= 4`.",
            "What it shows: risk of loss percentage over time for each layer.",
            "How to read it: 0% means no simulations crossed the threshold; 100% means every simulation crossed it.",
            "Main result: Layer 1 becomes risky earliest and reaches very high risk by hours 18-24. Layer 4 rises later but becomes high risk by hour 24. Layer 3 remains the lowest-risk layer.",
        ],
        "monte_carlo_hour24_box_risk_ranking.png": [
            "Data used: `monte_carlo_hour24_box_risk_ranking.csv`, using each box's Monte Carlo risk percentage at hour 24.",
            "What it shows: a horizontal bar chart ranking all boxes by probability of loss at hour 24. Bar colors identify the layer.",
            "How to read it: boxes with bars closer to 100% are almost always above the threshold in simulation and should be treated as high-risk positions.",
            "Main result: Layer 1 boxes are the dominant high-risk group. `L4B18`, `L4B20`, and `L2B6` are also important non-Layer-1 hotspots.",
        ],
        "monte_carlo_hour24_box_uncertainty.png": [
            "Data used: `monte_carlo_hour24_box_risk_ranking.csv`, using mean simulated value plus 5th and 95th percentiles at hour 24.",
            f"What it shows: each box's hour-24 simulated mean as a point, with an uncertainty interval from the 5th to 95th percentile. The dashed vertical line is the risk threshold of {RISK_THRESHOLD:g}.",
            "How to read it: a point to the right of the threshold means the average simulation is risky. A long interval means more uncertainty. If most or all of the interval is right of the threshold, the risk is robust.",
            "Main result: Layer 1 boxes sit clearly beyond the threshold. Some Layer 4 boxes also have high means and wide intervals extending far into risky values.",
        ],
        "monte_carlo_layer_1_hour24_risk_heatmap.png": [
            "Data used: `monte_carlo_box_hour_summary.csv` filtered to Layer 1 and hour 24, merged with box coordinates from the cleaned state-space summary.",
            "What it shows: a top-down map of Layer 1 where marker color is Monte Carlo risk of loss at hour 24.",
            "How to read it: darker red means higher simulated risk. Each marker is labeled by box ID.",
            "Main result: Layer 1 is broadly high-risk at hour 24, with most positions at or near complete risk.",
        ],
        "monte_carlo_layer_2_hour24_risk_heatmap.png": [
            "Data used: `monte_carlo_box_hour_summary.csv` filtered to Layer 2 and hour 24, merged with state-space box coordinates.",
            "What it shows: Layer 2 spatial risk pattern at hour 24.",
            "How to read it: darker red positions are more likely to exceed the risk threshold in simulation.",
            "Main result: `L2B6` is the main Layer 2 risk hotspot. Other Layer 2 boxes have moderate to low risk.",
        ],
        "monte_carlo_layer_3_hour24_risk_heatmap.png": [
            "Data used: `monte_carlo_box_hour_summary.csv` filtered to Layer 3 and hour 24, merged with state-space box coordinates.",
            "What it shows: Layer 3 spatial risk pattern at hour 24.",
            "How to read it: compare marker darkness to locate the highest-probability risk positions within Layer 3.",
            "Main result: Layer 3 is the safest layer overall. `L3B13` is the main hotspot, while `L3B12` and `L3B14` are low-risk.",
        ],
        "monte_carlo_layer_4_hour24_risk_heatmap.png": [
            "Data used: `monte_carlo_box_hour_summary.csv` filtered to Layer 4 and hour 24, merged with state-space box coordinates.",
            "What it shows: Layer 4 spatial risk pattern at hour 24.",
            "How to read it: darker red points are higher-risk box positions at the final time point.",
            "Main result: Layer 4 has several high-risk positions by hour 24, led by `L4B18` and `L4B20`, while `L4B19` is lower-risk.",
        ],
    }

    lines = ["# Monte Carlo Result Image Descriptions", ""]
    for image_name, paragraphs in descriptions.items():
        lines.append(f"## {image_name}")
        lines.extend(paragraphs)
        lines.append("")

    (OUTPUT_DIR / "image_descriptions.md").write_text("\n\n".join(lines), encoding="utf-8")

    for image_name, paragraphs in descriptions.items():
        sidecar = OUTPUT_DIR / f"{Path(image_name).stem}_description.txt"
        sidecar.write_text(f"{image_name}\n\n" + "\n\n".join(paragraphs), encoding="utf-8")


def main():
    df = load_data()
    box_hour, box_ranking, layer_hour, layer_ranking, first_crossing = write_summary_tables(df)
    plot_layer_mean_trends(layer_hour)
    plot_layer_risk_trends(layer_hour)
    plot_hour24_box_risk_ranking(box_ranking)
    plot_hour24_uncertainty(box_ranking)
    plot_layer_heatmaps(box_hour)
    write_text_summary(layer_ranking, box_ranking, first_crossing)
    write_image_descriptions()

    print(f"Wrote results to {OUTPUT_DIR}")
    print("Summary CSVs: 5")
    print("Plots: 8")
    print("Image descriptions: image_descriptions.md plus one sidecar .txt per plot")
    print("Top hour-24 risk boxes:")
    for _, row in box_ranking.head(5).iterrows():
        print(f"  {row['box_id']}: {row['risk_percent']:.1f}%")


if __name__ == "__main__":
    main()
