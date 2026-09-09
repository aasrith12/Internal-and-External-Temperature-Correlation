from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
STATE_SPACE_SUMMARY = BASE_DIR / "state_space_summary_results" / "box_hour_summary.csv"
MONTE_CARLO_SUMMARY = BASE_DIR / "monte_carlo_summary_results" / "monte_carlo_box_hour_summary.csv"
OUTPUT_DIR = BASE_DIR / "state_space_vs_monte_carlo_results"
OUTPUT_DIR.mkdir(exist_ok=True)

RISK_THRESHOLD = 4.0


def load_data():
    observed = pd.read_csv(STATE_SPACE_SUMMARY)
    monte_carlo = pd.read_csv(MONTE_CARLO_SUMMARY)
    return observed, monte_carlo


def compare_box_hours(observed, monte_carlo):
    columns = [
        "box_id",
        "layer",
        "box_number",
        "hour",
        "x_inches",
        "y_inches",
        "z_inches",
        "exposed_surfaces",
        "mean_value",
        "stdev_value",
        "trial_count",
    ]
    observed_subset = observed[columns].rename(
        columns={
            "mean_value": "observed_mean",
            "stdev_value": "observed_stdev",
            "trial_count": "observed_trial_count",
        }
    )

    monte_carlo_subset = monte_carlo[
        [
            "box_id",
            "layer",
            "box_number",
            "hour",
            "simulation_count",
            "mean_simulated_value",
            "stdev_simulated_value",
            "p05_simulated_value",
            "p50_simulated_value",
            "p95_simulated_value",
            "risk_percent",
        ]
    ]

    comparison = observed_subset.merge(
        monte_carlo_subset,
        on=["box_id", "layer", "box_number", "hour"],
        how="inner",
    )
    comparison["mean_difference"] = comparison["mean_simulated_value"] - comparison["observed_mean"]
    comparison["absolute_mean_difference"] = comparison["mean_difference"].abs()
    comparison["observed_is_risky"] = comparison["observed_mean"] >= RISK_THRESHOLD
    comparison["monte_carlo_is_risky"] = comparison["risk_percent"] >= 50
    comparison["risk_agreement"] = comparison["observed_is_risky"] == comparison["monte_carlo_is_risky"]
    comparison["observed_inside_5_95_interval"] = (
        comparison["observed_mean"].ge(comparison["p05_simulated_value"])
        & comparison["observed_mean"].le(comparison["p95_simulated_value"])
    )
    comparison.to_csv(OUTPUT_DIR / "observed_vs_monte_carlo_box_hour.csv", index=False)
    return comparison


def write_summary_tables(comparison):
    hour24 = comparison[comparison["hour"] == 24].copy()
    hour24 = hour24.sort_values(
        ["risk_percent", "observed_mean", "p95_simulated_value"],
        ascending=[False, False, False],
    )
    hour24.to_csv(OUTPUT_DIR / "hour24_observed_vs_monte_carlo_ranking.csv", index=False)

    layer_hour = (
        comparison.groupby(["layer", "hour"])
        .agg(
            observed_mean=("observed_mean", "mean"),
            monte_carlo_mean=("mean_simulated_value", "mean"),
            mean_difference=("mean_difference", "mean"),
            mean_absolute_difference=("absolute_mean_difference", "mean"),
            monte_carlo_risk_percent=("risk_percent", "mean"),
            risk_agreement_percent=("risk_agreement", lambda s: 100 * s.mean()),
            observed_inside_5_95_percent=("observed_inside_5_95_interval", lambda s: 100 * s.mean()),
            box_count=("box_id", "count"),
        )
        .reset_index()
    )
    layer_hour.to_csv(OUTPUT_DIR / "layer_hour_observed_vs_monte_carlo_summary.csv", index=False)

    layer_summary = (
        comparison.groupby("layer")
        .agg(
            observed_mean=("observed_mean", "mean"),
            monte_carlo_mean=("mean_simulated_value", "mean"),
            mean_difference=("mean_difference", "mean"),
            mean_absolute_difference=("absolute_mean_difference", "mean"),
            monte_carlo_risk_percent=("risk_percent", "mean"),
            risk_agreement_percent=("risk_agreement", lambda s: 100 * s.mean()),
            observed_inside_5_95_percent=("observed_inside_5_95_interval", lambda s: 100 * s.mean()),
            compared_box_hours=("box_id", "count"),
        )
        .reset_index()
        .sort_values("mean_absolute_difference", ascending=False)
    )
    layer_summary.to_csv(OUTPUT_DIR / "layer_observed_vs_monte_carlo_summary.csv", index=False)

    return hour24, layer_hour, layer_summary


