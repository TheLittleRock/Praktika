import re
import unicodedata
from pathlib import Path
from app.config import PROTOCOLS_DIR

def slugify(text: str) -> str:
    """Normalize text into safe filesystem string."""
    if not text:
        return ""
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    return re.sub(r'[-\s]+', '_', text)

def format_semester_folder(code: str, course_type: str = "") -> str:
    """Normalize semester code to FPRA1, FPRA2, ZFM2 with semester suffix, e.g. FPRA1_2026ZS."""
    clean = (code or "").strip().upper()
    ct = (course_type or "").strip().upper()
    
    if "ZFM" in ct or "ZFM" in clean:
        prefix = "ZFM2"
    elif "FPRA1" in ct or "FPRA1" in clean:
        prefix = "FPRA1"
    elif "FPRA2" in ct or "FPRA2" in clean:
        prefix = "FPRA2"
    elif "ZS" in clean:
        prefix = "FPRA1"
    elif "LS" in clean:
        prefix = "FPRA2"
    else:
        prefix = "FPRA1"

    if clean.startswith(prefix):
        return clean
    return f"{prefix}_{clean}"

def format_slot_folder(day_of_week: str = "", time_start: str = "", time_end: str = "", room: str = "", raw_name: str = "") -> str:
    """Format slot into simple clean folder name: e.g. Pondeli_8h or Pondeli_8h_F3 (no minutes zeroes, no end time)."""
    if day_of_week and time_start:
        hour_m = re.search(r'(\d{1,2})', time_start)
        hour = int(hour_m.group(1)) if hour_m else 8
        day_slug = slugify(day_of_week).capitalize()
        room_slug = f"_{room.strip().upper()}" if room and room.strip() else ""
        return f"{day_slug}_{hour}h{room_slug}"
    # Fallback to simplified raw_name
    name = re.sub(r':00', '', raw_name or 'praktikum')
    name = re.sub(r'\s*-\s*\d+.*', '', name)
    return slugify(name)

def get_protocol_storage_dirs(semester_code: str, slot_folder: str, measurement_code: str, student_name: str):
    sem_slug = format_semester_folder(semester_code)
    slot_slug = format_slot_folder(raw_name=slot_folder) if not ("_" in slot_folder and "h" in slot_folder) else slugify(slot_folder)
    meas_slug = slugify(measurement_code)
    stud_slug = slugify(student_name)

    base = PROTOCOLS_DIR / sem_slug / slot_slug / meas_slug / stud_slug
    source_dir = base / "source"
    corrected_dir = base / "corrected"

    source_dir.mkdir(parents=True, exist_ok=True)
    corrected_dir.mkdir(parents=True, exist_ok=True)

    return source_dir, corrected_dir

def save_source_file(file_bytes: bytes, filename: str, semester_code: str, slot_name: str, measurement_code: str, student_name: str) -> Path:
    source_dir, _ = get_protocol_storage_dirs(semester_code, slot_name, measurement_code, student_name)
    target_path = source_dir / filename
    with open(target_path, "wb") as f:
        f.write(file_bytes)
    return target_path

def save_corrected_file(file_bytes: bytes, filename: str, semester_code: str, slot_name: str, measurement_code: str, student_name: str) -> Path:
    _, corrected_dir = get_protocol_storage_dirs(semester_code, slot_name, measurement_code, student_name)
    target_path = corrected_dir / filename
    with open(target_path, "wb") as f:
        f.write(file_bytes)
    return target_path

def save_bodovani_file(content: str, semester_code: str, slot_name: str, measurement_code: str, student_name: str) -> Path:
    _, corrected_dir = get_protocol_storage_dirs(semester_code, slot_name, measurement_code, student_name)
    target_path = corrected_dir / "bodovani.txt"
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)
    return target_path

