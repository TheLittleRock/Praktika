import sqlite3
import bcrypt
import secrets
from datetime import datetime
from pathlib import Path
from app.config import DB_PATH, BACKUPS_DIR

# 12 Standard physics lab measurements for Winter Semester (FPRA1 / ZS)
MEASUREMENTS_ZS = [
    {"code": "01", "number": 1, "name": "Vzduchová dráha - ZZE, srážky, impuls síly", "semester_type": "ZS", "course_code": "FPRA1"},
    {"code": "02", "number": 2, "name": "Dynamika rotačního pohybu", "semester_type": "ZS", "course_code": "FPRA1"},
    {"code": "03", "number": 3, "name": "Měření modulu pružnosti v tahu a modulu pružnosti ve smyku", "semester_type": "ZS", "course_code": "FPRA1"},
    {"code": "04", "number": 4, "name": "Cavendishův experiment", "semester_type": "ZS", "course_code": "FPRA1"},
    {"code": "05", "number": 5, "name": "Poissonova konstanta a měření dutých objemů", "semester_type": "ZS", "course_code": "FPRA1"},
    {"code": "06", "number": 6, "name": "Kalorimetrie", "semester_type": "ZS", "course_code": "FPRA1"},
    {"code": "07", "number": 7, "name": "Tření a napětí vzduchu a kapalin", "semester_type": "ZS", "course_code": "FPRA1"},
    {"code": "08", "number": 8, "name": "Kondenzátor, mapování elektrostatického pole", "semester_type": "ZS", "course_code": "FPRA1"},
    {"code": "09", "number": 9, "name": "Rozšíření rozsahu miliampérmetru a voltmetru, cejchování dekády", "semester_type": "ZS", "course_code": "FPRA1"},
    {"code": "10", "number": 10, "name": "Harmonické oscilace", "semester_type": "ZS", "course_code": "FPRA1"},
    {"code": "11", "number": 11, "name": "Rezonanční obvody", "semester_type": "ZS", "course_code": "FPRA1"},
    {"code": "12", "number": 12, "name": "Coulombův zákon", "semester_type": "ZS", "course_code": "FPRA1"}
]

# Standard measurements for Summer Semester (FPRA2 / LS)
MEASUREMENTS_LS = [
    {"code": "LS01", "number": 1, "name": "Měření rychlosti světla", "semester_type": "LS", "course_code": "FPRA2"},
    {"code": "LS02", "number": 2, "name": "Interference a difrakce světla", "semester_type": "LS", "course_code": "FPRA2"},
    {"code": "LS03", "number": 3, "name": "Polarizace světla a optická aktivita", "semester_type": "LS", "course_code": "FPRA2"},
    {"code": "LS04", "number": 4, "name": "Geometrická optika a spektrometr", "semester_type": "LS", "course_code": "FPRA2"},
    {"code": "LS05", "number": 5, "name": "Fotoelektrický jev a Planckova konstanta", "semester_type": "LS", "course_code": "FPRA2"},
    {"code": "LS06", "number": 6, "name": "Hallův jev v polovodičích", "semester_type": "LS", "course_code": "FPRA2"},
    {"code": "LS07", "number": 7, "name": "Měření magnetické susceptibility", "semester_type": "LS", "course_code": "FPRA2"},
    {"code": "LS08", "number": 8, "name": "Elektronová difrakce", "semester_type": "LS", "course_code": "FPRA2"},
    {"code": "LS09", "number": 9, "name": "Rentgenové záření a Braggův zákon", "semester_type": "LS", "course_code": "FPRA2"},
    {"code": "LS10", "number": 10, "name": "Radioaktivní rozpad a Geiger-Müllerův počítač", "semester_type": "LS", "course_code": "FPRA2"},
    {"code": "LS11", "number": 11, "name": "Absorpce gama záření v látce", "semester_type": "LS", "course_code": "FPRA2"},
    {"code": "LS12", "number": 12, "name": "Franck-Hertzův experiment", "semester_type": "LS", "course_code": "FPRA2"}
]

