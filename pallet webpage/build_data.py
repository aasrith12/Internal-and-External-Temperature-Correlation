"""Rebuild the offline browser dataset from existing pallet analysis CSVs."""
import csv
import json
import shutil
import hashlib
from pathlib import Path
from audit_data import audit

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "New folder"


def rows(relative):
    with (SOURCE / relative).open(encoding="utf-8-sig", newline="") as source:
        result = list(csv.DictReader(source))
    for row in result:
        for key, value in row.items():
            if key == "box_id":
                continue
            row[key] = float(value) if value else None
    return result


def main():
    boxes = rows("state_space_summary_results/box_summary_ranked.csv")
    observed = rows("state_space_summary_results/box_hour_summary.csv")
    simulated = rows("monte_carlo_summary_results/monte_carlo_box_hour_summary.csv")
    crossing = {r["box_id"]: r for r in rows("state_space_summary_results/box_first_risk_crossing.csv")}
    for box in boxes:
        box.update(crossing[box["box_id"]])
        box["observed"] = sorted((r for r in observed if r["box_id"] == box["box_id"]), key=lambda r: r["hour"])
        box["simulated"] = sorted((r for r in simulated if r["box_id"] == box["box_id"]), key=lambda r: r["hour"])
        assert len(box["observed"]) == 13 and len(box["simulated"]) == 5
    boxes.sort(key=lambda b: b["box_number"])
    assert len(boxes) == 20
    audit_result = audit(SOURCE, boxes)
    if not all(c['passed'] for c in audit_result['checks']):
        raise ValueError(json.dumps(audit_result['checks'], indent=2))
    downloads = HERE / 'sources'
    downloads.mkdir(exist_ok=True)
    sources = []
    paths = ['state_space_combined_clean.csv', 'monte_carlo_combined_clean.csv',
             'state_space_summary_results/box_hour_summary.csv',
             'state_space_summary_results/box_summary_ranked.csv',
             'state_space_summary_results/box_first_risk_crossing.csv',
             'monte_carlo_summary_results/monte_carlo_box_hour_summary.csv',
             'State-space Model Data.xlsx']
    paths += [f'Monte Carlo Method Layer {layer}.xlsx' for layer in range(1,5)]
    paths += [f'state_space_summary_results/layer_{layer}_hour24_heatmap.png' for layer in range(1,5)]
    for relative in paths:
        original = SOURCE / relative
        shutil.copy2(original, downloads / original.name)
        sources.append(dict(name=original.name, original='New folder/'+relative,
                            href='sources/'+original.name, sha256=hashlib.sha256(original.read_bytes()).hexdigest()))
    data = {
        "metadata": {
            "threshold": 4,
            "hours": [0, 6, 12, 18, 24],
            "valueUnit": "value (source unit unconfirmed)",
            "source": "Existing state-space and Monte Carlo summary CSVs in New folder",
            "geometryNote": "Box centers use source coordinates in inches. Box dimensions and pallet geometry are inferred for visualization.",
            "riskNote": "Risk is simulated threshold exceedance (value >= 4), not a validated spoilage probability.",
        },
        "boxes": boxes,
        "audit": audit_result,
        "sources": sources,
    }
    (HERE / "data.js").write_text("window.PALLET_DATA = " + json.dumps(data, separators=(",", ":"), allow_nan=False) + ";\n", encoding="utf-8")
    print(f"Built data.js: {len(boxes)} boxes, {len(observed)} observed summaries, {len(simulated)} simulation summaries")


if __name__ == "__main__":
    main()