def plot_observed_vs_monte_carlo_scatter(comparison):
    fig, ax = plt.subplots(figsize=(8, 7))
    colors = comparison["layer"].map({1: "#2a78d6", 2: "#1baf7a", 3: "#eda100", 4: "#4a3aa7"})
    ax.scatter(comparison["observed_mean"], comparison["mean_simulated_value"], c=colors, s=52, alpha=0.82)
    low = min(comparison["observed_mean"].min(), comparison["mean_simulated_value"].min())
    high = max(comparison["observed_mean"].max(), comparison["mean_simulated_value"].max())
    ax.plot([low, high], [low, high], color="black", linestyle="--", linewidth=1.2)
    ax.set_title("Observed Mean vs Monte Carlo Mean")
    ax.set_xlabel("Observed state-space mean")
    ax.set_ylabel("Monte Carlo simulated mean")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "observed_vs_monte_carlo_mean_scatter.png", dpi=180)
    plt.close(fig)


def plot_hour24_comparison(hour24):
    rows = hour24.sort_values("observed_mean", ascending=True)
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(rows["box_id"], rows["observed_mean"], color="#2a78d6", alpha=0.75, label="Observed mean")
    ax.scatter(rows["mean_simulated_value"], rows["box_id"], color="#e34948", s=45, label="Monte Carlo mean", zorder=3)
    ax.axvline(RISK_THRESHOLD, color="black", linestyle="--", linewidth=1.2, label=f"Threshold {RISK_THRESHOLD:g}")
    ax.set_title("Hour-24 Observed Mean vs Monte Carlo Mean by Box")
    ax.set_xlabel("Value")
    ax.set_ylabel("Box")
    ax.grid(axis="x", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "hour24_observed_vs_monte_carlo_box_comparison.png", dpi=180)
    plt.close(fig)


def plot_difference_by_box(hour24):
    rows = hour24.sort_values("mean_difference", ascending=True)
    colors = rows["mean_difference"].map(lambda value: "#d03b3b" if value > 0 else "#2a78d6")
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(rows["box_id"], rows["mean_difference"], color=colors)
    ax.axvline(0, color="black", linewidth=1.2)
    ax.set_title("Hour-24 Monte Carlo Over/Under Estimate by Box")
    ax.set_xlabel("Monte Carlo mean - observed mean")
    ax.set_ylabel("Box")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "hour24_monte_carlo_mean_difference_by_box.png", dpi=180)
    plt.close(fig)


def plot_layer_mean_comparison(layer_hour):
    fig, ax = plt.subplots(figsize=(10, 6))
    for layer, rows in layer_hour.groupby("layer"):
        ax.plot(rows["hour"], rows["observed_mean"], marker="o", linewidth=2, label=f"Layer {layer} observed")
        ax.plot(rows["hour"], rows["monte_carlo_mean"], marker="s", linewidth=1.8, linestyle="--", label=f"Layer {layer} Monte Carlo")
    ax.axhline(RISK_THRESHOLD, color="black", linestyle=":", linewidth=1.2)
    ax.set_title("Layer Mean: Observed vs Monte Carlo")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Mean value")
    ax.set_xticks(sorted(layer_hour["hour"].unique()))
    ax.grid(True, alpha=0.25)
    ax.legend(ncol=2, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "layer_observed_vs_monte_carlo_mean_trends.png", dpi=180)
    plt.close(fig)


