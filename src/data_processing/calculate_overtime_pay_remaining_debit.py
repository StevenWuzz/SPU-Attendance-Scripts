import argparse
import json
from pathlib import Path
from typing import Dict

from .calculate_debit_attendance import calculate_debit_from_file
from .calculate_overtime import calculate_total_overtime_from_file
from src.utils import OUTPUT_FOLDER

OVERTIME_RATE_PER_HOUR = 15000

def calculate_overtime_pay_and_remaining_debit_from_file(input_path: str, start_date = None) -> str:
    debit_data = json.loads(calculate_debit_from_file(input_path, start_date)).get("debit_summary", {})
    overtime_data = json.loads(calculate_total_overtime_from_file(input_path, start_date))
    overtime_hours_data = overtime_data["total_overtime_hours"]

    overtime_to_be_paid: Dict[str, float] = {}
    remaining_debit: Dict[str, float] = {}
    for employee, debit_hours in debit_data.items():
        overtime_hours = overtime_hours_data.get(employee, 0.0)
        overtime_to_be_paid[employee] = max(0.0, overtime_hours - debit_hours) * OVERTIME_RATE_PER_HOUR
        remaining_debit[employee] = max(0.0, debit_hours - overtime_hours)

    return json.dumps({"overtime_to_be_paid_in_rupiah": overtime_to_be_paid, "remaining_debit_hours": remaining_debit}, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute overtime payment for each employee"
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

    payload = calculate_overtime_pay_and_remaining_debit_from_file(args.input, args.date)
    output_path = Path(OUTPUT_FOLDER) / args.out
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        handle.write(payload)

if __name__ == "__main__":
    main()
