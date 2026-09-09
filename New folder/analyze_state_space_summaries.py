from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "state_space_combined_clean.csv"
OUTPUT_DIR = BASE_DIR / "state_space_summary_results"
OUTPUT_DIR.mkdir(exist_ok=True)

RISK_THRESHOLD = 4.0


def load_data():
    return pd.read_csv(INPUT_FILE)


def write_summary_tables(df):
    box_hour = (
        df.groupby(["box_id", "layer", "box_number", "hour", "x_inches", "y_inches", "z_inches", "exposed_surfaces"])
        .agg(
            mean_value=("value", "mean"),
            stdev_value=("value", "std"),
            min_value=("value", "min"),
            max_value=("value", "max"),
            trial_count=("value", "count"),
        )
        .reset_index()
    )
    box_hour.to_csv(OUTPUT_DIR / "box_hour_summary.csv", index=False)

    first_last = box_hour.pivot_table(index=["box_id", "layer", "box_number"], columns="hour", values="mean_value")
    box_summary = (
        box_hour.groupby(["box_id", "layer", "box_number", "x_inches", "y_inches", "z_inches", "exposed_surfaces"])
        .agg(
            overall_mean=("mean_value", "mean"),
            hour_24_mean=("mean_value", lambda s: s[box_hour.loc[s.index, "hour"].eq(24)].iloc[0]),
            peak_mean=("mean_value", "max"),
            lowest_mean=("mean_value", "min"),
        )
        .reset_index()
    )
    box_summary["change_0_to_24"] = box_summary.apply(
        lambda row: first_last.loc[(row["box_id"], row["layer"], row["box_number"]), 24]
        - first_last.loc[(row["box_id"], row["layer"], row["box_number"]), 0],
        axis=1,
    )
    box_summary = box_summary.sort_values("hour_24_mean", ascending=False)
    box_summary.to_csv(OUTPUT_DIR / "box_summary_ranked.csv", index=False)

    layer_hour = (
        df.groupby(["layer", "hour"])
        .agg(
            mean_value=("value", "mean"),
            stdev_value=("value", "std"),
            min_value=("value", "min"),
            max_value=("value", "max"),
            observation_count=("value", "count"),
        )
        .reset_index()
    )
    layer_hour.to_csv(OUTPUT_DIR / "layer_hour_summary.csv", index=False)

    layer_summary = (
        layer_hour.groupby("layer")
        .agg(
            overall_mean=("mean_value", "mean"),
            hour_24_mean=("mean_value", lambda s: s[layer_hour.loc[s.index, "hour"].eq(24)].iloc[0]),
            peak_mean=("mean_value", "max"),
            lowest_mean=("mean_value", "min"),
        )
        .reset_index()
    )
    layer_summary["change_0_to_24"] = layer_summary["hour_24_mean"] - layer_hour[layer_hour["hour"] == 0][
        "mean_value"
    ].to_numpy()
    layer_summary = layer_summary.sort_values("hour_24_mean", ascending=False)
    layer_summary.to_csv(OUTPUT_DIR / "layer_summary_ranked.csv", index=False)

    risk_by_trial = df.copy()
    risk_by_trial["is_risky"] = risk_by_trial["value"] >= RISK_THRESHOLD
    risk_hour = (
        risk_by_trial.groupby(["layer", "hour"])
        .agg(
            risky_observations=("is_risky", "sum"),
            total_observations=("is_risky", "count"),
            risk_percent=("is_risky", lambda s: 100 * s.mean()),
        )
        .reset_index()
    )
    risk_hour.to_csv(OUTPUT_DIR / "layer_hour_risk_summary.csv", index=False)

    risk_box_hour = (
        risk_by_trial.groupby(["box_id", "layer", "box_number", "hour"])
        .agg(
            risky_observations=("is_risky", "sum"),
            total_observations=("is_risky", "count"),
            risk_percent=("is_risky", lambda s: 100 * s.mean()),
        )
        .reset_index()
    )
    risk_box_hour.to_csv(OUTPUT_DIR / "box_hour_risk_summary.csv", index=False)

    crossing_rows = []
    for (box_id, layer, box_number), rows in risk_box_hour.groupby(["box_id", "layer", "box_number"]):
        crossed = rows[rows["risk_percent"] > 0].sort_values("hour")
        crossing_rows.append(
            {
                "box_id": box_id,
                "layer": layer,
                "box_number": box_number,
                "first_risk_hour": None if crossed.empty else int(crossed.iloc[0]["hour"]),
                "risk_percent_at_24h": float(rows[rows["hour"] == 24]["risk_percent"].iloc[0]),
            }
        )
    first_crossing = pd.DataFrame(crossing_rows).sort_values(
        ["first_risk_hour", "risk_percent_at_24h", "box_number"],
        ascending=[True, False, True],
        na_position="last",
    )
    first_crossing.to_csv(OUTPUT_DIR / "box_first_risk_crossing.csv", index=False)

    return box_hour, box_summary, layer_hour, layer_summary, risk_hour, risk_box_hour, first_crossing


