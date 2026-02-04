import argparse
import json
from pathlib import Path
from typing import Dict, Set

from .data_processing.calculate_meals_count import calculate_meals_count_from_file
from .data_processing.calculate_overtime_pay_remaining_debit import (
    calculate_overtime_pay_and_remaining_debit_from_file,
)
from .data_processing.calculate_valid_invalid_working_days import (
    calculate_valid_invalid_working_days_from_file,
)
from src.utils import OUTPUT_FOLDER


def _collect_employee_names(*maps: Dict[str, object]) -> Set[str]:
    employees: Set[str] = set()
    for mapping in maps:
        employees.update(mapping.keys())
    return employees


def calculate_all_from_file(input_path: str) -> str:
    overtime_payload = json.loads(
        calculate_overtime_pay_and_remaining_debit_from_file(input_path)
    )
    working_days_payload = json.loads(
        calculate_valid_invalid_working_days_from_file(input_path)
    )
    meals_payload = json.loads(calculate_meals_count_from_file(input_path))

    overtime_to_be_paid = overtime_payload.get("overtime_to_be_paid_in_rupiah", {})
    remaining_debit = overtime_payload.get("remaining_debit_hours", {})
    valid_working_days = working_days_payload.get("valid_working_days", {})
    invalid_working_days = working_days_payload.get("invalid_working_days", {})
    meals_count = meals_payload.get("total_meal_count", {})

    employees = _collect_employee_names(
        overtime_to_be_paid,
        remaining_debit,
        valid_working_days,
        invalid_working_days,
        meals_count,
    )

    summary: Dict[str, Dict[str, float]] = {}
    for employee in sorted(employees):
        summary[employee] = {
            "valid_working_days": float(valid_working_days.get(employee, 0.0) or 0.0),
            "invalid_working_days": float(
                invalid_working_days.get(employee, 0.0) or 0.0
            ),
            "overtime_to_be_paid_in_rupiah": float(
                overtime_to_be_paid.get(employee, 0.0) or 0.0
            ),
            "remaining_debit_hours": float(
                remaining_debit.get(employee, 0.0) or 0.0
            ),
            "meals_count": int(meals_count.get(employee, 0) or 0),
        }

    return json.dumps(summary, ensure_ascii=False, indent=2)

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate per-employee attendance summary including working days, "
            "overtime pay, remaining debit hours, and meals count."
        )
    )
    parser.add_argument(
        "--input",
        "-i",
        default="report_scan_gps_2025-12-01_2025-12-31_20260101090802.xls",
        help="Path to the XLS export.",
    )
    parser.add_argument(
        "--out",
        "-o",
        help="Write JSON output to a file instead of stdout.",
    )
    args = parser.parse_args()

    payload = calculate_all_from_file(args.input)

    if args.out:
        output_path = Path(OUTPUT_FOLDER) / args.out
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            handle.write(payload)
    else:
        print(payload)

if __name__ == "__main__":
    main()
