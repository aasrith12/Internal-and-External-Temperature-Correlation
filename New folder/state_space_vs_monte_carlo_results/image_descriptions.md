# Observed vs Monte Carlo Result Image Descriptions



## observed_vs_monte_carlo_mean_scatter.png

Data used: `observed_vs_monte_carlo_box_hour.csv`, using matched box-hour rows that exist in both observed state-space summaries and Monte Carlo summaries.

What it shows: each point compares one box-hour observed mean against the Monte Carlo simulated mean. The dashed diagonal line means perfect agreement.

How to read it: points near the diagonal mean Monte Carlo matches observed data closely. Points above the line mean Monte Carlo is higher than observed; points below mean Monte Carlo is lower.

Main result: the points mostly track the diagonal, so the simulation is aligned with observed average behavior overall.



## hour24_observed_vs_monte_carlo_box_comparison.png

Data used: `hour24_observed_vs_monte_carlo_ranking.csv`, filtered to hour 24.

What it shows: blue bars are observed hour-24 means by box; red points are Monte Carlo hour-24 means for the same boxes. The dashed line is the risk threshold.

How to read it: when the red point sits close to the end of the blue bar, Monte Carlo agrees with observed data. Values right of the threshold are risky.

Main result: the highest observed boxes are also high in Monte Carlo, especially Layer 1 boxes and key Layer 4/Layer 2 hotspots.



## hour24_monte_carlo_mean_difference_by_box.png

Data used: `hour24_observed_vs_monte_carlo_ranking.csv`, using `Monte Carlo mean - observed mean` for each box at hour 24.

What it shows: whether Monte Carlo overestimates or underestimates each box's observed hour-24 mean.

How to read it: bars to the right of zero mean Monte Carlo is higher than observed. Bars to the left mean Monte Carlo is lower than observed.

Main result: differences are generally small because the Monte Carlo means were generated around the observed averages, but this plot identifies boxes with the largest deviations.



## layer_observed_vs_monte_carlo_mean_trends.png

Data used: `layer_hour_observed_vs_monte_carlo_summary.csv`, comparing observed and Monte Carlo mean values by layer and hour.

What it shows: each layer has an observed trend line and a Monte Carlo trend line across the matched hours.

How to read it: paired lines that overlap or run close together indicate good simulation alignment for that layer.

Main result: Monte Carlo follows the same layer ordering and time progression as the observed data.



## layer_observed_inside_monte_carlo_interval.png

Data used: `layer_hour_observed_vs_monte_carlo_summary.csv`, using the percent of observed box means that fall inside each Monte Carlo 5th-95th percentile range.

What it shows: how often the observed result is covered by the Monte Carlo uncertainty interval.

How to read it: higher percentages mean the simulation uncertainty range contains the observed data more often.

Main result: this is a coverage check. Low values would mean Monte Carlo uncertainty is too narrow or shifted; high values mean the simulation range is plausible.



## layer_1_hour24_risk_agreement_map.png

Data used: `hour24_observed_vs_monte_carlo_ranking.csv`, filtered to Layer 1 at hour 24.

What it shows: a spatial map showing whether observed risk and Monte Carlo risk agree for each Layer 1 box.

How to read it: red means both observed and Monte Carlo classify the position as risky; other colors show disagreement or low-risk agreement.

Main result: Layer 1 is broadly risky in both observed and simulated views.



## layer_2_hour24_risk_agreement_map.png

Data used: `hour24_observed_vs_monte_carlo_ranking.csv`, filtered to Layer 2 at hour 24.

What it shows: Layer 2 spatial agreement between observed threshold status and Monte Carlo risk status.

How to read it: red boxes are risky in both views; orange boxes are flagged by Monte Carlo but have observed means below threshold.

Main result: L2B6 is the major Layer 2 agreement hotspot, while the remaining boxes are lower or mixed.



## layer_3_hour24_risk_agreement_map.png

Data used: `hour24_observed_vs_monte_carlo_ranking.csv`, filtered to Layer 3 at hour 24.

What it shows: Layer 3 spatial agreement between observed and simulated risk.

How to read it: red indicates both methods see risk; green indicates both are low.

Main result: Layer 3 remains the safest layer, with fewer boxes risky in both views.



## layer_4_hour24_risk_agreement_map.png

Data used: `hour24_observed_vs_monte_carlo_ranking.csv`, filtered to Layer 4 at hour 24.

What it shows: Layer 4 spatial agreement between observed and simulated risk.

How to read it: red indicates consistent risk across both methods, highlighting the most dependable hotspots.

Main result: L4B18 and L4B20 are key Layer 4 risk positions in both observed and Monte Carlo results.