def plot_layer_agreement(layer_hour):
    fig, ax = plt.subplots(figsize=(10, 6))
    for layer, rows in layer_hour.groupby("layer"):
        ax.plot(rows["hour"], rows["observed_inside_5_95_percent"], marker="o", linewidth=2, label=f"Layer {layer}")
    ax.set_title("Observed Means Inside Monte Carlo 5th-95th Percentile Interval")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Observed box means inside interval (%)")
    ax.set_ylim(0, 105)
    ax.set_xticks(sorted(layer_hour["hour"].unique()))
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "layer_observed_inside_monte_carlo_interval.png", dpi=180)
    plt.close(fig)


def plot_risk_alignment_heatmap(hour24):
    state = hour24.copy()
    state["category"] = "Both low"
    state.loc[state["observed_is_risky"] & state["monte_carlo_is_risky"], "category"] = "Both risky"
    state.loc[state["observed_is_risky"] & ~state["monte_carlo_is_risky"], "category"] = "Observed risky only"
    state.loc[~state["observed_is_risky"] & state["monte_carlo_is_risky"], "category"] = "Monte Carlo risky only"
    colors = {
        "Both risky": "#d03b3b",
        "Monte Carlo risky only": "#eda100",
        "Observed risky only": "#4a3aa7",
        "Both low": "#1baf7a",
    }

    for layer, rows in state.groupby("layer"):
        fig, ax = plt.subplots(figsize=(7, 6))
        ax.scatter(
            rows["x_inches"],
            rows["y_inches"],
            c=rows["category"].map(colors),
            s=420,
            edgecolor="black",
            linewidth=1,
        )
        for _, row in rows.iterrows():
            ax.text(row["x_inches"], row["y_inches"], row["box_id"], ha="center", va="center", fontsize=9, weight="bold")
        ax.set_title(f"Layer {layer} Hour-24 Risk Agreement")
        ax.set_xlabel("X coordinate (inches)")
        ax.set_ylabel("Y coordinate (inches)")
        ax.grid(True, alpha=0.2)
        handles = [
            plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=color, markeredgecolor="black", markersize=9, label=label)
            for label, color in colors.items()
        ]
        ax.legend(handles=handles, loc="best", fontsize=8)
        fig.tight_layout()
        fig.savefig(OUTPUT_DIR / f"layer_{int(layer)}_hour24_risk_agreement_map.png", dpi=180)
        plt.close(fig)


