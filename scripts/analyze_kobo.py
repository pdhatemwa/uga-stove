#!/usr/bin/env python3
import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path


def identifier(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", (value or "").upper())


def label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").casefold())


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a UGA Stove Kobo CSV export")
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    with args.source.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source, delimiter=";"))

    household_counts = Counter(key for row in rows if (key := identifier(row.get("HH ID", ""))))
    serial_counts = Counter(
        key for row in rows if (key := identifier(row.get("Serial number", "")))
    )
    point_counts = Counter(
        key for row in rows if (key := label(row.get("Distribution Center", "")))
    )
    report = {
        "rows": len(rows),
        "columns": len(rows[0]) if rows else 0,
        "unique_household_ids": len(household_counts),
        "duplicate_household_keys": sum(1 for count in household_counts.values() if count > 1),
        "extra_household_rows": sum(count - 1 for count in household_counts.values() if count > 1),
        "unique_stove_serials": len(serial_counts),
        "duplicate_stove_keys": sum(1 for count in serial_counts.values() if count > 1),
        "extra_stove_rows": sum(count - 1 for count in serial_counts.values() if count > 1),
        "normalized_distribution_labels": len(point_counts),
        "blank_household_ids": sum(not identifier(row.get("HH ID", "")) for row in rows),
        "blank_serial_numbers": sum(not identifier(row.get("Serial number", "")) for row in rows),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
