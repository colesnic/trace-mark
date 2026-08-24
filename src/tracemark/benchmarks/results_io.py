"""CSV output helpers for machine-readable benchmark results."""

from __future__ import annotations

import csv
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def write_rows_csv(path: Path, rows: list[Any]) -> None:
    """Write dataclass rows (or dicts) to a CSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("")
        return
    if is_dataclass(rows[0]):
        dict_rows = [asdict(row) for row in rows]
        fieldnames = list(dict_rows[0].keys())
    else:
        dict_rows = [dict(row) for row in rows]
        fieldnames = list(dict_rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in dict_rows:
            writer.writerow(row)


def write_metrics_json(path: Path, data: dict[str, Any]) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)
