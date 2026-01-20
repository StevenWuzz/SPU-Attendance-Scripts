import argparse
import json
from pathlib import Path
from datetime import date, datetime, time
from typing import Dict, List, Tuple, Union, Set

from src.filter_report import generate_filtered_report
from src.utils import OUTPUT_FOLDER, parse_datetime, MULAI_ISTIRAHAT, SELESAI_ISTIRAHAT, C_IN, C_OUT

MEAL_TYPES = {MULAI_ISTIRAHAT, SELESAI_ISTIRAHAT, C_IN, C_OUT}
C_IN_LATEST = time(9, 1)
C_OUT_EARLIEST = time(16, 0)
BREAKFAST = "Breakfast"
LUNCH = "Lunch"
DINNER = "Dinner"


def calculate_meal_pay_from_file(input_file = "report_scan_gps_2025-12-01_2025-12-31_20260101090802.xls") -> str:
    filtered_records = generate_filtered_report(input_file, include_type=MEAL_TYPES)
    meal_hours_breakdown: Dict[str, List[Dict[str, Union[float, bool]]]] = {}
    total_meal_count: Dict[str, int] = {}
    
    for employee, records in filtered_records.items():
        entitled_meals_count = 0
        meal_sessions: List[Dict[str, Union[float, bool]]] = []
        lunch_break_end_by_date: Dict[date, Tuple[datetime, str]] = {}
        entitled_types_by_date: Dict[date, Set[str]] = {}
        c_in_out_by_date: Dict[date, Set[str]] = {}
        parsed_records: List[Tuple[str, datetime, str]] = []

        # Precompute C IN/C OUT presence per date for lunch eligibility.
        for record in records:
            if len(record) < 2:
                continue

            meal_type, recorded_time = record[0], record[1]
            if meal_type not in MEAL_TYPES:
                continue

            parsed = parse_datetime(str(recorded_time))
            if not parsed:
                continue

            parsed_records.append((meal_type, parsed, recorded_time))
            if meal_type in {C_IN, C_OUT}:
                date_key = parsed.date()
                c_in_out_by_date.setdefault(date_key, set()).add(meal_type)

        for meal_type, parsed, recorded_time in parsed_records:
            date_key = parsed.date()

            if meal_type == SELESAI_ISTIRAHAT:
                if date_key not in lunch_break_end_by_date:
                    lunch_break_end_by_date[date_key] = (parsed, recorded_time)
                continue

            if meal_type == MULAI_ISTIRAHAT and date_key in lunch_break_end_by_date:
                end_dt, end_time = lunch_break_end_by_date.pop(date_key)
                hours = (end_dt - parsed).total_seconds() / 3600.0
                has_c_in = C_IN in c_in_out_by_date.get(date_key, set())
                has_c_out = C_OUT in c_in_out_by_date.get(date_key, set())
                is_eligible_lunch = hours <= 1.0 and has_c_in and has_c_out
                is_entitled_lunch = False
                if is_eligible_lunch and LUNCH not in entitled_types_by_date.get(date_key, set()):
                    is_entitled_lunch = True
                    entitled_meals_count += 1
                    entitled_types_by_date.setdefault(date_key, set()).add(LUNCH)
                meal_sessions.append(
                    {
                        "meal_type": LUNCH,
                        "mulai": recorded_time,
                        "selesai": end_time,
                        "hours": hours,
                        "is_eligible": is_eligible_lunch,
                        "is_entitled": is_entitled_lunch
                    }
                )
                continue

            if meal_type == C_OUT:
                is_eligible_supper = parsed - datetime.combine(parsed.date(), C_OUT_EARLIEST) >= 0
                is_entitled_supper = False
                if is_eligible_supper and DINNER not in entitled_types_by_date.get(date_key, set()):
                    is_entitled_supper = True
                    entitled_meals_count += 1
                    entitled_types_by_date.setdefault(date_key, set()).add(DINNER)
                meal_sessions.append(
                    {
                        "meal_type": DINNER,
                        "check_out_time": recorded_time,
                        "is_eligible": is_eligible_supper,
                        "is_entitled": is_entitled_supper
                    }
                )
                continue

            if meal_type == C_IN:
                is_eligible_breakfast = parsed - datetime.combine(parsed.date(), C_IN_LATEST) < 0
                is_entitled_breakfast = False
                if is_eligible_breakfast and BREAKFAST not in entitled_types_by_date.get(date_key, set()):
                    is_entitled_breakfast = True
                    entitled_meals_count += 1
                    entitled_types_by_date.setdefault(date_key, set()).add(BREAKFAST)
                meal_sessions.append(
                    {
                        "meal_type": BREAKFAST,
                        "check_in_time": recorded_time,
                        "is_eligible": is_eligible_breakfast,
                        "is_entitled": is_entitled_breakfast
                    }
                )
        
        meal_hours_breakdown[employee] = meal_sessions
        total_meal_count[employee] = entitled_meals_count

    return json.dumps({
            "meal_hours_breakdown": meal_hours_breakdown, 
            "total_meal_count": total_meal_count,
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
        default="report_scan_gps_2025-12-01_2025-12-31_20260101090802.xls",
        help="Path to the XLS export.",
    )
    parser.add_argument(
        "--out",
        "-o",
        help="Write JSON output to a file instead of stdout.",
    )
    args = parser.parse_args()

    meal_calculation = calculate_meal_pay_from_file(args.input)
    if args.out:
        output_path = Path(OUTPUT_FOLDER) / args.out
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            handle.write(meal_calculation)
    else:
        print(meal_calculation)

if __name__ == "__main__":
    main()



                
            
