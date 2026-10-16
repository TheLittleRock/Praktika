import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("PRAKTIKA_DATA_DIR", BASE_DIR / "data"))
PROTOCOLS_DIR = DATA_DIR / "protocols"
DB_PATH = DATA_DIR / "praktika.sqlite3"
BACKUPS_DIR = DATA_DIR / "backups"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
PROTOCOLS_DIR.mkdir(parents=True, exist_ok=True)
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

SECRET_KEY = os.getenv("PRAKTIKA_SECRET_KEY", "praktika-evaluation-super-secret-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

DAYS_OF_WEEK = ["Pondělí", "Úterý", "Středa", "Čtvrtek", "Pátek"]

# 12 Standard physics laboratory measurements
DEFAULT_MEASUREMENTS = [
    {"code": "U01", "name": "Úloha 1: Měření na vzduchové dráze (ZZH a ZZE)"},
    {"code": "U02", "name": "Úloha 2: Měření modulu pružnosti v tahu a ve smyku"},
    {"code": "U03", "name": "Úloha 3: Určení tíhového zrychlení reverzním kyvadlem"},
    {"code": "U04", "name": "Úloha 4: Měření momentu setrvačnosti těles"},
    {"code": "U05", "name": "Úloha 5: Studium kmitavého pohybu a tlumených kmitů"},
    {"code": "U06", "name": "Úloha 6: Měření viskozity kapalin"},
    {"code": "U07", "name": "Úloha 7: Měření povrchového napětí kapalin"},
    {"code": "U08", "name": "Úloha 8: Měření rychlosti zvuku v plynech a pevných látkách"},
    {"code": "U09", "name": "Úloha 9: Studium teplotní závislosti odporu a Ohmův zákon"},
    {"code": "U10", "name": "Úloha 10: Měření kapacity a indukčnosti střídavým můstkem"},
    {"code": "U11", "name": "Úloha 11: Studium magnetického pole Helmholtzových cívek"},
    {"code": "U12", "name": "Úloha 12: Měření indexu lomu spektrometrem"}
]