def write_text_summary(comparison, hour24, layer_summary):
    corr = comparison["observed_mean"].corr(comparison["mean_simulated_value"])
    hour24_corr = hour24["observed_mean"].corr(hour24["mean_simulated_value"])
    overall_inside = 100 * comparison["observed_inside_5_95_interval"].mean()
    overall_risk_agreement = 100 * comparison["risk_agreement"].mean()

    both_risky = hour24[hour24["observed_is_risky"] & hour24["monte_carlo_is_risky"]]
    mc_only = hour24[~hour24["observed_is_risky"] & hour24["monte_carlo_is_risky"]]
    observed_only = hour24[hour24["observed_is_risky"] & ~hour24["monte_carlo_is_risky"]]

    lines = [
        "Observed state-space vs Monte Carlo comparison",
        f"Risk threshold used: value >= {RISK_THRESHOLD:g}",
        "",
        f"Overall observed-vs-Monte Carlo mean correlation: {corr:.3f}",
        f"Hour-24 observed-vs-Monte Carlo mean correlation: {hour24_corr:.3f}",
        f"Observed means inside Monte Carlo 5th-95th interval: {overall_inside:.1f}%",
        f"Observed risky/not-risky agreement with Monte Carlo >=50% risk: {overall_risk_agreement:.1f}%",
        "",
        "Layer ranking by largest mean absolute difference:",
    ]
    for _, row in layer_summary.iterrows():
        lines.append(
            f"- Layer {int(row['layer'])}: mean absolute difference={row['mean_absolute_difference']:.3f}, "
            f"risk agreement={row['risk_agreement_percent']:.1f}%, "
            f"inside interval={row['observed_inside_5_95_percent']:.1f}%"
        )

    lines.extend(["", "Hour-24 boxes risky in both observed and Monte Carlo views:"])
    for _, row in both_risky.sort_values("risk_percent", ascending=False).iterrows():
        lines.append(
            f"- {row['box_id']}: observed mean={row['observed_mean']:.2f}, "
            f"Monte Carlo mean={row['mean_simulated_value']:.2f}, risk={row['risk_percent']:.1f}%"
        )

    lines.extend(["", "Hour-24 boxes Monte Carlo flags as risky but observed mean is below threshold:"])
    if mc_only.empty:
        lines.append("- None")
    else:
        for _, row in mc_only.sort_values("risk_percent", ascending=False).iterrows():
            lines.append(
                f"- {row['box_id']}: observed mean={row['observed_mean']:.2f}, "
                f"Monte Carlo mean={row['mean_simulated_value']:.2f}, risk={row['risk_percent']:.1f}%"
            )

    lines.extend(["", "Hour-24 boxes observed as risky but Monte Carlo risk is below 50%:"])
    if observed_only.empty:
        lines.append("- None")
    else:
        for _, row in observed_only.sort_values("observed_mean", ascending=False).iterrows():
            lines.append(
                f"- {row['box_id']}: observed mean={row['observed_mean']:.2f}, "
                f"Monte Carlo mean={row['mean_simulated_value']:.2f}, risk={row['risk_percent']:.1f}%"
            )

    (OUTPUT_DIR / "summary.txt").write_text("\n".join(lines), encoding="utf-8")


