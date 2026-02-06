import argparse
import json
from pathlib import Path
from datetime import date, datetime, time
from typing import Dict, List, Tuple, Union, Set

from src.filter_report import generate_filtered_report
from src.utils import (
    OUTPUT_FOLDER,
    format_datetime,
    parse_datetime,
    MULAI_ISTIRAHAT,
    SELESAI_ISTIRAHAT,
    C_IN,
    C_OUT,
)

MEAL_TYPES = {MULAI_ISTIRAHAT, SELESAI_ISTIRAHAT, C_IN, C_OUT}
C_IN_LATEST = time(9, 1)
C_OUT_EARLIEST = time(16, 0)
BREAKFAST = "Breakfast"
LUNCH = "Lunch"
DINNER = "Dinner"


def calculate_meals_count_from_file(input_file = "report_scan_gps_2025-12-01_2025-12-31_20260101090802.xlsx", start_date = None) -> str:
    filtered_records = generate_filtered_report(input_file, MEAL_TYPES, start_date)
    meal_hours_breakdown: Dict[str, List[Dict[str, Union[float, bool]]]] = {}
    total_meal_count: Dict[str, int] = {}
    
    for employee, records in filtered_records.items():
        entitled_meals_count = 0
        parsed_dates: List[datetime] = []
        meal_sessions: List[Dict[str, Union[float, bool]]] = []
        entitled_meals_by_date: Dict[date, Set[str]] = {}
        latest_c_in_by_date: Dict[date, datetime] = {}
        earliest_c_out_by_date: Dict[date, datetime] = {}
        latest_lunch_break_end_by_date: Dict[date, datetime] = {}
        earliest_lunch_break_start_by_date: Dict[date, datetime] = {}

        for record in records:
            if len(record) < 2:
                continue

            meal_type, recorded_time = record[0], record[1]
            if meal_type not in MEAL_TYPES:
                continue

            parsed = parse_datetime(str(recorded_time))
            if not parsed:
                continue

            date_key = parsed.date()
            parsed_dates.append(date_key)
            if meal_type == C_IN and date_key not in latest_c_in_by_date:
                latest_c_in_by_date[date_key] = parsed
            elif meal_type == C_OUT:
                earliest_c_out_by_date[date_key] = parsed
            elif meal_type == MULAI_ISTIRAHAT:
                earliest_lunch_break_start_by_date[date_key] = parsed
            elif meal_type == SELESAI_ISTIRAHAT and date_key not in latest_lunch_break_end_by_date:
                latest_lunch_break_end_by_date[date_key] = parsed

        for date_key in parsed_dates:
            latest_c_in = latest_c_in_by_date.get(date_key)
            is_eligible_breakfast = (
                latest_c_in is not None
                and latest_c_in < datetime.combine(date_key, C_IN_LATEST)
            )
            is_entitled_breakfast = False
            if is_eligible_breakfast and BREAKFAST not in entitled_meals_by_date.get(date_key, set()):
                is_entitled_breakfast = True
                entitled_meals_count += 1
                entitled_meals_by_date.setdefault(date_key, set()).add(BREAKFAST)
            meal_sessions.append(
                {
                    "meal_type": BREAKFAST,
                    "check_in_time": format_datetime(latest_c_in) if latest_c_in else None,
                    "is_eligible": is_eligible_breakfast,
                    "is_entitled": is_entitled_breakfast
                }
            )

            earliest_c_out = earliest_c_out_by_date.get(date_key)
            is_eligible_dinner = (
                earliest_c_out is not None
                and earliest_c_out >= datetime.combine(date_key, C_OUT_EARLIEST)
            )
            is_entitled_dinner = False
            if is_eligible_dinner and DINNER not in entitled_meals_by_date.get(date_key, set()):
                is_entitled_dinner = True
                entitled_meals_count += 1
                entitled_meals_by_date.setdefault(date_key, set()).add(DINNER)
            meal_sessions.append(
                {
                    "meal_type": DINNER,
                    "check_out_time": format_datetime(earliest_c_out) if earliest_c_out else None,
                    "is_eligible": is_eligible_dinner,
                    "is_entitled": is_entitled_dinner
                }
            )

            end_lunch_break = latest_lunch_break_end_by_date.get(date_key)
            beginning_lunch_break = earliest_lunch_break_start_by_date.get(date_key)
            if end_lunch_break is None or beginning_lunch_break is None:
                continue
            is_c_in_out_in_order = (
                latest_c_in is not None
                and earliest_c_out is not None
                and latest_c_in < beginning_lunch_break
                and end_lunch_break < earliest_c_out
            )
            lunch_duration = (end_lunch_break - beginning_lunch_break).total_seconds() / 3600.0
            is_eligible_lunch = lunch_duration < (1.0 + 60/3600) and is_c_in_out_in_order
            is_entitled_lunch = False
            if is_eligible_lunch and LUNCH not in entitled_meals_by_date.get(date_key, set()):
                is_entitled_lunch = True
                entitled_meals_count += 1
                entitled_meals_by_date.setdefault(date_key, set()).add(LUNCH)
                meal_sessions.append(
                    {
                        "meal_type": LUNCH,
                        "mulai": format_datetime(beginning_lunch_break),
                        "selesai": format_datetime(end_lunch_break),
                        "duration": lunch_duration,
                        "is_eligible": is_eligible_lunch,
                        "is_entitled": is_entitled_lunch
                    }
                )
        
        meal_hours_breakdown[employee] = meal_sessions
        total_meal_count[employee] = entitled_meals_count

    return json.dumps({
            "total_meal_count": total_meal_count,
            "meal_hours_breakdown": meal_hours_breakdown,
        }, 
        ensure_ascii=False, 
        indent=2
    )

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Count number of entitled meals for each employee."
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

    meal_calculation = calculate_meals_count_from_file(args.input, args.date)
    output_path = Path(OUTPUT_FOLDER) / args.out
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        handle.write(meal_calculation)

if __name__ == "__main__":
    main()



                
            