# Measurements for ZFM (Základní fyzikální měření)
MEASUREMENTS_ZFM = [
    {"code": "ZFM01", "number": 1, "name": "ZFM 1: Hustota pevných látek a kapalin", "semester_type": "ZFM", "course_code": "ZFM2"},
    {"code": "ZFM02", "number": 2, "name": "ZFM 2: Povrchové napětí a viskozita", "semester_type": "ZFM", "course_code": "ZFM2"},
    {"code": "ZFM03", "number": 3, "name": "ZFM 3: Měrné teplo kapalin a fázové přeměny", "semester_type": "ZFM", "course_code": "ZFM2"},
    {"code": "ZFM04", "number": 4, "name": "ZFM 4: Rychlost zvuku akustickým rezonátorem", "semester_type": "ZFM", "course_code": "ZFM2"},
    {"code": "ZFM05", "number": 5, "name": "ZFM 5: Odpor vodičů a vnitřní odpor zdroje", "semester_type": "ZFM", "course_code": "ZFM2"},
    {"code": "ZFM06", "number": 6, "name": "ZFM 6: Teplotní závislost odporu termistoru", "semester_type": "ZFM", "course_code": "ZFM2"}
]

# Initial presets for point deductions and text comments
INITIAL_DEDUCTION_PRESETS = [
    # Formát
    {"type": "deduction", "category": "format", "pts": 0.25, "text": "teoretická část opomíjí části úlohy. Např. teoretický popis způsobu cejchování dekády."},
    {"type": "deduction", "category": "format", "pts": 0.25, "text": "Graf / tabulka není referencována v textu protokolu."},
    {"type": "deduction", "category": "format", "pts": 0.125, "text": "Chybí jednotka u naměřené nebo vypočtené veličiny."},
    {"type": "deduction", "category": "format", "pts": 0.125, "text": "Neakademický styl vyjadřování v protokolu."},
    {"type": "deduction", "category": "format", "pts": 0.25, "text": "Chybí nebo jsou nečitelné popisky os v grafu."},
    {"type": "deduction", "category": "format", "pts": 0.25, "text": "Chybí citace použité literatury nebo chybný formát referencí."},
    # Chyby
    {"type": "deduction", "category": "chyby", "pts": 0.125, "text": "Chybné zaokrouhlení (chyba na více než 1-2 platné číslice)."},
    {"type": "deduction", "category": "chyby", "pts": 0.25, "text": "Chybí určení statistické nebo systematické chyby měření."},
    {"type": "deduction", "category": "chyby", "pts": 0.25, "text": "V grafu chybí chybové úsečky (errorbary)."},
    {"type": "deduction", "category": "chyby", "pts": 0.125, "text": "Chyba fitu chybně interpretována jako chyba měření."},
    # Diskuze
    {"type": "deduction", "category": "diskuze", "pts": 0.25, "text": "Diskuze je pouze shrnutím výsledků bez hlubšího komentáře."},
    {"type": "deduction", "category": "diskuze", "pts": 0.25, "text": "Chybí porovnání s očekáváním nebo tabulkovou hodnotou."},
    {"type": "deduction", "category": "diskuze", "pts": 0.25, "text": "Nekomentována neshoda výsledku s teorií."},
    {"type": "deduction", "category": "diskuze", "pts": 0.25, "text": "Chybí diskuze systematických a statistických vlivů na měření."},
    # Výsledky
    {"type": "deduction", "category": "vysledky", "pts": 0.25, "text": "Chybí postup výpočtu nebo mezivýsledky."},
    {"type": "deduction", "category": "vysledky", "pts": 0.5, "text": "Nesplněn jeden ze zadaných pracovních úkolů."},
    {"type": "deduction", "category": "vysledky", "pts": 0.25, "text": "Nevysvětlený fit / podivné hodnoty parametrů fitu."},
    {"type": "deduction", "category": "vysledky", "pts": 0.25, "text": "Výsledné hodnoty neodpovídají naměřeným datům."}
]

