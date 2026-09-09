from pathlib import Path
import re

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
SOURCE_FILE = BASE_DIR / "State-space Model Data.xlsx"
OUTPUT_FILE = BASE_DIR / "state_space_combined_clean.csv"


TRIAL_COLUMNS = ["Trial 2", "Trial 3", "Trial 4", "Trial 5", "Trial 6"]


def parse_box_id(box_id):
    match = re.fullmatch(r"L(\d+)B(\d+)", str(box_id).strip())
    if not match:
        raise ValueError(f"Unexpected box id: {box_id!r}")
    return int(match.group(1)), int(match.group(2))


def parse_coordinates(value):
    parts = [part.strip() for part in str(value).split(",")]
    if len(parts) != 3:
        raise ValueError(f"Unexpected coordinate value: {value!r}")
    return tuple(float(part) for part in parts)


def is_hour_marker(value):
    return isinstance(value, str) and re.fullmatch(r"Hour\s+\d+", value.strip()) is not None


def clean_state_space_data():
    raw = pd.read_excel(SOURCE_FILE, sheet_name=0, header=None)
    records = []
    current_hour = None
    header_row = None

    for row_index, row in raw.iterrows():
        first_cell = row.iloc[0]

        if is_hour_marker(first_cell):
            current_hour = int(str(first_cell).split()[1])
            header_row = None
            continue

        if current_hour is not None and first_cell == "Box ID":
            header_row = row
            continue

        if current_hour is None or header_row is None or pd.isna(first_cell):
            continue

        box_id = str(first_cell).strip()
        if not box_id.startswith("L"):
            continue

        layer, box_number = parse_box_id(box_id)
        x_coord, y_coord, z_coord = parse_coordinates(row.iloc[6])
        exposed_surfaces = int(row.iloc[7])

        for offset, trial_name in enumerate(TRIAL_COLUMNS, start=1):
            value = row.iloc[offset]
            if pd.isna(value) or value == "-":
                continue

            records.append(
                {
                    "hour": current_hour,
                    "box_id": box_id,
                    "layer": layer,
                    "box_number": box_number,
                    "trial": trial_name,
                    "value": float(value),
                    "x_inches": x_coord,
                    "y_inches": y_coord,
                    "z_inches": z_coord,
                    "exposed_surfaces": exposed_surfaces,
                }
            )

    cleaned = pd.DataFrame.from_records(records)
    cleaned = cleaned.sort_values(["hour", "layer", "box_number", "trial"]).reset_index(drop=True)
    cleaned.to_csv(OUTPUT_FILE, index=False)
    return cleaned


def main():
    cleaned = clean_state_space_data()
    print(f"Wrote {OUTPUT_FILE.name}")
    print(f"Rows: {len(cleaned)}")
    print(f"Hours: {cleaned['hour'].min()} to {cleaned['hour'].max()} ({cleaned['hour'].nunique()} time points)")
    print(f"Boxes: {cleaned['box_id'].nunique()}")
    print(f"Trials: {', '.join(sorted(cleaned['trial'].unique()))}")
    print(f"Missing values skipped: expected max 1300 rows, wrote {len(cleaned)} rows")


if __name__ == "__main__":
    main()
