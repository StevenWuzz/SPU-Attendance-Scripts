#!/usr/bin/env python3
"""Extract key fields from the GPS attendance XLS export."""

import json
from collections import defaultdict
from typing import DefaultDict, Dict, List, Tuple

import xlrd


def _build_map(path: str, include_type: Dict) -> Dict[str, List[Tuple[str, str, str]]]:
    """Return Nama Karyawan -> list of (Tipe Absensi, Tanggal Absensi, Alamat)."""
    workbook = xlrd.open_workbook(path)
    sheet = workbook.sheet_by_index(0)

    headers = [str(cell).strip() for cell in sheet.row_values(0)]
    required = ["Nama Karyawan", "Tanggal Absensi", "Tipe Absensi"]
    missing = [field for field in required if field not in headers]
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")

    col_index = {name: headers.index(name) for name in required}
    records: DefaultDict[str, List[Tuple[str, str, str]]] = defaultdict(list)

    for row_idx in range(1, sheet.nrows):
        row = sheet.row_values(row_idx)
        name = str(row[col_index["Nama Karyawan"]]).strip()
        if not name:
            continue

        tipe_absensi = str(row[col_index["Tipe Absensi"]]).strip()
        if tipe_absensi not in include_type:
            continue

        raw_date = row[col_index["Tanggal Absensi"]]
        tanggal_absensi = _extract_datetime(raw_date, workbook)

        records[name].append((tipe_absensi, tanggal_absensi))

    return dict(records)


def _extract_datetime(raw_value, workbook) -> str:
    """Convert the Excel date/time cell to a YYYY-MM-DD HH:MM:SS string."""
    if isinstance(raw_value, (int, float)):
        try:
            dt = xlrd.xldate_as_datetime(raw_value, workbook.datemode)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    text = str(raw_value).strip()
    if not text:
        return ""

    if "T" in text:
        return text.replace("T", " ")

    return text


def generate_filtered_report(input_path: str, include_type: Dict) -> Dict[str, List[Tuple[str, str, str]]]:
    mapping = _build_map(input_path, include_type)
    payload = json.dumps(mapping, ensure_ascii=False, indent=2)
    return json.loads(payload)
