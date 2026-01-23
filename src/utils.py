from datetime import datetime, time
from typing import Optional

OUTPUT_FOLDER = "outputs/"

ABSENSI_MASUK = "Absensi Masuk"
ABSENSI_PULANG = "Absensi Pulang"
MULAI_KERJA_DI_RUMAH = "Mulai Kerja di Rumah"
SELESAI_KERJA_DI_RUMAH = "Selesai Kerja di Rumah"
MULAI_LEMBUR = "Mulai Lembur"
SELESAI_LEMBUR = "Selesai Lembur"
MULAI_ISTIRAHAT = "Mulai Istirahat"
SELESAI_ISTIRAHAT = "Selesai Istirahat"
A_IN = "A IN"
A_OUT = "A OUT"
C_IN = "C IN"
C_OUT = "C OUT"

def parse_datetime(value: str) -> Optional[datetime]:
    """Parse a datetime string in YYYY-MM-DD HH:MM[:SS] format."""
    if not value:
        return None

    text = str(value).strip()
    if not text:
        return None

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    return None


def parse_time(value: str) -> Optional[time]:
    """Parse a time string in HH:MM[:SS] format, optionally with a date."""
    dt = parse_datetime(value)
    if dt:
        return dt.time()

    if not value:
        return None

    text = str(value).strip()
    if not text:
        return None

    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue

    return None


def format_datetime(value: datetime) -> str:
    """Format a datetime value as YYYY-MM-DD HH:MM:SS."""
    return value.strftime("%Y-%m-%d %H:%M:%S")
