import argparse
import json
from calendar import monthrange
from datetime import datetime, time
from pathlib import Path
from typing import Dict, List

from src.filter_report import generate_filtered_report
from src.utils import OUTPUT_FOLDER, parse_datetime, ABSENSI_MASUK, ABSENSI_PULANG, A_IN, A_OUT, MULAI_KERJA_DI_RUMAH, SELESAI_KERJA_DI_RUMAH

TIME_WINDOW = (time(8, 0), time(17, 0))
MAX_VALIDITY_TOLERANCE = 31 / 60.0 # hours
ATTENDANCE_TYPES = {ABSENSI_MASUK, ABSENSI_PULANG, A_IN, A_OUT, MULAI_KERJA_DI_RUMAH, SELESAI_KERJA_DI_RUMAH}
HOME_TYPES = {MULAI_KERJA_DI_RUMAH, SELESAI_KERJA_DI_RUMAH}
CHECK_TOLERANCE_IN = {ABSENSI_MASUK, MULAI_KERJA_DI_RUMAH}
CHECK_TOLERANCE_OUT = {ABSENSI_PULANG, SELESAI_KERJA_DI_RUMAH}
CHECK_IN_TYPES = {ABSENSI_MASUK, A_IN, MULAI_KERJA_DI_RUMAH}
CHECK_OUT_TYPES = {ABSENSI_PULANG, A_OUT, SELESAI_KERJA_DI_RUMAH}


def _get_number_of_days_in_month(year: int, month: int) -> int:
    _, days = monthrange(year, month)
    return days

def get_date_to_attendances(json_data) -> Dict[str, Dict[str, list]]:
    """Return employee -> date (YYYY-MM-DD) -> list of attendance records."""
    summary = {}

    for employee, records in json_data.items():
        date_map = {}
        for record in records:
            if len(record) < 2:
                continue
            recorded_time = record[1]
            parsed = parse_datetime(str(recorded_time))
            if not parsed:
                continue
            date_key = parsed.strftime("%Y-%m-%d")
            date_map.setdefault(date_key, []).append(record)
        summary[employee] = date_map

    return summary

def _count_valid_invalid_days(valid_value: float, invalid_value: float, is_valid: bool, attendance_type: str) -> tuple[float, float]:
    step = 0.25 if attendance_type in HOME_TYPES else 0.5
    if is_valid:
        valid_value = min(valid_value + step, step)
    else:
        invalid_value = max(invalid_value - step, -step)
    return valid_value, invalid_value

def calculate_valid_invalid_working_days_from_file(input_file = "report_scan_gps_2025-12-01_2025-12-31_20260101090802.xls") -> str:
    mapping = generate_filtered_report(input_file, include_type=ATTENDANCE_TYPES)
    payload = json.dumps(mapping, ensure_ascii=False, indent=2)
    employee_to_date_attendances = get_date_to_attendances(json.loads(payload))

    try: 
        date_to_attendances = next(iter(employee_to_date_attendances.values()))
        date = next(iter(date_to_attendances.keys()))
    except StopIteration:
        print("WARNING: No attendance records found in the input file, can't calculate valid/invalid working days.")
        return json.dumps({}, ensure_ascii=False, indent=2)
    parsed_date = datetime.strptime(date, "%Y-%m-%d")
    number_of_days = _get_number_of_days_in_month(parsed_date.year, parsed_date.month)

    employee_to_valid_days: Dict[str, float] = {}
    breakdown_valid_days: Dict[str, List[Dict[str, float]]] = {}
    employee_to_invalid_days: Dict[str, float] = {}
    breakdown_invalid_days: Dict[str, List[Dict[str, float]]] = {}
    for employee, date_to_attendances in employee_to_date_attendances.items():
        valid_days = 0.0
        invalid_days = 0.0

        for date in range(1, number_of_days + 1):
            date_key = f"{parsed_date.year}-{parsed_date.month:02d}-{date:02d}"
            attendances = date_to_attendances.get(date_key, [])
            if not attendances:
                continue
            
            valid_check_in, valid_check_out = 0.0, 0.0
            invalid_check_in, invalid_check_out = 0.0, 0.0
            for attendance in attendances:
                attendance_type, recorded_time = attendance[0], attendance[1]

                parsed = parse_datetime(str(recorded_time))
                if not parsed:
                    raise ValueError(f"Cannot parse datetime: {recorded_time}")
                
                target_start_dt = datetime.combine(parsed.date(), TIME_WINDOW[0])
                target_end_dt = datetime.combine(parsed.date(), TIME_WINDOW[1])

                delta_start_hours = (parsed - target_start_dt).total_seconds() / 3600.0
                delta_end_hours = (parsed - target_end_dt).total_seconds() / 3600.0

                is_check_in_valid = attendance_type == A_IN or (attendance_type in CHECK_TOLERANCE_IN and delta_start_hours < MAX_VALIDITY_TOLERANCE)
                is_check_out_valid = attendance_type == A_OUT or (attendance_type in CHECK_TOLERANCE_OUT and -delta_end_hours < MAX_VALIDITY_TOLERANCE)

                if attendance_type in CHECK_IN_TYPES:
                    valid_check_in, invalid_check_in = _count_valid_invalid_days(
                        valid_check_in, invalid_check_in, is_check_in_valid, attendance_type
                    )
                if attendance_type in CHECK_OUT_TYPES:
                    valid_check_out, invalid_check_out = _count_valid_invalid_days(
                        valid_check_out, invalid_check_out, is_check_out_valid, attendance_type
                    ) 

            valid_days += valid_check_in + valid_check_out
            invalid_days += invalid_check_in + invalid_check_out
            
            breakdown_valid_days[employee] = breakdown_valid_days.get(employee, []) + [
                {
                    "date": parsed.date().isoformat(),
                    "valid_check_in_count": valid_check_in,
                    "valid_check_out_count": valid_check_out,
                }
            ]
            breakdown_invalid_days[employee] = breakdown_invalid_days.get(employee, []) + [
                {
                    "date": parsed.date().isoformat(),
                    "invalid_check_in_count": invalid_check_in,
                    "invalid_check_out_count": invalid_check_out,
                }
            ]

        employee_to_valid_days[employee] = valid_days
        employee_to_invalid_days[employee] = invalid_days
    
    return json.dumps({
            "valid_working_days": employee_to_valid_days, 
            "invalid_working_days": employee_to_invalid_days, 
            "valid_days_breakdown": breakdown_valid_days, 
            "invalid_days_breakdown": breakdown_invalid_days
        }, 
        ensure_ascii=False, 
        indent=2
    )

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calculate valid and invalid working days from the attendance criteria"
    )
    parser.add_argument(
        "--input",
        "-i",
        default="report_scan_gps_2025-12-01_2025-12-31_20260101090802.xls",
        help="Path to the XLS export"
    )
    parser.add_argument(
        "--out",
        "-o",
        help="Write JSON output to a file instead of stdout.",
    )
    args = parser.parse_args()

    output = calculate_valid_invalid_working_days_from_file(args.input)
    if args.out:
        output_path = Path(OUTPUT_FOLDER) / args.out
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            handle.write(output)
    else:
        print(output)

if __name__ == "__main__":
    main()
