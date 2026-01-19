import argparse
import json
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple, Union

from src.filter_report import generate_filtered_report
from src.utils import OUTPUT_FOLDER, parse_datetime

MEAL_TYPES = {"Mulai Istirahat", "Selesai Istirahat", "C IN", "C OUT"}
C_IN_LATEST = time(9, 0)
C_OUT_EARLIEST = time(16, 0)

def calculate_meal_pay_from_file(input_file = "report_scan_gps_2025-12-01_2025-12-31_20260101090802.xls") -> str:
    filtered_records = generate_filtered_report(input_file, include_type=MEAL_TYPES)
    meal_hours_breakdown: Dict[str, List[Dict[str, Union[float, bool]]]] = {}
    total_meal_count: Dict[str, int] = {}
    
    for employee, records in filtered_records.items():
        entitled_meals_count = 0
        meal_sessions: List[Dict[str, Union[float, bool]]] = []
        lunch_break_end: Optional[Tuple[datetime, str]] = None

        for record in records:
            if len(record) < 2:
                continue

            meal_type, recorded_time = record[0], record[1]
            if meal_type not in MEAL_TYPES:
                continue

            parsed = parse_datetime(str(recorded_time))
            if not parsed:
                continue

            if meal_type == "Selesai Istirahat":
                lunch_break_end = (parsed, recorded_time)
            elif meal_type == "Mulai Istirahat" and lunch_break_end is not None:
                end_dt, end_time = lunch_break_end
                hours = (end_dt - parsed).total_seconds() / 3600.0
                if hours <= 1.0:
                    entitled_meals_count += 1
                meal_sessions.append(
                    {
                        "meal_type": "Lunch",
                        "mulai": recorded_time,
                        "selesai": end_time,
                        "hours": hours,
                        "is_entitled": hours <= 1.0
                    }
                )
                lunch_break_end = None
                continue

            if meal_type == "C OUT":
                is_entitled_supper = parsed - datetime.combine(parsed.date(), C_IN_LATEST) <= 0
                if is_entitled_supper:
                    entitled_meals_count += 1
                meal_sessions.append(
                    {
                        "meal_type": "Supper",
                        "check_out_time": recorded_time,
                        "is_entitled": is_entitled_supper
                    }
                )
            if meal_type == "C IN":
                is_entitled_breakfast =  parsed - datetime.combine(parsed.date(), C_OUT_EARLIEST) >= 0
                if is_entitled_breakfast:
                    entitled_meals_count += 1
                meal_sessions.append(
                    {
                        "meal_type": "Breakfast",
                        "check_in_time": recorded_time,
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
        with open(OUTPUT_FOLDER + args.out, "w", encoding="utf-8") as handle:
            handle.write(meal_calculation)
    else:
        print(meal_calculation)

if __name__ == "__main__":
    main()



                
            
