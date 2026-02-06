#!/usr/bin/env python3
"""Filter overtime records and compute Selesai Lembur - Mulai Lembur durations."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from src.filter_report import generate_filtered_report
from src.utils import MULAI_LEMBUR, SELESAI_LEMBUR, OUTPUT_FOLDER, parse_datetime

OVERTIME_TYPES = {MULAI_LEMBUR, SELESAI_LEMBUR}


def _calculate_overtime_durations(
    records: Dict[str, List[List[str]]]
) -> Dict[str, List[Dict[str, float]]]:
    """Compute per-session overtime durations for each employee.

    Assumes entries are ordered: Selesai Lembur, Mulai Lembur, Selesai Lembur, ...
    """
    summary: Dict[str, List[Dict[str, Union[float, bool]]]] = {}

    for employee, entries in records.items():
        sessions: List[Dict[str, Union[float, bool]]] = []
        last_end: Optional[Tuple[datetime, str]] = None

        for record in entries:
            if len(record) < 2:
                continue

            attendance_type, recorded_time = record[0], record[1]
            if attendance_type not in OVERTIME_TYPES:
                continue

            parsed = parse_datetime(str(recorded_time))
            if not parsed:
                continue

            if attendance_type == "Selesai Lembur":
                last_end = (parsed, recorded_time)
                continue

            if attendance_type == "Mulai Lembur" and last_end is not None:
                end_dt, end_time = last_end
                hours = max((end_dt - parsed).total_seconds() / 3600.0, 8.0)
                same_date = parsed.date() == end_dt.date()
                sessions.append(
                    {
                        "mulai": recorded_time,
                        "selesai": end_time,
                        "hours": hours,
                        "isValid": same_date,
                    }
                )
                last_end = None

        summary[employee] = sessions

    return summary


def _calculate_total_overtime(
    durations: Dict[str, List[Dict[str, Union[float, bool]]]]
) -> Dict[str, float]:
    """Compute total overtime hours per employee"""
    total_overtime_hours: Dict[str, float] = {}

    for employee, sessions in durations.items():
        total = 0.0
        for session in sessions:
            if session.get("isValid"):
                total += float(session.get("hours", 0.0) or 0.0)
        total_overtime_hours[employee] = total

    return total_overtime_hours

def calculate_total_overtime_from_file(input_file = "report_scan_gps_2025-12-01_2025-12-31_20260101090802.xlsx", start_date = None) -> str:
    filtered = generate_filtered_report(input_file, OVERTIME_TYPES, start_date)
    durations = _calculate_overtime_durations(filtered)
    totals = _calculate_total_overtime(durations)
    payload = json.dumps({"overtime_sessions": durations, "total_overtime_hours": totals}, ensure_ascii=False, indent=2)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Filter overtime records and compute Selesai - Mulai differences."
    )
    parser.add_argument(
        "--input",
        "-i",
        default="report_scan_gps_2025-12-01_2025-12-31_20260101090802.xlsx",
        help="Path to the XLS export.",
    )
    parser.add_argument(
        "--date",
        "-d",
        default=None,
        help="Starting date of the resulting filtered report.",
    )
    parser.add_argument(
        "--out",
        "-o",
        help="Write JSON output to a file instead of stdout.",
    )
    args = parser.parse_args()

    payload = calculate_total_overtime_from_file(args.input, args.date)
    output_path = Path(OUTPUT_FOLDER) / args.out
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        handle.write(payload)

if __name__ == "__main__":
    main()
