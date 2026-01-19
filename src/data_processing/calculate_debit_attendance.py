#!/usr/bin/env python3
"""Extract key fields from the GPS attendance XLS export."""

import argparse
import json
from datetime import datetime, time
from pathlib import Path
from typing import Dict

from src.filter_report import generate_filtered_report
from src.utils import OUTPUT_FOLDER, parse_datetime, ABSENSI_MASUK, ABSENSI_PULANG, A_IN, A_OUT, MULAI_KERJA_DI_RUMAH, SELESAI_KERJA_DI_RUMAH

TIME_WINDOW = (time(8, 0), time(17, 0))
LATE_GRACE_PERIOD = 16 / 60.0  # hours

ATTENDANCE_TYPES = {ABSENSI_MASUK, ABSENSI_PULANG, A_IN, A_OUT, MULAI_KERJA_DI_RUMAH, SELESAI_KERJA_DI_RUMAH}
CHECK_IN_TYPES = {ABSENSI_MASUK, A_IN, MULAI_KERJA_DI_RUMAH}
CHECK_OUT_TYPES = {ABSENSI_PULANG, A_OUT, SELESAI_KERJA_DI_RUMAH}


def _calculate_debit(data) -> Dict[str, float]:
    summary: Dict[str, float] = {}

    for employee, records in data.items():
        debit_total = 0.0  # hours

        for record in records:
            if len(record) < 2:
                raise ValueError(f"Invalid record for {employee}: {record}")
            attendance_type, recorded_time = record[0], record[1]

            parsed = parse_datetime(str(recorded_time))
            if not parsed:
                raise ValueError(f"Cannot parse datetime: {recorded_time}")

            target_start_dt = datetime.combine(parsed.date(), TIME_WINDOW[0])
            target_end_dt = datetime.combine(parsed.date(), TIME_WINDOW[1])

            delta_start_hours = (parsed - target_start_dt).total_seconds() / 3600.0
            delta_end_hours = (parsed - target_end_dt).total_seconds() / 3600.0

            if attendance_type in CHECK_IN_TYPES and LATE_GRACE_PERIOD <= delta_start_hours:
                debit_total += delta_start_hours
            elif attendance_type in CHECK_OUT_TYPES and delta_end_hours <= 0:
                debit_total += -delta_end_hours

        summary[employee] = debit_total

    return summary

def calculate_debit_from_file(input_file = "report_scan_gps_2025-12-01_2025-12-31_20260101090802.xls") -> str:
    mapping = generate_filtered_report(input_file, include_type= ATTENDANCE_TYPES)
    payload = json.dumps(mapping, ensure_ascii=False, indent=2)
    statistics = _calculate_debit(json.loads(payload))
    return json.dumps(statistics, ensure_ascii=False, indent=2)
    

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse Nama Karyawan, Tipe Absensi, Tanggal Absensi, and Alamat from the XLS report."
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

    mapping = generate_filtered_report(args.input, include_type= ATTENDANCE_TYPES)
    payload = json.dumps(mapping, ensure_ascii=False, indent=2)
    json_data = json.loads(payload)

    statistics = _calculate_debit(json_data)
    output = json.dumps({"attendance": json_data, "debit_hours": statistics}, ensure_ascii=False, indent=2)
    
    if args.out:
        output_path = Path(OUTPUT_FOLDER) / args.out
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            handle.write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