def write_image_descriptions():
    descriptions = {
        "observed_vs_monte_carlo_mean_scatter.png": [
            "Data used: `observed_vs_monte_carlo_box_hour.csv`, using matched box-hour rows that exist in both observed state-space summaries and Monte Carlo summaries.",
            "What it shows: each point compares one box-hour observed mean against the Monte Carlo simulated mean. The dashed diagonal line means perfect agreement.",
            "How to read it: points near the diagonal mean Monte Carlo matches observed data closely. Points above the line mean Monte Carlo is higher than observed; points below mean Monte Carlo is lower.",
            "Main result: the points mostly track the diagonal, so the simulation is aligned with observed average behavior overall.",
        ],
        "hour24_observed_vs_monte_carlo_box_comparison.png": [
            "Data used: `hour24_observed_vs_monte_carlo_ranking.csv`, filtered to hour 24.",
            "What it shows: blue bars are observed hour-24 means by box; red points are Monte Carlo hour-24 means for the same boxes. The dashed line is the risk threshold.",
            "How to read it: when the red point sits close to the end of the blue bar, Monte Carlo agrees with observed data. Values right of the threshold are risky.",
            "Main result: the highest observed boxes are also high in Monte Carlo, especially Layer 1 boxes and key Layer 4/Layer 2 hotspots.",
        ],
        "hour24_monte_carlo_mean_difference_by_box.png": [
            "Data used: `hour24_observed_vs_monte_carlo_ranking.csv`, using `Monte Carlo mean - observed mean` for each box at hour 24.",
            "What it shows: whether Monte Carlo overestimates or underestimates each box's observed hour-24 mean.",
            "How to read it: bars to the right of zero mean Monte Carlo is higher than observed. Bars to the left mean Monte Carlo is lower than observed.",
            "Main result: differences are generally small because the Monte Carlo means were generated around the observed averages, but this plot identifies boxes with the largest deviations.",
        ],
        "layer_observed_vs_monte_carlo_mean_trends.png": [
            "Data used: `layer_hour_observed_vs_monte_carlo_summary.csv`, comparing observed and Monte Carlo mean values by layer and hour.",
            "What it shows: each layer has an observed trend line and a Monte Carlo trend line across the matched hours.",
            "How to read it: paired lines that overlap or run close together indicate good simulation alignment for that layer.",
            "Main result: Monte Carlo follows the same layer ordering and time progression as the observed data.",
        ],
        "layer_observed_inside_monte_carlo_interval.png": [
            "Data used: `layer_hour_observed_vs_monte_carlo_summary.csv`, using the percent of observed box means that fall inside each Monte Carlo 5th-95th percentile range.",
            "What it shows: how often the observed result is covered by the Monte Carlo uncertainty interval.",
            "How to read it: higher percentages mean the simulation uncertainty range contains the observed data more often.",
            "Main result: this is a coverage check. Low values would mean Monte Carlo uncertainty is too narrow or shifted; high values mean the simulation range is plausible.",
        ],
        "layer_1_hour24_risk_agreement_map.png": [
            "Data used: `hour24_observed_vs_monte_carlo_ranking.csv`, filtered to Layer 1 at hour 24.",
            "What it shows: a spatial map showing whether observed risk and Monte Carlo risk agree for each Layer 1 box.",
            "How to read it: red means both observed and Monte Carlo classify the position as risky; other colors show disagreement or low-risk agreement.",
            "Main result: Layer 1 is broadly risky in both observed and simulated views.",
        ],
        "layer_2_hour24_risk_agreement_map.png": [
            "Data used: `hour24_observed_vs_monte_carlo_ranking.csv`, filtered to Layer 2 at hour 24.",
            "What it shows: Layer 2 spatial agreement between observed threshold status and Monte Carlo risk status.",
            "How to read it: red boxes are risky in both views; orange boxes are flagged by Monte Carlo but have observed means below threshold.",
            "Main result: L2B6 is the major Layer 2 agreement hotspot, while the remaining boxes are lower or mixed.",
        ],
        "layer_3_hour24_risk_agreement_map.png": [
            "Data used: `hour24_observed_vs_monte_carlo_ranking.csv`, filtered to Layer 3 at hour 24.",
            "What it shows: Layer 3 spatial agreement between observed and simulated risk.",
            "How to read it: red indicates both methods see risk; green indicates both are low.",
            "Main result: Layer 3 remains the safest layer, with fewer boxes risky in both views.",
        ],
        "layer_4_hour24_risk_agreement_map.png": [
            "Data used: `hour24_observed_vs_monte_carlo_ranking.csv`, filtered to Layer 4 at hour 24.",
            "What it shows: Layer 4 spatial agreement between observed and simulated risk.",
            "How to read it: red indicates consistent risk across both methods, highlighting the most dependable hotspots.",
            "Main result: L4B18 and L4B20 are key Layer 4 risk positions in both observed and Monte Carlo results.",
        ],
    }

    lines = ["# Observed vs Monte Carlo Result Image Descriptions", ""]
    for image_name, paragraphs in descriptions.items():
        lines.append(f"## {image_name}")
        lines.extend(paragraphs)
        lines.append("")
    (OUTPUT_DIR / "image_descriptions.md").write_text("\n\n".join(lines), encoding="utf-8")

    for image_name, paragraphs in descriptions.items():
        sidecar = OUTPUT_DIR / f"{Path(image_name).stem}_description.txt"
        sidecar.write_text(f"{image_name}\n\n" + "\n\n".join(paragraphs), encoding="utf-8")


def main():
    observed, monte_carlo = load_data()
    comparison = compare_box_hours(observed, monte_carlo)
    hour24, layer_hour, layer_summary = write_summary_tables(comparison)

    plot_observed_vs_monte_carlo_scatter(comparison)
    plot_hour24_comparison(hour24)
    plot_difference_by_box(hour24)
    plot_layer_mean_comparison(layer_hour)
    plot_layer_agreement(layer_hour)
    plot_risk_alignment_heatmap(hour24)
    write_text_summary(comparison, hour24, layer_summary)
    write_image_descriptions()

    print(f"Wrote results to {OUTPUT_DIR}")
    print(f"Compared box-hour rows: {len(comparison)}")
    print("Summary CSVs: 4")
    print("Plots: 9")
    print("Image descriptions: image_descriptions.md plus one sidecar .txt per plot")


if __name__ == "__main__":
    main()