def plot_layer_trends(layer_hour):
    fig, ax = plt.subplots(figsize=(10, 6))
    for layer, rows in layer_hour.groupby("layer"):
        ax.plot(rows["hour"], rows["mean_value"], marker="o", linewidth=2, label=f"Layer {layer}")
    ax.axhline(RISK_THRESHOLD, color="black", linestyle="--", linewidth=1.2, label=f"Risk threshold {RISK_THRESHOLD:g}")
    ax.set_title("Layer Mean Value Over Time")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Mean value")
    ax.set_xticks(sorted(layer_hour["hour"].unique()))
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "layer_mean_trends.png", dpi=180)
    plt.close(fig)


def plot_hour24_box_ranking(box_summary):
    rows = box_summary.sort_values("hour_24_mean", ascending=True)
    colors = rows["layer"].map({1: "#2a78d6", 2: "#1baf7a", 3: "#eda100", 4: "#4a3aa7"})
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(rows["box_id"], rows["hour_24_mean"], color=colors)
    ax.axvline(RISK_THRESHOLD, color="black", linestyle="--", linewidth=1.2)
    ax.set_title("Box Ranking at Hour 24")
    ax.set_xlabel("Mean value at hour 24")
    ax.set_ylabel("Box")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "hour24_box_ranking.png", dpi=180)
    plt.close(fig)


def plot_layer_risk_trends(risk_hour):
    fig, ax = plt.subplots(figsize=(10, 6))
    for layer, rows in risk_hour.groupby("layer"):
        ax.plot(rows["hour"], rows["risk_percent"], marker="o", linewidth=2, label=f"Layer {layer}")
    ax.set_title(f"Risk Over Time by Layer (Value >= {RISK_THRESHOLD:g})")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Risky observations (%)")
    ax.set_ylim(0, 105)
    ax.set_xticks(sorted(risk_hour["hour"].unique()))
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "layer_risk_trends.png", dpi=180)
    plt.close(fig)


def plot_layer_heatmaps(box_hour):
    hour24 = box_hour[box_hour["hour"] == 24]
    for layer, rows in hour24.groupby("layer"):
        fig, ax = plt.subplots(figsize=(7, 6))
        scatter = ax.scatter(
            rows["x_inches"],
            rows["y_inches"],
            c=rows["mean_value"],
            s=420,
            cmap="coolwarm",
            vmin=hour24["mean_value"].min(),
            vmax=hour24["mean_value"].max(),
            edgecolor="black",
            linewidth=1,
        )
        for _, row in rows.iterrows():
            ax.text(row["x_inches"], row["y_inches"], row["box_id"], ha="center", va="center", fontsize=9, weight="bold")
        ax.set_title(f"Layer {layer} Heat Map at Hour 24")
        ax.set_xlabel("X coordinate (inches)")
        ax.set_ylabel("Y coordinate (inches)")
        ax.grid(True, alpha=0.2)
        fig.colorbar(scatter, ax=ax, label="Mean value at hour 24")
        fig.tight_layout()
        fig.savefig(OUTPUT_DIR / f"layer_{layer}_hour24_heatmap.png", dpi=180)
        plt.close(fig)


def write_text_summary(layer_summary, box_summary, first_crossing):
    lines = [
        "State-space summary analysis",
        f"Risk threshold used: value >= {RISK_THRESHOLD:g}",
        "",
        "Layer ranking by hour-24 mean value:",
    ]
    for _, row in layer_summary.iterrows():
        lines.append(
            f"- Layer {int(row['layer'])}: hour-24 mean={row['hour_24_mean']:.2f}, "
            f"change 0->24={row['change_0_to_24']:.2f}"
        )

    lines.extend(["", "Highest boxes at hour 24:"])
    for _, row in box_summary.head(8).iterrows():
        lines.append(
            f"- {row['box_id']}: hour-24 mean={row['hour_24_mean']:.2f}, "
            f"layer={int(row['layer'])}, exposed surfaces={int(row['exposed_surfaces'])}"
        )

    lines.extend(["", "Earliest boxes with any risk crossing:"])
    for _, row in first_crossing.head(10).iterrows():
        lines.append(
            f"- {row['box_id']}: first risk hour={row['first_risk_hour']}, "
            f"risk at 24h={row['risk_percent_at_24h']:.1f}%"
        )

    (OUTPUT_DIR / "summary.txt").write_text("\n".join(lines), encoding="utf-8")