INITIAL_COMMENT_PRESETS = [
    {"type": "comment", "category": "obecne", "pts": 0.0, "text": "to není akademický styl"},
    {"type": "comment", "category": "obecne", "pts": 0.0, "text": ", kde....čárka!"},
    {"type": "comment", "category": "obecne", "pts": 0.0, "text": "Opět, graf není referencován v textu."},
    {"type": "comment", "category": "obecne", "pts": 0.0, "text": "Opět, tabulka není nikde zmíněna."},
    {"type": "comment", "category": "obecne", "pts": 0.0, "text": "Tato část textu je naprosto zbytečná."},
    {"type": "comment", "category": "obecne", "pts": 0.0, "text": "Odkázat se na tabulku."},
    {"type": "comment", "category": "obecne", "pts": 0.0, "text": "Toto je vhodné do diskuze."},
    {"type": "comment", "category": "obecne", "pts": 0.0, "text": "Jak to vzniklo? Jak by se tomu dalo předejít?"},
    {"type": "comment", "category": "obecne", "pts": 0.0, "text": "Co je to za fit? Odkud se vzal? Co graf? Mělo by být popsáno v sekci vypracování."},
    {"type": "comment", "category": "obecne", "pts": 0.0, "text": "Diskuze není jen o shrnutí výsledků. Měla by více diskutovat co proč a jak vyšlo/nevyšlo."},
    {"type": "comment", "category": "obecne", "pts": 0.0, "text": "Texty v grafu jsou moc malé a je v rastrové grafice."}
]

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # Users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'assistant',
        created_at TEXT NOT NULL
    )
    """)

    # Semesters
    cur.execute("""
    CREATE TABLE IF NOT EXISTS semesters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """)

    # Slots / Termíny
    cur.execute("""
    CREATE TABLE IF NOT EXISTS slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        semester_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        day_of_week TEXT NOT NULL,
        time_start TEXT NOT NULL,
        time_end TEXT NOT NULL,
        room TEXT,
        course_code TEXT NOT NULL DEFAULT 'FPRA1',
        created_at TEXT NOT NULL,
        FOREIGN KEY(semester_id) REFERENCES semesters(id) ON DELETE CASCADE
    )
    """)

    # Measurements / Úlohy
    cur.execute("""
    CREATE TABLE IF NOT EXISTS measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL,
        number INTEGER NOT NULL,
        name TEXT NOT NULL,
        semester_type TEXT NOT NULL DEFAULT 'ZS',
        description TEXT
    )
    """)

    # Presets table (časté chyby / rychlé komentáře)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS presets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER DEFAULT NULL,
        type TEXT NOT NULL, -- 'deduction' or 'comment'
        category TEXT NOT NULL, -- 'vysledky', 'diskuze', 'format', 'chyby', 'obecne'
        pts REAL NOT NULL DEFAULT 0.0,
        text TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Protocols
    cur.execute("""
    CREATE TABLE IF NOT EXISTS protocols (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        semester_id INTEGER NOT NULL,
        slot_id INTEGER NOT NULL,
        measurement_id INTEGER NOT NULL,
        student_name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'new',
        source_filename TEXT NOT NULL,
        source_path TEXT NOT NULL,
        corrected_filename TEXT,
        corrected_path TEXT,
        evaluator_id INTEGER,
        total_points REAL DEFAULT 10.0,
        grade TEXT DEFAULT 'A',
        graded_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(semester_id) REFERENCES semesters(id),
        FOREIGN KEY(slot_id) REFERENCES slots(id),
        FOREIGN KEY(measurement_id) REFERENCES measurements(id),
        FOREIGN KEY(evaluator_id) REFERENCES users(id)
    )
    """)

    # Evaluation details
    cur.execute("""
    CREATE TABLE IF NOT EXISTS evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        protocol_id INTEGER UNIQUE NOT NULL,
        vysledky_score REAL NOT NULL,
        diskuze_score REAL NOT NULL,
        format_score REAL NOT NULL,
        chyby_score REAL NOT NULL,
        total_points REAL NOT NULL,
        grade TEXT NOT NULL,
        manual_grade_override TEXT,
        deductions_json TEXT NOT NULL DEFAULT '[]',
        raw_output_1 TEXT,
        raw_output_2 TEXT,
        general_comment TEXT DEFAULT '',
        updated_at TEXT NOT NULL,
        FOREIGN KEY(protocol_id) REFERENCES protocols(id) ON DELETE CASCADE
    )
    """)

    # Annotations state (drawing, pins, text, highlights)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS annotations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        protocol_id INTEGER UNIQUE NOT NULL,
        annotations_json TEXT NOT NULL DEFAULT '[]',
        updated_at TEXT NOT NULL,
        FOREIGN KEY(protocol_id) REFERENCES protocols(id) ON DELETE CASCADE
    )
    """)

    # Migrations: check if semester_type column exists in measurements
    try:
        cur.execute("ALTER TABLE measurements ADD COLUMN semester_type TEXT NOT NULL DEFAULT 'ZS'")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE protocols ADD COLUMN ai_proposals_json TEXT DEFAULT NULL")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE protocols ADD COLUMN ai_status TEXT DEFAULT 'pending'")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE measurements ADD COLUMN instructions_text TEXT DEFAULT ''")
    except Exception:
        pass

    try:
        cur.execute("SELECT value FROM app_settings WHERE key = 'gemini_api_key'")
        row = cur.fetchone()
        if not row or not row[0]:
            # Leave empty by default; user enters their own Gemini API key in Settings
            cur.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('gemini_api_key', '')")

        cur.execute("SELECT value FROM app_settings WHERE key = 'gemini_model'")
        mrow = cur.fetchone()
        if not mrow or not mrow[0] or '1.5' in mrow[0] or '2.5' in mrow[0]:
            cur.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('gemini_model', 'gemini-3.5-flash')")
            cur.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('ai_model', 'gemini-3.5-flash')")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE measurements ADD COLUMN course_code TEXT NOT NULL DEFAULT 'FPRA1'")
    except Exception:
        pass

    try:
        cur.execute("UPDATE measurements SET course_code = 'FPRA1' WHERE semester_type = 'ZS' OR course_code IS NULL")
        cur.execute("UPDATE measurements SET course_code = 'FPRA2' WHERE semester_type = 'LS'")
        cur.execute("UPDATE measurements SET course_code = 'ZFM2' WHERE semester_type = 'ZFM'")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE users ADD COLUMN custom_gemini_api_key TEXT DEFAULT NULL")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE slots ADD COLUMN course_code TEXT NOT NULL DEFAULT 'FPRA1'")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE presets ADD COLUMN user_id INTEGER DEFAULT NULL")
    except Exception:
        pass

    try:
        cur.execute("SELECT sql FROM sqlite_master WHERE name='measurements'")
        row = cur.fetchone()
        if row and "code TEXT UNIQUE" in row[0]:
            cur.execute("CREATE TABLE measurements_new (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL, number INTEGER NOT NULL, name TEXT NOT NULL, semester_type TEXT NOT NULL DEFAULT 'ZS', course_code TEXT NOT NULL DEFAULT 'FPRA1', description TEXT, instructions_text TEXT DEFAULT '', UNIQUE(course_code, code))")
            cur.execute("INSERT INTO measurements_new (id, code, number, name, semester_type, course_code, description, instructions_text) SELECT id, code, number, name, semester_type, course_code, description, COALESCE(instructions_text, '') FROM measurements")
            cur.execute("DROP TABLE measurements")
            cur.execute("ALTER TABLE measurements_new RENAME TO measurements")
    except Exception as e:
        pass

    try:
        cur.execute("ALTER TABLE protocols ADD COLUMN share_token TEXT DEFAULT NULL")
    except Exception:
        pass

    try:
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_protocols_share_token ON protocols(share_token)")
    except Exception:
        pass

    try:
        cur.execute("SELECT id FROM protocols WHERE share_token IS NULL OR share_token = ''")
        missing_token_rows = cur.fetchall()
        for r in missing_token_rows:
            tok = secrets.token_urlsafe(16)
            cur.execute("UPDATE protocols SET share_token = ? WHERE id = ?", (tok, r[0]))
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE evaluations ADD COLUMN general_comment TEXT DEFAULT ''")
    except Exception:
        pass

    # Seed Admin User if none exists
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        default_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode("utf-8")
        now = datetime.now().isoformat()
        cur.execute("""
        INSERT INTO users (username, password_hash, full_name, role, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, ("admin", default_hash, "Správce aplikace", "admin", now))

    # Update admin title if still 'Správce praktika'
    cur.execute("UPDATE users SET full_name = 'Správce aplikace' WHERE username = 'admin' AND full_name = 'Správce praktika'")

    # Seed Default Semesters
    cur.execute("SELECT COUNT(*) FROM semesters")
    if cur.fetchone()[0] == 0:
        now = datetime.now().isoformat()
        cur.execute("INSERT INTO semesters (code, name, is_active, created_at) VALUES ('2026ZS', 'Zimní semestr 2026', 1, ?)", (now,))
        cur.execute("INSERT INTO semesters (code, name, is_active, created_at) VALUES ('2026LS', 'Letní semestr 2026', 0, ?)", (now,))

    # Seed Measurements (Re-seed with clean names from Image 4)
    cur.execute("SELECT id, number, name FROM measurements WHERE semester_type = 'ZS'")
    zs_rows = cur.fetchall()
    if not zs_rows:
        for m in MEASUREMENTS_ZS:
            cur.execute("""
            INSERT INTO measurements (code, number, name, semester_type, course_code, description)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (m["code"], m["number"], m["name"], m["semester_type"], m["course_code"], ""))
    elif any(r[2].startswith("Úloha ") for r in zs_rows):
        for m in MEASUREMENTS_ZS:
            cur.execute("UPDATE measurements SET name = ?, code = ?, course_code = ? WHERE semester_type = 'ZS' AND number = ?",
                        (m["name"], m["code"], m["course_code"], m["number"]))

    # Seed Task 1 instructions if empty
    cur.execute("SELECT id, instructions_text FROM measurements WHERE number = 1 AND semester_type = 'ZS'")
    u1 = cur.fetchone()
    if u1 and not u1[1]:
        cur.execute("""
        UPDATE measurements SET instructions_text = ? WHERE id = ?
        """, (
            "Zadání úlohy 1: Vzduchová dráha - zákon zachování hybnosti a mechanické energie.\n"
            "Požadavky na protokol:\n"
            "1. Teoretický úvod: Odvození vztahu pro rovnoměrně zrychlený pohyb s = (1/2)*a*t^2, zákon zachování hybnosti při pružné i nepružné srážce vozíků.\n"
            "2. Naměřené hodnoty: Přehledné tabulky časů průchodu fotobuňkami pro jednotlivé hmotnosti vozíků a sklon dráhy.\n"
            "3. Grafické zpracování: Graf s(t^2) s lineární regresní přímkou a chybovými úsečkami (errorbary). Určení zrychlení a tíhového zrychlení g.\n"
            "4. Nejistoty: Výpočet statistické chyby a přenosu chyb pro rychlosti a energie. Zaokrouhlování chyb na 1 až 2 platné číslice, výsledky se stejným počtem desetinných míst jako chyba.\n"
            "5. Diskuze: Kvantitativní zhodnocení platnosti zákona zachování energie a hybnosti, ztráty mechanické energie při nepružné srážce, vliv odporu vzduchu a nerovnosti dráhy.",
            u1[0]
        ))

    cur.execute("SELECT COUNT(*) FROM measurements WHERE semester_type = 'LS'")
    if cur.fetchone()[0] < 12:
        for m in MEASUREMENTS_LS:
            cur.execute("""
            INSERT INTO measurements (code, number, name, semester_type, course_code, description)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (m["code"], m["number"], m["name"], m["semester_type"], m["course_code"], ""))

    cur.execute("SELECT COUNT(*) FROM measurements WHERE semester_type = 'ZFM'")
    if cur.fetchone()[0] < 6:
        for m in MEASUREMENTS_ZFM:
            cur.execute("""
            INSERT INTO measurements (code, number, name, semester_type, course_code, description)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (m["code"], m["number"], m["name"], m["semester_type"], m["course_code"], ""))

    # Seed Presets if none exist
    cur.execute("SELECT COUNT(*) FROM presets")
    if cur.fetchone()[0] == 0:
        now = datetime.now().isoformat()
        for p in INITIAL_DEDUCTION_PRESETS:
            cur.execute("INSERT INTO presets (type, category, pts, text, created_at) VALUES (?, ?, ?, ?, ?)",
                        (p["type"], p["category"], p["pts"], p["text"], now))
        for p in INITIAL_COMMENT_PRESETS:
            cur.execute("INSERT INTO presets (type, category, pts, text, created_at) VALUES (?, ?, ?, ?, ?)",
                        (p["type"], p["category"], p["pts"], p["text"], now))

    # Fix slots that had duplicate names
    cur.execute("SELECT id, name, room FROM slots")
    for s_id, s_name, s_room in cur.fetchall():
        if "Pondělí" in s_name and "(" in s_name:
            cur.execute("UPDATE slots SET name = 'Skupina 1' WHERE id = ?", (s_id,))
        elif "Středa" in s_name and "(" in s_name:
            cur.execute("UPDATE slots SET name = 'Skupina 2' WHERE id = ?", (s_id,))

    conn.commit()
    conn.close()

def create_sqlite_backup(target_path: Path):
    """Safely creates a consistent online SQLite backup using SQLite's native backup API with WAL checkpoint."""
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    src_conn = get_db()
    try:
        src_conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    except Exception as ex:
        print("wal_checkpoint warning during backup:", ex)
    
    dest_conn = sqlite3.connect(str(target_path), timeout=30.0)
    try:
        with dest_conn:
            src_conn.backup(dest_conn)
    finally:
        dest_conn.close()
        src_conn.close()

def perform_daily_auto_backup():
    """Performs automated daily backup, rotating to preserve the last 7 daily snapshots."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    backup_file = BACKUPS_DIR / f"praktika_auto_{today_str}.sqlite"
    if not backup_file.exists():
        try:
            create_sqlite_backup(backup_file)
            backups = sorted(BACKUPS_DIR.glob("praktika_auto_*.sqlite"))
            while len(backups) > 7:
                oldest = backups.pop(0)
                try:
                    oldest.unlink()
                except Exception:
                    pass
        except Exception as e:
            print("Auto backup error:", e)
            return None
    return backup_file