def write_image_descriptions():
    descriptions = {
        "layer_mean_trends.png": [
            "Data used: `layer_hour_summary.csv`, generated from `state_space_combined_clean.csv` by averaging all trial values for each layer at each hour.",
            f"What it shows: a line chart of mean value over time for Layers 1-4. The dashed horizontal line marks the risk threshold of {RISK_THRESHOLD:g}.",
            "How to read it: the higher the line, the greater the measured temperature/loss value for that layer. A layer crossing the dashed line means its average value has entered the risk zone.",
            "Main result: Layer 1 rises fastest and stays highest. Layer 4 becomes the second-highest layer by hour 24. Layers 2 and 3 remain lower, with Layer 3 the safest overall.",
        ],
        "hour24_box_ranking.png": [
            "Data used: `box_summary_ranked.csv`, specifically each box's mean value at hour 24 across available trials.",
            f"What it shows: a horizontal bar chart ranking all pallet boxes by their final hour-24 mean value. The vertical dashed line marks the risk threshold of {RISK_THRESHOLD:g}. Bar colors indicate the box's layer.",
            "How to read it: boxes farther to the right have higher final values and are more concerning. Any bar crossing the dashed line is above the selected risk threshold at hour 24.",
            "Main result: the top Layer 1 boxes dominate the highest-risk end of the ranking, with `L1B3`, `L1B5`, `L1B4`, `L1B2`, and `L1B1` all above the threshold. `L4B18`, `L4B20`, and `L2B6` are also important high-risk positions.",
        ],
        "layer_risk_trends.png": [
            "Data used: `layer_hour_risk_summary.csv`, generated by marking each cleaned observation as risky when its value is greater than or equal to the threshold.",
            f"What it shows: percentage of risky observations by layer at each hour, using `value >= {RISK_THRESHOLD:g}` as the risk definition.",
            "How to read it: a value of 100% means every available trial observation for that layer at that hour is above the risk threshold. A value of 0% means no observations are above the threshold.",
            "Main result: Layer 1 enters risk much earlier than the other layers. Layer 4 begins rising later but becomes strongly risky by the end. Layers 2 and 3 have lower risk percentages, with Layer 3 lowest overall.",
        ],
        "layer_1_hour24_heatmap.png": [
            "Data used: `box_hour_summary.csv`, filtered to Layer 1 and hour 24. Each plotted point is one box position using its `x_inches` and `y_inches` coordinates.",
            "What it shows: a top-down spatial heat map for Layer 1 at hour 24. Color represents the box's mean hour-24 value across available trials, and each marker is labeled with its box ID.",
            "How to read it: warmer/redder points are higher final values; cooler/bluer points are lower final values. Because all Layer 1 boxes are high, the map mainly shows which top-layer positions are highest among already-risky boxes.",
            "Main result: all Layer 1 boxes are elevated at hour 24, with `L1B3` and `L1B5` slightly highest.",
        ],
        "layer_2_hour24_heatmap.png": [
            "Data used: `box_hour_summary.csv`, filtered to Layer 2 and hour 24. Coordinates come from the state-space workbook.",
            "What it shows: a top-down spatial heat map for Layer 2 at hour 24, with marker color showing each box's mean final value.",
            "How to read it: compare marker colors and labels to see which Layer 2 positions are heating/lossing more than others.",
            "Main result: `L2B6` is the clear Layer 2 hotspot. The other Layer 2 boxes are lower, with `L2B7` and `L2B10` among the safer positions.",
        ],
        "layer_3_hour24_heatmap.png": [
            "Data used: `box_hour_summary.csv`, filtered to Layer 3 and hour 24.",
            "What it shows: a top-down spatial heat map for Layer 3 at hour 24.",
            "How to read it: use marker color to compare final mean values across Layer 3 box positions.",
            "Main result: Layer 3 is the coolest/lowest-risk layer overall. `L3B13` is the main Layer 3 hotspot, while `L3B14` and `L3B12` are among the lowest-risk boxes.",
        ],
        "layer_4_hour24_heatmap.png": [
            "Data used: `box_hour_summary.csv`, filtered to Layer 4 and hour 24.",
            "What it shows: a top-down spatial heat map for Layer 4 at hour 24.",
            "How to read it: warmer/redder markers indicate higher final values. Compare the box labels to locate the riskiest positions within the bottom/top referenced Layer 4 plane, depending on pallet orientation.",
            "Main result: Layer 4 has a late but strong rise. `L4B18` is the highest Layer 4 hotspot, followed by `L4B20` and `L4B17`. `L4B19` is the lowest Layer 4 position.",
        ],
    }

    lines = ["# State-space Result Image Descriptions", ""]
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
    box_hour, box_summary, layer_hour, layer_summary, risk_hour, _, first_crossing = write_summary_tables(df)
    plot_layer_trends(layer_hour)
    plot_hour24_box_ranking(box_summary)
    plot_layer_risk_trends(risk_hour)
    plot_layer_heatmaps(box_hour)
    write_text_summary(layer_summary, box_summary, first_crossing)
    write_image_descriptions()

    print(f"Wrote results to {OUTPUT_DIR}")
    print(f"Summary CSVs: 7")
    print(f"Plots: 7")
    print("Image descriptions: image_descriptions.md plus one sidecar .txt per plot")
    print("Top hour-24 boxes:")
    for _, row in box_summary.head(5).iterrows():
        print(f"  {row['box_id']}: {row['hour_24_mean']:.2f}")


if __name__ == "__main__":
    main()
