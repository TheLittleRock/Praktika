import os
import io
import csv
import zipfile
import json
import re
import time
import secrets
from datetime import datetime
from pathlib import Path
from typing import List, Optional

try:
    import pymupdf
except ImportError:
    import fitz as pymupdf

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status, Response, Request, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from fastapi.templating import Jinja2Templates
from app.config import BASE_DIR, DATA_DIR, PROTOCOLS_DIR, DB_PATH, BACKUPS_DIR
from app.database import get_db, init_db, create_sqlite_backup, perform_daily_auto_backup
from app.auth import verify_password, get_password_hash, create_access_token, get_current_user
from app.models import (
    UserLogin, UserCreate, UserResponse, ChangePasswordRequest,
    SemesterCreate, SemesterUpdate, SemesterResponse,
    SlotCreate, SlotUpdate, SlotResponse,
    MeasurementCreate, MeasurementUpdate, MeasurementResponse,
    PresetCreate, PresetResponse,
    EvaluationSaveRequest, AutosaveRequest, ProtocolAssignRequest, AnnotationSaveRequest,
    ProtocolMetadataUpdateRequest, BulkDeleteRequest, BulkUpdateRequest, AISettingsRequest, AdminPasswordResetRequest, ProfileUpdateRequest,
    UserAdminUpdateRequest, AutodetectResponse, AIProposalActionRequest,
    AIChatMessage, AIChatRequest, AIChatResponse
)
from app.storage import save_source_file, save_corrected_file, save_bodovani_file, slugify, format_slot_folder, format_semester_folder
from app.pdf_service import extract_pdf_annotations, burn_annotations_to_pdf, format_points, calculate_grade_letter
from app.ai_service import (
    analyze_protocol, get_gemini_api_key, save_gemini_api_key, get_ai_setting, save_ai_setting,
    run_background_ai_analysis, generate_task_rubric, merge_ai_results,
    chat_with_ai, get_protocol_chat_history, clear_protocol_chat_history
)
from app.version import VERSION


# Initialize Database & run daily backup check
init_db()
perform_daily_auto_backup()

app = FastAPI(title="Praktika Evaluation Studio", version=VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = BASE_DIR / "app" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ==========================================
# AUTHENTICATION & USER MANAGEMENT
# ==========================================

@app.post("/api/auth/login")
def login(credentials: UserLogin, response: Response):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash, full_name, role FROM users WHERE username = ?", (credentials.username,))
    user = cur.fetchone()
    conn.close()

    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Nesprávné uživatelské jméno nebo heslo")

    token = create_access_token({"sub": user["username"], "role": user["role"]})
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True, max_age=60*60*24*7)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"]
        }
    }

@app.get("/api/auth/me")
def get_me(user: dict = Depends(get_current_user)):
    return user

@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"status": "ok", "message": "Odhlášeno"}

@app.post("/api/auth/change-password")
def change_password(req: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users WHERE id = ?", (user["id"],))
    row = cur.fetchone()

    if not row or not verify_password(req.old_password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=400, detail="Současné heslo není správné")

    new_hash = get_password_hash(req.new_password)
    cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user["id"]))
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Heslo bylo úspěšně změněno"}

@app.post("/api/auth/profile")
def update_profile(req: ProfileUpdateRequest, user: dict = Depends(get_current_user)):
    if not req.full_name or not req.full_name.strip():
        raise HTTPException(status_code=400, detail="Jméno nesmí být prázdné")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET full_name = ? WHERE id = ?", (req.full_name.strip(), user["id"]))
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Profil byl úspěšně aktualizován", "full_name": req.full_name.strip()}

@app.get("/api/users", response_model=List[UserResponse])
def list_users(user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Pouze správce aplikace má přístup ke správě uživatelů")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, full_name, role, COALESCE(is_active, 1) as is_active FROM users ORDER BY full_name")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

@app.put("/api/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, req: UserAdminUpdateRequest, user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Pouze správce aplikace může upravovat uživatele")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, full_name, role, COALESCE(is_active, 1) as is_active FROM users WHERE id = ?", (user_id,))
    target = cur.fetchone()
    if not target:
        conn.close()
        raise HTTPException(status_code=404, detail="Uživatel nebyl nalezen")
    
    fields = []
    vals = []
    if req.full_name is not None and req.full_name.strip():
        fields.append("full_name = ?")
        vals.append(req.full_name.strip())
    if req.role is not None and req.role in ("admin", "assistant"):
        fields.append("role = ?")
        vals.append(req.role.strip())
    if req.is_active is not None:
        fields.append("is_active = ?")
        vals.append(1 if req.is_active else 0)
    
    if fields:
        vals.append(user_id)
        cur.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", tuple(vals))
        conn.commit()

    cur.execute("SELECT id, username, full_name, role, COALESCE(is_active, 1) as is_active FROM users WHERE id = ?", (user_id,))
    updated = dict(cur.fetchone())
    conn.close()
    return updated

@app.post("/api/users", response_model=UserResponse)
def create_user(new_user: UserCreate, user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Pouze správce aplikace může vytvářet nové uživatele")

    conn = get_db()
    cur = conn.cursor()
    try:
        pw_hash = get_password_hash(new_user.password)
        now = datetime.now().isoformat()
        cur.execute("""
        INSERT INTO users (username, password_hash, full_name, role, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, (new_user.username.strip(), pw_hash, new_user.full_name.strip(), new_user.role, now))
        user_id = cur.lastrowid
        conn.commit()
    except Exception:
        conn.close()
        raise HTTPException(status_code=400, detail="Uživatel s tímto jménem již existuje")
    conn.close()

    return {"id": user_id, "username": new_user.username, "full_name": new_user.full_name, "role": new_user.role}

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Pouze správce aplikace může mazat uživatele")

    if user["id"] == user_id:
        raise HTTPException(status_code=400, detail="Nemůžete smazat svůj vlastní administrátorský účet")

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Uživatel nenalezen")

        # Unassign any protocols assigned to this user so foreign keys don't fail
        cur.execute("UPDATE protocols SET evaluator_id = NULL WHERE evaluator_id = ?", (user_id,))
        # Remove presets created by this user
        cur.execute("DELETE FROM presets WHERE user_id = ?", (user_id,))
        # Delete user
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()

    return {"status": "ok", "message": "Uživatel byl smazán"}

@app.post("/api/users/{user_id}/reset-password")
def admin_reset_password(user_id: int, req: AdminPasswordResetRequest, user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Pouze správce aplikace může resetovat hesla")
    if not req.new_password or len(req.new_password.strip()) < 3:
        raise HTTPException(status_code=400, detail="Nové heslo musí mít alespoň 3 znaky")
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, full_name FROM users WHERE id = ?", (user_id,))
    target_user = cur.fetchone()
    if not target_user:
        conn.close()
        raise HTTPException(status_code=404, detail="Uživatel nebyl nalezen")
    
    pw_hash = get_password_hash(req.new_password.strip())
    cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (pw_hash, user_id))
    conn.commit()
    conn.close()
    return {"status": "ok", "message": f"Heslo pro uživatele {target_user['full_name'] or target_user['username']} bylo úspěšně nastaveno"}

# ==========================================
# SEMESTERS & SLOTS (TERMÍNY)
# ==========================================

@app.get("/api/semesters", response_model=List[SemesterResponse])
def get_semesters():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, code, name, is_active FROM semesters ORDER BY id DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

@app.post("/api/semesters", response_model=SemesterResponse)
def create_semester(item: SemesterCreate, user: dict = Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    try:
        cur.execute("""
        INSERT INTO semesters (code, name, is_active, created_at)
        VALUES (?, ?, ?, ?)
        """, (item.code.strip(), item.name.strip(), 1 if item.is_active else 0, now))
        sem_id = cur.lastrowid
        conn.commit()
    except Exception:
        conn.close()
        raise HTTPException(status_code=400, detail="Semestr s tímto kódem již existuje")
    conn.close()
    return {"id": sem_id, "code": item.code, "name": item.name, "is_active": item.is_active}

@app.post("/api/semesters/{sem_id}/activate")
def activate_semester(sem_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE semesters SET is_active = 0")
    cur.execute("UPDATE semesters SET is_active = 1 WHERE id = ?", (sem_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.put("/api/semesters/{sem_id}", response_model=SemesterResponse)
def update_semester(sem_id: int, item: SemesterUpdate, user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Pouze správce aplikace může upravovat semestry")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, is_active FROM semesters WHERE id = ?", (sem_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Semestr nebyl nalezen")
    
    try:
        cur.execute("UPDATE semesters SET code = ?, name = ? WHERE id = ?", (item.code.strip(), item.name.strip(), sem_id))
        conn.commit()
    except Exception:
        conn.close()
        raise HTTPException(status_code=400, detail="Semestr s tímto kódem již existuje")
    conn.close()
    return {"id": sem_id, "code": item.code.strip(), "name": item.name.strip(), "is_active": bool(row["is_active"])}

@app.delete("/api/semesters/{sem_id}")
def delete_semester(sem_id: int, user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Pouze správce aplikace může mazat semestry")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM protocols WHERE semester_id = ?", (sem_id,))
    proto_count = cur.fetchone()[0]
    if proto_count > 0:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Nelze smazat semestr, který obsahuje {proto_count} protokolů. Nejprve smažte nebo přesuňte protokoly.")
    
    cur.execute("DELETE FROM slots WHERE semester_id = ?", (sem_id,))
    cur.execute("DELETE FROM semesters WHERE id = ?", (sem_id,))
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Semestr byl smazán"}

@app.get("/api/slots", response_model=List[SlotResponse])
def get_slots(semester_id: Optional[int] = None, course_code: Optional[str] = None):
    conn = get_db()
    cur = conn.cursor()
    query = """
    SELECT id, semester_id, name, day_of_week, time_start, time_end, room, COALESCE(course_code, 'FPRA1') as course_code
    FROM slots WHERE 1=1
    """
    params = []
    if semester_id:
        query += " AND semester_id = ?"
        params.append(semester_id)
    if course_code:
        query += " AND (course_code = ? OR course_code IS NULL)"
        params.append(course_code)
    query += " ORDER BY semester_id DESC, day_of_week, time_start"
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

@app.post("/api/slots", response_model=SlotResponse)
def create_slot(slot: SlotCreate, user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Pouze administrátor může vytvářet termíny cvičení.")
    conn = get_db()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    c_code = slot.course_code or "FPRA1"
    cur.execute("""
    INSERT INTO slots (semester_id, name, day_of_week, time_start, time_end, room, course_code, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (slot.semester_id, slot.name.strip(), slot.day_of_week.strip(), slot.time_start.strip(), slot.time_end.strip(), slot.room.strip() if slot.room else "", c_code, now))
    slot_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {
        "id": slot_id,
        "semester_id": slot.semester_id,
        "name": slot.name,
        "day_of_week": slot.day_of_week,
        "time_start": slot.time_start,
        "time_end": slot.time_end,
        "room": slot.room,
        "course_code": c_code
    }

@app.put("/api/slots/{slot_id}", response_model=SlotResponse)
def update_slot(slot_id: int, slot: SlotUpdate, user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Pouze administrátor může upravovat termíny cvičení.")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, semester_id, name, day_of_week, time_start, time_end, room, COALESCE(course_code, 'FPRA1') as course_code FROM slots WHERE id = ?", (slot_id,))
    existing = cur.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Termín nenalezen")

    name = slot.name.strip() if slot.name is not None else existing["name"]
    day_of_week = slot.day_of_week.strip() if slot.day_of_week is not None else existing["day_of_week"]
    time_start = slot.time_start.strip() if slot.time_start is not None else existing["time_start"]
    time_end = slot.time_end.strip() if slot.time_end is not None else existing["time_end"]
    room = slot.room.strip() if slot.room is not None else existing["room"]
    course_code = slot.course_code.strip() if slot.course_code is not None else existing["course_code"]

    cur.execute("""
    UPDATE slots SET name = ?, day_of_week = ?, time_start = ?, time_end = ?, room = ?, course_code = ?
    WHERE id = ?
    """, (name, day_of_week, time_start, time_end, room, course_code, slot_id))
    conn.commit()
    conn.close()
    return {
        "id": slot_id,
        "semester_id": existing["semester_id"],
        "name": name,
        "day_of_week": day_of_week,
        "time_start": time_start,
        "time_end": time_end,
        "room": room,
        "course_code": course_code
    }

@app.delete("/api/slots/{slot_id}")
def delete_slot(slot_id: int, user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Pouze administrátor může mazat termíny cvičení.")
    conn = get_db()
    cur = conn.cursor()
    # Check if any protocol is assigned to this slot
    cur.execute("SELECT COUNT(*) FROM protocols WHERE slot_id = ?", (slot_id,))
    if cur.fetchone()[0] > 0:
        conn.close()
        raise HTTPException(status_code=400, detail="Termín nelze smazat, protože obsahuje přiřazené protokoly.")

    cur.execute("DELETE FROM slots WHERE id = ?", (slot_id,))
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Termín byl smazán"}

# ==========================================
# MEASUREMENTS (ÚLOHY)
# ==========================================

@app.get("/api/measurements", response_model=List[MeasurementResponse])
def get_measurements(course_code: Optional[str] = None, semester_type: Optional[str] = None):
    conn = get_db()
    cur = conn.cursor()
    query = "SELECT id, code, number, name, COALESCE(course_code, 'FPRA1') as course_code, semester_type, description, COALESCE(instructions_text, '') as instructions_text FROM measurements WHERE 1=1"
    params = []
    if course_code:
        query += " AND course_code = ?"
        params.append(course_code)
    elif semester_type:
        query += " AND semester_type = ?"
        params.append(semester_type)
    query += " ORDER BY course_code, number ASC"
    cur.execute(query, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

@app.post("/api/measurements", response_model=MeasurementResponse)
def create_measurement(meas: MeasurementCreate, user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Pouze administrátor může spravovat laboratorní úlohy.")
    conn = get_db()
    cur = conn.cursor()
    c_code = meas.course_code or ("FPRA1" if meas.semester_type == "ZS" else ("FPRA2" if meas.semester_type == "LS" else "ZFM2"))
    sem_type = meas.semester_type or ("ZS" if c_code == "FPRA1" else "LS")
    cur.execute("""
    INSERT INTO measurements (code, number, name, course_code, semester_type, description, instructions_text)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (meas.code.strip(), meas.number, meas.name.strip(), c_code, sem_type, meas.description or "", meas.instructions_text or ""))
    meas_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {
        "id": meas_id,
        "code": meas.code,
        "number": meas.number,
        "name": meas.name,
        "course_code": c_code,
        "semester_type": sem_type,
        "description": meas.description,
        "instructions_text": meas.instructions_text or ""
    }

@app.put("/api/measurements/{meas_id}")
def update_measurement(meas_id: int, meas: MeasurementUpdate, user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Pouze administrátor může spravovat laboratorní úlohy.")
    conn = get_db()
    cur = conn.cursor()
    fields = []
    vals = []
    if meas.name is not None:
        fields.append("name = ?")
        vals.append(meas.name.strip())
    if meas.code is not None:
        fields.append("code = ?")
        vals.append(meas.code.strip())
    if meas.number is not None:
        fields.append("number = ?")
        vals.append(meas.number)
    if meas.course_code is not None:
        fields.append("course_code = ?")
        vals.append(meas.course_code.strip())
    if meas.semester_type is not None:
        fields.append("semester_type = ?")
        vals.append(meas.semester_type.strip())
    if meas.description is not None:
        fields.append("description = ?")
        vals.append(meas.description.strip())
    if meas.instructions_text is not None:
        fields.append("instructions_text = ?")
        vals.append(meas.instructions_text.strip())
    if fields:
        vals.append(meas_id)
        cur.execute(f"UPDATE measurements SET {', '.join(fields)} WHERE id = ?", tuple(vals))
        conn.commit()
    conn.close()
    return {"status": "ok"}

@app.post("/api/measurements/{meas_id}/upload-instructions")
async def upload_measurement_instructions(meas_id: int, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Pouze administrátor může nahrávat zadání úloh.")
    contents = await file.read()
    filename = (file.filename or "").lower()
    extracted_text = ""
    if filename.endswith(".pdf"):
        try:
            doc = pymupdf.open(stream=contents, filetype="pdf")
            pages_text = [page.get_text() for page in doc]
            extracted_text = "\n\n".join(pages_text).strip()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Chyba při čtení PDF zadání: {e}")
    else:
        try:
            extracted_text = contents.decode("utf-8").strip()
        except Exception:
            extracted_text = contents.decode("latin2", errors="ignore").strip()

    if not extracted_text:
        raise HTTPException(status_code=400, detail="Ze souboru se nepodařilo vytěžit žádný čitelný text.")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name, number FROM measurements WHERE id = ?", (meas_id,))
    m_row = cur.fetchone()
    task_name = m_row["name"] if m_row else "Laboratorní úloha"
    task_num = m_row["number"] if m_row else 1

    try:
        rubric_text = await generate_task_rubric(extracted_text, task_name, task_num)
    except Exception as e:
        print("Rubric synthesis fallback error:", e)
        rubric_text = extracted_text[:20000]

    cur.execute("UPDATE measurements SET instructions_text = ? WHERE id = ?", (rubric_text, meas_id))
    conn.commit()
    conn.close()
    return {
        "status": "ok",
        "instructions_text": rubric_text,
        "chars_extracted": len(extracted_text),
        "rubric_generated": bool(rubric_text != extracted_text[:20000])
    }

@app.post("/api/measurements/{meas_id}/generate-rubric")
async def generate_measurement_rubric(meas_id: int, req: Optional[dict] = None, user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Pouze administrátor může generovat metodiku úlohy.")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name, number, instructions_text FROM measurements WHERE id = ?", (meas_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Úloha nenalezena")

    input_text = ""
    if req and isinstance(req, dict) and req.get("instructions_text"):
        input_text = req["instructions_text"].strip()
    if not input_text:
        input_text = (row["instructions_text"] or "").strip()

    if not input_text:
        conn.close()
        raise HTTPException(status_code=400, detail="Pro tuto úlohu není k dispozici žádný text zadání k přeformulování.")

    try:
        rubric = await generate_task_rubric(input_text, row["name"], row["number"])
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Chyba při generování rubriky: {e}")

    cur.execute("UPDATE measurements SET instructions_text = ? WHERE id = ?", (rubric, meas_id))
    conn.commit()
    conn.close()
    return {"status": "ok", "instructions_text": rubric}

@app.delete("/api/measurements/{meas_id}")
def delete_measurement(meas_id: int, user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Pouze administrátor může mazat laboratorní úlohy.")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM protocols WHERE measurement_id = ?", (meas_id,))
    if cur.fetchone()[0] > 0:
        conn.close()
        raise HTTPException(status_code=400, detail="Úlohu nelze smazat, protože jsou k ní přiřazeny protokoly.")

    cur.execute("DELETE FROM measurements WHERE id = ?", (meas_id,))
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Úloha byla smazána"}

# ==========================================
# PRESETS (ČASTÉ CHYBY & RYCHLÉ KOMENTÁŘE)
# ==========================================

@app.get("/api/presets", response_model=List[PresetResponse])
def get_presets(type: Optional[str] = None, user: dict = Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    if type:
        cur.execute("""
        SELECT id, user_id, type, category, pts, text FROM presets
        WHERE type = ? AND (user_id IS NULL OR user_id = ?)
        ORDER BY (user_id = ?) DESC, category, pts DESC, id ASC
        """, (type, user["id"], user["id"]))
    else:
        cur.execute("""
        SELECT id, user_id, type, category, pts, text FROM presets
        WHERE user_id IS NULL OR user_id = ?
        ORDER BY type, (user_id = ?) DESC, category, pts DESC, id ASC
        """, (user["id"], user["id"]))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

@app.post("/api/presets", response_model=PresetResponse)
def create_preset(preset: PresetCreate, user: dict = Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    # If user is admin and explicitly requested user_id is None, make global preset; otherwise assign user["id"]
    assigned_user_id = None if (user["role"] == "admin" and preset.user_id is None) else (preset.user_id if user["role"] == "admin" else user["id"])
    cur.execute("""
    INSERT INTO presets (user_id, type, category, pts, text, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (assigned_user_id, preset.type, preset.category, preset.pts, preset.text.strip(), now))
    p_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {
        "id": p_id,
        "user_id": assigned_user_id,
        "type": preset.type,
        "category": preset.category,
        "pts": preset.pts,
        "text": preset.text
    }

@app.delete("/api/presets/{preset_id}")
def delete_preset(preset_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM presets WHERE id = ?", (preset_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Předvolba nenalezena")
    if user["role"] != "admin" and row["user_id"] != user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Nemáte oprávnění smazat tuto předvolbu.")
    cur.execute("DELETE FROM presets WHERE id = ?", (preset_id,))
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Předvolba byla smazána"}

# ==========================================
# PROTOCOLS MANAGEMENT & ROLE RESTRICTIONS
# ==========================================

@app.get("/api/protocols")
def list_protocols(
    semester_id: Optional[int] = None,
    slot_id: Optional[int] = None,
    measurement_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    evaluator_id: Optional[str] = None,
    search: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    conn = get_db()
    cur = conn.cursor()

    query = """
    SELECT 
        p.id, p.semester_id, p.slot_id, p.measurement_id, p.student_name,
        p.status, p.source_filename, p.corrected_filename, p.total_points, p.grade,
        p.evaluator_id, p.graded_at, p.created_at, p.updated_at,
        s.code as semester_code, s.name as semester_name,
        sl.name as slot_name, sl.day_of_week, sl.time_start, sl.time_end, sl.room as slot_room,
        m.code as measurement_code, m.number as measurement_number, m.name as measurement_name,
        u.full_name as evaluator_name
    FROM protocols p
    JOIN semesters s ON p.semester_id = s.id
    JOIN slots sl ON p.slot_id = sl.id
    JOIN measurements m ON p.measurement_id = m.id
    LEFT JOIN users u ON p.evaluator_id = u.id
    WHERE 1=1
    """
    params = []

    # Role restriction and evaluator filtering
    if user["role"] == "assistant":
        if evaluator_id == "me":
            query += " AND p.evaluator_id = ?"
            params.append(user["id"])
        elif evaluator_id == "unassigned":
            query += " AND p.evaluator_id IS NULL"
        elif evaluator_id in ("others", "other"):
            query += " AND 1=0"
        else:
            query += " AND (p.evaluator_id = ? OR p.evaluator_id IS NULL)"
            params.append(user["id"])
    else:
        # Admin or other roles
        if evaluator_id == "me":
            query += " AND p.evaluator_id = ?"
            params.append(user["id"])
        elif evaluator_id in ("others", "other"):
            query += " AND p.evaluator_id != ? AND p.evaluator_id IS NOT NULL"
            params.append(user["id"])
        elif evaluator_id == "unassigned":
            query += " AND p.evaluator_id IS NULL"
        elif evaluator_id and str(evaluator_id).isdigit():
            query += " AND p.evaluator_id = ?"
            params.append(int(evaluator_id))

    if semester_id:
        query += " AND p.semester_id = ?"
        params.append(semester_id)
    if slot_id:
        query += " AND p.slot_id = ?"
        params.append(slot_id)
    if measurement_id:
        query += " AND p.measurement_id = ?"
        params.append(measurement_id)
    if status_filter:
        query += " AND p.status = ?"
        params.append(status_filter)
    if search:
        query += " AND (p.student_name LIKE ? OR p.source_filename LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY p.id DESC"
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

@app.post("/api/protocols/upload")
async def upload_protocol(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    semester_id: int = Form(...),
    slot_id: int = Form(...),
    measurement_id: int = Form(...),
    student_name: Optional[str] = Form(None),
    user: dict = Depends(get_current_user)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Podporovány jsou pouze soubory PDF")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT code FROM semesters WHERE id = ?", (semester_id,))
    sem_row = cur.fetchone()
    cur.execute("SELECT name, day_of_week, time_start, room FROM slots WHERE id = ?", (slot_id,))
    slot_row = cur.fetchone()
    cur.execute("SELECT code, number FROM measurements WHERE id = ?", (measurement_id,))
    meas_row = cur.fetchone()

    if not sem_row or not slot_row or not meas_row:
        conn.close()
        raise HTTPException(status_code=400, detail="Neplatný semestr, termín nebo úloha")

    content = await file.read()

    actual_student_name = student_name.strip() if student_name and student_name.strip() else ""
    if not actual_student_name or actual_student_name.lower() in ("student", "protokol", "null", "undefined"):
        # Auto-detect from PDF text content
        try:
            doc = pymupdf.open(stream=content, filetype="pdf")
            first_page_text = doc[0].get_text() if len(doc) > 0 else ""
            doc.close()
            m_name = re.search(r'(?:Jm[ée]no(?:\s+a\s+\S+)?|Meno(?:\s+a\s+\S+)?|Vypracoval(?:a)?|Autor(?:ka)?|Student(?:ka)?)\s*[:=]\s*([^\n\r,]+)', first_page_text, re.I)
            if not m_name:
                m_name = re.search(r'(?:Jm[ée]no(?:\s+a\s+\S+)?|Meno(?:\s+a\s+\S+)?|Vypracoval(?:a)?|Autor(?:ka)?|Student(?:ka)?)\s*[:=]?\s*\n\s*([^\n\r,]+)', first_page_text, re.I)
            if m_name and m_name.group(1).strip():
                detected = m_name.group(1).strip()
                detected = re.sub(r'[\(\[\{].*?[\)\]\}]', '', detected).strip()
                if len(detected) >= 3 and not any(k in detected.lower() for k in ["úloha", "datum", "skupina", "obor", "mereni"]):
                    actual_student_name = detected
        except Exception as ex:
            print("PDF stream name autodetect warning:", ex)

    if not actual_student_name:
        clean = Path(file.filename).stem
        clean = clean.replace("_opravene", "").replace("_opraveno", "").replace("-opravene", "")
        parts = clean.split("_")
        if len(parts) >= 2 and any(p.lower().startswith("uloha") or p.lower().startswith("u") for p in parts):
            actual_student_name = parts[1] if len(parts) > 2 else parts[0]
        else:
            actual_student_name = clean.replace("_", " ")

    slot_folder = format_slot_folder(day_of_week=slot_row["day_of_week"], time_start=slot_row["time_start"], room=slot_row["room"], raw_name=slot_row["name"])
    source_path = save_source_file(
        file_bytes=content,
        filename=file.filename,
        semester_code=sem_row["code"],
        slot_name=slot_folder,
        measurement_code=meas_row["code"],
        student_name=actual_student_name
    )

    existing_annots = []
    try:
        existing_annots = extract_pdf_annotations(source_path)
    except Exception as e:
        print("Note extraction warning:", e)

    now = datetime.now().isoformat()
    # Automatically assign current user (assistant or admin) as initial evaluator so it immediately appears in "Moje protokoly"
    evaluator_id = user["id"]
    share_token = secrets.token_urlsafe(16)

    cur.execute("""
    INSERT INTO protocols (
        semester_id, slot_id, measurement_id, student_name, status,
        source_filename, source_path, evaluator_id, share_token, created_at, updated_at
    ) VALUES (?, ?, ?, ?, 'new', ?, ?, ?, ?, ?, ?)
    """, (semester_id, slot_id, measurement_id, actual_student_name, file.filename, str(source_path), evaluator_id, share_token, now, now))
    protocol_id = cur.lastrowid

    if existing_annots:
        cur.execute("""
        INSERT INTO annotations (protocol_id, annotations_json, updated_at)
        VALUES (?, ?, ?)
        """, (protocol_id, json.dumps(existing_annots, ensure_ascii=False), now))

    conn.commit()
    conn.close()

    # Automatically trigger background AI analysis if enabled
    if get_ai_setting("auto_analyze_on_upload", "true").lower() in ("true", "1", "yes"):
        background_tasks.add_task(run_background_ai_analysis, protocol_id)

    return {
        "id": protocol_id,
        "student_name": actual_student_name,
        "source_filename": file.filename,
        "extracted_annotations_count": len(existing_annots)
    }

@app.get("/api/protocols/{proto_id}")
def get_protocol_detail(proto_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    SELECT 
        p.*,
        s.code as semester_code, s.name as semester_name,
        sl.name as slot_name, sl.day_of_week, sl.time_start, sl.time_end, sl.room as slot_room,
        m.code as measurement_code, m.number as measurement_number, m.name as measurement_name,
        u.full_name as evaluator_name
    FROM protocols p
    JOIN semesters s ON p.semester_id = s.id
    JOIN slots sl ON p.slot_id = sl.id
    JOIN measurements m ON p.measurement_id = m.id
    LEFT JOIN users u ON p.evaluator_id = u.id
    WHERE p.id = ?
    """, (proto_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Protokol nenalezen")

    proto = dict(row)

    # Check permission
    if user["role"] == "assistant" and proto["evaluator_id"] and proto["evaluator_id"] != user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Nemáte oprávnění k tomuto protokolu")

    cur.execute("SELECT * FROM evaluations WHERE protocol_id = ?", (proto_id,))
    eval_row = cur.fetchone()
    proto["evaluation"] = dict(eval_row) if eval_row else None
    if proto["evaluation"]:
        proto["evaluation"]["deductions"] = json.loads(proto["evaluation"]["deductions_json"])

    cur.execute("SELECT annotations_json FROM annotations WHERE protocol_id = ?", (proto_id,))
    annot_row = cur.fetchone()
    raw_annots = json.loads(annot_row[0]) if annot_row else []
    
    def _norm_rect_coords(r):
        if isinstance(r, (list, tuple)) and len(r) >= 4:
            return [float(r[0]), float(r[1]), float(r[2]), float(r[3])]
        elif isinstance(r, dict):
            x = float(r.get("x", r.get("x0", 0)))
            y = float(r.get("y", r.get("y0", 0)))
            w = float(r["width"]) if "width" in r else (float(r.get("x1", x)) - x)
            h = float(r.get("height", 0)) if "height" in r else (float(r.get("y1", y)) - y)
            return [x, y, x + w, y + h]
        return None

    normalized_annots = []
    for a in raw_annots:
        if isinstance(a, dict):
            if "rect" in a and a["rect"]:
                nr = _norm_rect_coords(a["rect"])
                if nr:
                    a["rect"] = nr
            if "rects" in a and a["rects"]:
                a["rects"] = [_norm_rect_coords(r) for r in a["rects"] if _norm_rect_coords(r)]
            normalized_annots.append(a)
    proto["annotations"] = normalized_annots

    # If database annotations are empty, check if PDF file contains native annotations (e.g. Acrobat)
    if not proto["annotations"]:
        pdf_to_check = proto.get("corrected_path") or proto.get("source_path")
        if pdf_to_check and Path(pdf_to_check).exists():
            try:
                extracted = extract_pdf_annotations(pdf_to_check)
                if extracted:
                    proto["annotations"] = extracted
                    cur.execute("""
                    INSERT INTO annotations (protocol_id, annotations_json, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(protocol_id) DO UPDATE SET
                        annotations_json = excluded.annotations_json,
                        updated_at = excluded.updated_at
                    """, (proto_id, json.dumps(extracted, ensure_ascii=False), datetime.now().isoformat()))
                    conn.commit()
            except Exception as e:
                print("Warning: could not extract native PDF annotations:", e)

    proto["ai_proposals"] = json.loads(proto["ai_proposals_json"]) if proto.get("ai_proposals_json") else None
    proto["ai_status"] = proto.get("ai_status") or ("ready" if proto.get("ai_proposals") else "idle")

    conn.close()
    return proto

@app.delete("/api/protocols/{proto_id}")
def delete_protocol(proto_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT source_path, corrected_path, evaluator_id FROM protocols WHERE id = ?", (proto_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Protokol nenalezen")

        if user["role"] == "assistant" and row["evaluator_id"] and row["evaluator_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Nemáte oprávnění smazat tento protokol")

        cur.execute("DELETE FROM evaluations WHERE protocol_id = ?", (proto_id,))
        cur.execute("DELETE FROM annotations WHERE protocol_id = ?", (proto_id,))
        cur.execute("DELETE FROM protocols WHERE id = ?", (proto_id,))
        conn.commit()
    finally:
        conn.close()

    for p in [row["source_path"], row["corrected_path"]]:
        if p and Path(p).exists():
            try:
                Path(p).unlink()
            except Exception:
                pass

    return {"status": "ok", "message": "Protokol byl smazán"}

# ==========================================
# PDF STREAMING & FILE SERVING
# ==========================================

@app.get("/api/protocols/{proto_id}/pdf/source")
def get_source_pdf(proto_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT source_path, source_filename FROM protocols WHERE id = ?", (proto_id,))
    row = cur.fetchone()
    conn.close()

    if not row or not Path(row["source_path"]).exists():
        raise HTTPException(status_code=404, detail="Soubor PDF nenalezen")

    return FileResponse(
        path=row["source_path"],
        media_type="application/pdf",
        filename=row["source_filename"]
    )

@app.get("/api/protocols/{proto_id}/pdf/corrected")
def get_corrected_pdf(proto_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT corrected_path, corrected_filename FROM protocols WHERE id = ?", (proto_id,))
    row = cur.fetchone()
    conn.close()

    if not row or not row["corrected_path"] or not Path(row["corrected_path"]).exists():
        raise HTTPException(status_code=404, detail="Opravené PDF dosud nebylo vytvořeno")

    return FileResponse(
        path=row["corrected_path"],
        media_type="application/pdf",
        filename=row["corrected_filename"] or "opravene.pdf"
    )

@app.get("/api/protocols/{proto_id}/export/bodovani.txt")
def download_bodovani(proto_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    SELECT e.raw_output_2, p.student_name, m.code as measurement_code
    FROM evaluations e
    JOIN protocols p ON e.protocol_id = p.id
    JOIN measurements m ON p.measurement_id = m.id
    WHERE e.protocol_id = ?
    """, (proto_id,))
    row = cur.fetchone()
    conn.close()

    if not row or not row["raw_output_2"]:
        raise HTTPException(status_code=404, detail="Hodnocení dosud nebylo uloženo")

    safe_name = slugify(row['student_name'])
    filename = f"bodovani_{safe_name}_{row['measurement_code']}.txt"
    return Response(
        content=row["raw_output_2"],
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

# ==========================================
# SAVING EVALUATION & BURNING CORRECTIONS
# ==========================================

@app.post("/api/protocols/{proto_id}/annotations")
def save_annotations(proto_id: int, req: AnnotationSaveRequest, user: dict = Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    annot_json = json.dumps(req.annotations, ensure_ascii=False)

    cur.execute("""
    INSERT INTO annotations (protocol_id, annotations_json, updated_at)
    VALUES (?, ?, ?)
    ON CONFLICT(protocol_id) DO UPDATE SET
        annotations_json = excluded.annotations_json,
        updated_at = excluded.updated_at
    """, (proto_id, annot_json, now))

    cur.execute("UPDATE protocols SET status = 'in_progress', evaluator_id = COALESCE(evaluator_id, ?), updated_at = ? WHERE id = ? AND status = 'new'", (user["id"], now, proto_id))
    conn.commit()
    conn.close()
    return {"status": "ok", "count": len(req.annotations)}

@app.post("/api/protocols/{proto_id}/evaluation")
def save_evaluation(proto_id: int, req: EvaluationSaveRequest, request: Request, user: dict = Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    SELECT p.*, s.code as semester_code, sl.name as slot_name, sl.day_of_week, sl.time_start, sl.room as slot_room, m.code as measurement_code
    FROM protocols p
    JOIN semesters s ON p.semester_id = s.id
    JOIN slots sl ON p.slot_id = sl.id
    JOIN measurements m ON p.measurement_id = m.id
    WHERE p.id = ?
    """, (proto_id,))
    proto_row = cur.fetchone()
    if not proto_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Protokol nenalezen")
    proto = dict(proto_row)

    now = datetime.now().isoformat()
    deductions_raw = [d.dict() for d in req.deductions]
    deductions_json_str = json.dumps(deductions_raw, ensure_ascii=False)

    clean_override = req.manual_grade_override if (isinstance(req.manual_grade_override, str) and req.manual_grade_override.upper() in ['A', 'B', 'C', 'D', 'E', 'F']) else None
    grade_val = clean_override or (req.grade if req.grade and req.grade in ['A', 'B', 'C', 'D', 'E', 'F'] else calculate_grade_mark(req.total_points))

    cur.execute("""
    INSERT INTO evaluations (
        protocol_id, vysledky_score, diskuze_score, format_score, chyby_score,
        total_points, grade, manual_grade_override, deductions_json,
        raw_output_1, raw_output_2, general_comment, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(protocol_id) DO UPDATE SET
        vysledky_score = excluded.vysledky_score,
        diskuze_score = excluded.diskuze_score,
        format_score = excluded.format_score,
        chyby_score = excluded.chyby_score,
        total_points = excluded.total_points,
        grade = excluded.grade,
        manual_grade_override = excluded.manual_grade_override,
        deductions_json = excluded.deductions_json,
        raw_output_1 = excluded.raw_output_1,
        raw_output_2 = excluded.raw_output_2,
        general_comment = excluded.general_comment,
        updated_at = excluded.updated_at
    """, (
        proto_id, req.vysledky_score, req.diskuze_score, req.format_score, req.chyby_score,
        req.total_points, grade_val, clean_override, deductions_json_str,
        req.raw_output_1, req.raw_output_2, req.general_comment or "", now
    ))

    slot_folder = format_slot_folder(day_of_week=proto["day_of_week"], time_start=proto["time_start"], room=proto["slot_room"], raw_name=proto["slot_name"])

    save_bodovani_file(
        content=req.raw_output_2,
        semester_code=proto["semester_code"],
        slot_name=slot_folder,
        measurement_code=proto["measurement_code"],
        student_name=proto["student_name"]
    )

    corrected_filename = Path(proto["source_filename"]).stem + "_opravene.pdf"
    corrected_path_str = None

    if req.annotations is not None:
        annot_json = json.dumps(req.annotations, ensure_ascii=False)
        cur.execute("""
        INSERT INTO annotations (protocol_id, annotations_json, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(protocol_id) DO UPDATE SET
            annotations_json = excluded.annotations_json,
            updated_at = excluded.updated_at
        """, (proto_id, annot_json, now))

    if req.burn_to_pdf:
        if req.annotations is not None:
            annots = req.annotations
        else:
            cur.execute("SELECT annotations_json FROM annotations WHERE protocol_id = ?", (proto_id,))
            annot_row = cur.fetchone()
            annots = json.loads(annot_row[0]) if annot_row else []

        eval_summary = {
            "total_points": req.total_points,
            "grade": grade_val or calculate_grade_mark(req.total_points),
            "vysledky_score": req.vysledky_score,
            "diskuze_score": req.diskuze_score,
            "format_score": req.format_score,
            "chyby_score": req.chyby_score,
            "deductions": deductions_raw,
            "general_comment": req.general_comment or ""
        }

        source_path = Path(proto["source_path"])
        if not source_path.exists():
            try:
                source_path.parent.mkdir(parents=True, exist_ok=True)
                fb_doc = pymupdf.open()
                fb_page = fb_doc.new_page(width=595, height=842)
                fb_page.insert_text((50, 50), f"Protokol: {proto.get('student_name', 'Student')}\nUloha: {proto.get('measurement_code', 'Uloha')}")
                fb_doc.save(str(source_path))
                fb_doc.close()
            except Exception as ex:
                print("Could not recreate missing source PDF:", ex)

        share_tok = proto.get("share_token")
        if not share_tok:
            share_tok = secrets.token_urlsafe(16)
            cur.execute("UPDATE protocols SET share_token = ? WHERE id = ?", (share_tok, proto_id))
            conn.commit()

        base_url = str(request.base_url).rstrip("/")
        try:
            cur.execute("SELECT value FROM app_settings WHERE key = 'app_public_url'")
            setting_row = cur.fetchone()
            if setting_row and setting_row[0] and setting_row[0].strip():
                base_url = setting_row[0].strip().rstrip("/")
        except Exception:
            pass

        try:
            burned_bytes = burn_annotations_to_pdf(
                source_pdf_path=source_path,
                annotations_list=annots,
                evaluation=eval_summary,
                evaluator_name=user["full_name"],
                share_token=share_tok,
                base_url=base_url,
                student_name=proto.get("student_name"),
                task_code=proto.get("measurement_code"),
                general_comment=req.general_comment
            )
            saved_path = save_corrected_file(
                file_bytes=burned_bytes,
                filename=corrected_filename,
                semester_code=proto["semester_code"],
                slot_name=slot_folder,
                measurement_code=proto["measurement_code"],
                student_name=proto["student_name"]
            )
            corrected_path_str = str(saved_path)
        except Exception as e:
            print("PDF burning error:", e)

    target_status = "revision" if req.status == "revision" else ("graded" if req.burn_to_pdf else "in_progress")

    cur.execute("""
    UPDATE protocols SET
        status = ?,
        total_points = ?,
        grade = ?,
        evaluator_id = ?,
        corrected_filename = ?,
        corrected_path = COALESCE(?, corrected_path),
        graded_at = ?,
        updated_at = ?
    WHERE id = ?
    """, (
        target_status, req.total_points, req.grade, user["id"],
        corrected_filename, corrected_path_str, now, now, proto_id
    ))

    conn.commit()
    conn.close()

    return {
        "status": "ok",
        "protocol_id": proto_id,
        "total_points": req.total_points,
        "grade": req.grade,
        "protocol_status": target_status,
        "corrected_pdf_created": corrected_path_str is not None
    }

@app.post("/api/protocols/{proto_id}/autosave")
def autosave_protocol(proto_id: int, req: AutosaveRequest, user: dict = Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM protocols WHERE id = ?", (proto_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Protokol nenalezen")

    now = datetime.now().isoformat()

    if req.annotations is not None:
        annot_json = json.dumps(req.annotations, ensure_ascii=False)
        cur.execute("""
        INSERT INTO annotations (protocol_id, annotations_json, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(protocol_id) DO UPDATE SET
            annotations_json = excluded.annotations_json,
            updated_at = excluded.updated_at
        """, (proto_id, annot_json, now))

    if req.ai_proposals is not None:
        cur.execute(
            "UPDATE protocols SET ai_proposals_json = ? WHERE id = ?",
            (json.dumps(req.ai_proposals, ensure_ascii=False), proto_id)
        )

    if req.evaluation is not None:
        ev = req.evaluation
        deductions_raw = [d.dict() for d in (ev.deductions or [])]
        deductions_json_str = json.dumps(deductions_raw, ensure_ascii=False)
        clean_override = ev.manual_grade_override if (isinstance(ev.manual_grade_override, str) and ev.manual_grade_override.upper() in ['A', 'B', 'C', 'D', 'E', 'F']) else None
        tot_pts = ev.total_points if ev.total_points is not None else 10.0
        grade_val = clean_override or (ev.grade if ev.grade and ev.grade in ['A', 'B', 'C', 'D', 'E', 'F'] else calculate_grade_mark(tot_pts))
        gen_comm_val = ev.general_comment if (ev and ev.general_comment is not None) else (req.general_comment or "")
        cur.execute("""
        INSERT INTO evaluations (
            protocol_id, vysledky_score, diskuze_score, format_score, chyby_score,
            total_points, grade, manual_grade_override, deductions_json,
            raw_output_1, raw_output_2, general_comment, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(protocol_id) DO UPDATE SET
            vysledky_score = excluded.vysledky_score,
            diskuze_score = excluded.diskuze_score,
            format_score = excluded.format_score,
            chyby_score = excluded.chyby_score,
            total_points = excluded.total_points,
            grade = excluded.grade,
            manual_grade_override = excluded.manual_grade_override,
            deductions_json = excluded.deductions_json,
            raw_output_1 = excluded.raw_output_1,
            raw_output_2 = excluded.raw_output_2,
            general_comment = excluded.general_comment,
            updated_at = excluded.updated_at
        """, (
            proto_id, ev.vysledky_score or 3.0, ev.diskuze_score or 3.0, ev.format_score or 2.0, ev.chyby_score or 2.0,
            tot_pts, grade_val, clean_override, deductions_json_str,
            ev.raw_output_1 or "", ev.raw_output_2 or "", gen_comm_val or "", now
        ))

    cur.execute("""
    UPDATE protocols SET
        status = CASE WHEN status = 'new' THEN 'in_progress' ELSE status END,
        evaluator_id = COALESCE(evaluator_id, ?),
        updated_at = ?
    WHERE id = ?
    """, (user["id"], now, proto_id))

    conn.commit()
    conn.close()
    return {"status": "ok", "saved_at": now}

# Assign evaluator to protocol
@app.put("/api/protocols/{proto_id}/assign")
def assign_protocol(proto_id: int, req: ProtocolAssignRequest, user: dict = Depends(get_current_user)):
    # Assistant can only assign protocol to themselves or unassign
    if user["role"] == "assistant":
        if req.evaluator_id is not None and req.evaluator_id != user["id"]:
            raise HTTPException(status_code=403, detail="Asistent může protokol přiřadit pouze sobě nebo zrušit své přiřazení.")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, evaluator_id FROM protocols WHERE id = ?", (proto_id,))
    existing = cur.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Protokol nenalezen")

    if user["role"] == "assistant" and existing["evaluator_id"] and existing["evaluator_id"] != user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Nemáte oprávnění měnit přiřazení cizího protokolu.")

    eval_name = None
    if req.evaluator_id:
        cur.execute("SELECT full_name FROM users WHERE id = ?", (req.evaluator_id,))
        urow = cur.fetchone()
        if not urow:
            conn.close()
            raise HTTPException(status_code=400, detail="Uživatel nenalezen")
        eval_name = urow[0]

    now = datetime.now().isoformat()
    cur.execute("UPDATE protocols SET evaluator_id = ?, updated_at = ? WHERE id = ?", (req.evaluator_id, now, proto_id))
    conn.commit()
    conn.close()
    return {"status": "ok", "evaluator_id": req.evaluator_id, "evaluator_name": eval_name}

# Update Protocol Metadata (Student Name, Semester, Slot, Measurement)
@app.put("/api/protocols/{proto_id}/metadata")
def update_protocol_metadata(proto_id: int, req: ProtocolMetadataUpdateRequest, user: dict = Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM protocols WHERE id = ?", (proto_id,))
    proto = cur.fetchone()
    if not proto:
        conn.close()
        raise HTTPException(status_code=404, detail="Protokol nenalezen")

    # Verify target metadata exist
    cur.execute("SELECT code FROM semesters WHERE id = ?", (req.semester_id,))
    sem_row = cur.fetchone()
    cur.execute("SELECT name, day_of_week, time_start, room FROM slots WHERE id = ?", (req.slot_id,))
    slot_row = cur.fetchone()
    cur.execute("SELECT code FROM measurements WHERE id = ?", (req.measurement_id,))
    meas_row = cur.fetchone()

    if not sem_row or not slot_row or not meas_row:
        conn.close()
        raise HTTPException(status_code=400, detail="Neplatný semestr, termín nebo úloha")

    student_name = req.student_name.strip()
    if not student_name:
        conn.close()
        raise HTTPException(status_code=400, detail="Jméno studenta nesmí být prázdné")

    now = datetime.now().isoformat()
    cur.execute("""
    UPDATE protocols SET
        student_name = ?,
        semester_id = ?,
        slot_id = ?,
        measurement_id = ?,
        updated_at = ?
    WHERE id = ?
    """, (student_name, req.semester_id, req.slot_id, req.measurement_id, now, proto_id))
    conn.commit()
    conn.close()
    return {
        "status": "ok",
        "message": "Metadata protokolu byla úspěšně aktualizována",
        "id": proto_id,
        "student_name": student_name,
        "semester_id": req.semester_id,
        "slot_id": req.slot_id,
        "measurement_id": req.measurement_id
    }

# Bulk Delete Protocols Endpoint
@app.post("/api/protocols/bulk-delete")
def bulk_delete_protocols(req: BulkDeleteRequest, user: dict = Depends(get_current_user)):
    if not req.protocol_ids:
        return {"status": "ok", "deleted_count": 0}
    
    conn = get_db()
    deleted_count = 0
    try:
        cur = conn.cursor()
        for proto_id in req.protocol_ids:
            cur.execute("SELECT id, source_path, corrected_path, evaluator_id FROM protocols WHERE id = ?", (proto_id,))
            row = cur.fetchone()
            if not row:
                continue
            # Assistant can only delete their own protocols
            if user["role"] == "assistant" and row["evaluator_id"] and row["evaluator_id"] != user["id"]:
                continue
            
            cur.execute("DELETE FROM evaluations WHERE protocol_id = ?", (proto_id,))
            cur.execute("DELETE FROM annotations WHERE protocol_id = ?", (proto_id,))
            cur.execute("DELETE FROM protocols WHERE id = ?", (proto_id,))
            deleted_count += 1
            
            for p in [row["source_path"], row["corrected_path"]]:
                if p and Path(p).exists():
                    try:
                        Path(p).unlink()
                    except Exception:
                        pass
        conn.commit()
    finally:
        conn.close()
        
    return {"status": "ok", "deleted_count": deleted_count}

# Bulk Update Protocols Metadata Endpoint
@app.post("/api/protocols/bulk-update")
def bulk_update_protocols(req: BulkUpdateRequest, user: dict = Depends(get_current_user)):
    if not req.protocol_ids:
        return {"status": "ok", "updated_count": 0}
    
    conn = get_db()
    updated_count = 0
    now = datetime.now().isoformat()
    try:
        cur = conn.cursor()
        for proto_id in req.protocol_ids:
            cur.execute("SELECT id, evaluator_id FROM protocols WHERE id = ?", (proto_id,))
            row = cur.fetchone()
            if not row:
                continue
            # Assistant cannot change protocols assigned to other assistants
            if user["role"] == "assistant" and row["evaluator_id"] and row["evaluator_id"] != user["id"]:
                continue
            
            updates = ["updated_at = ?"]
            params = [now]
            
            if req.semester_id is not None:
                updates.append("semester_id = ?")
                params.append(req.semester_id)
            if req.slot_id is not None:
                updates.append("slot_id = ?")
                params.append(req.slot_id)
            if req.measurement_id is not None:
                updates.append("measurement_id = ?")
                params.append(req.measurement_id)
            if req.evaluator_id is not None:
                target_eval = None if req.evaluator_id <= 0 else req.evaluator_id
                if user["role"] == "assistant" and target_eval is not None and target_eval != user["id"]:
                    pass
                else:
                    updates.append("evaluator_id = ?")
                    params.append(target_eval)
            
            params.append(proto_id)
            cur.execute(f"UPDATE protocols SET {', '.join(updates)} WHERE id = ?", params)
            updated_count += 1
            
        conn.commit()
    finally:
        conn.close()
        
    return {"status": "ok", "updated_count": updated_count}

# Autodetect Protocol Metadata Endpoint
@app.post("/api/protocols/autodetect", response_model=AutodetectResponse)
async def autodetect_protocol_metadata(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Lze analyzovat pouze soubory PDF")
    
    content = await file.read()
    try:
        doc = pymupdf.open(stream=content, filetype="pdf")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Nelze otevřít PDF soubor: {str(e)}")

    page_text = doc[0].get_text() if len(doc) > 0 else ""
    preview = page_text[:1200]
    filename = file.filename

    conn = get_db()
    cur = conn.cursor()

    # 1. Course Code
    course_code = "FPRA1"
    if re.search(r'praktik(?:um|a)\s*1\b|FPRA1\b', page_text, re.I) or "FPRA1" in filename:
        course_code = "FPRA1"
    elif re.search(r'praktik(?:um|a)\s*2\b|FPRA2\b', page_text, re.I) or "FPRA2" in filename:
        course_code = "FPRA2"
    elif re.search(r'základní fyzikální měření 2|ZFM2\b', page_text, re.I) or "ZFM2" in filename:
        course_code = "ZFM2"

    # 2. Student Name
    student_name = ""
    m_name = re.search(r'(?:Jm[ée]no(?:\s+a\s+\S+)?|Meno(?:\s+a\s+\S+)?|Vypracoval(?:a)?|Autor(?:ka)?|Student(?:ka)?)\s*[:=]\s*([^\n\r,]+)', page_text, re.I)
    if not m_name:
        m_name = re.search(r'(?:Jm[ée]no(?:\s+a\s+\S+)?|Meno(?:\s+a\s+\S+)?|Vypracoval(?:a)?|Autor(?:ka)?|Student(?:ka)?)\s*[:=]?\s*\n\s*([^\n\r,]+)', page_text, re.I)
    if m_name:
        student_name = m_name.group(1).strip()
    else:
        clean = Path(filename).stem
        for s in ['_opravene', '_opraveno', '-opravene', 'FPRA1_', 'FPRA2_', 'ZFM2_']:
            clean = clean.replace(s, '')
        parts = clean.split('_')
        student_name = parts[-1].capitalize() if parts else "Student"

    # 3. Task Number & Measurement ID
    measurement_id = None
    task_number = None

    cur.execute("SELECT id, number, name FROM measurements WHERE course_code = ? ORDER BY number", (course_code,))
    course_meas = cur.fetchall()

    # Check filename first (e.g. FPRA1_1_..., uloha1, 06 Kalorimetria...)
    m_fn = re.search(r'(?:FPRA[12]|ZFM2)[_\s]+(\d{1,2})(?:[_\s\-.]|$)', filename, re.I)
    if not m_fn:
        m_fn = re.search(r'(?:uloha|meranie)[_\s]*(\d{1,2})(?:[_\s\-.]|$)', filename, re.I)
    if not m_fn:
        m_fn = re.search(r'^(\d{1,2})[_\s\-.]', filename)
    if m_fn:
        fn_num = int(m_fn.group(1))
        for m in course_meas:
            if m["number"] == fn_num:
                task_number = fn_num
                measurement_id = m["id"]
                break

    # If not found or to corroborate, check title/content keyword matching
    if task_number is None or measurement_id is None:
        for m in course_meas:
            m_name_words = [w.lower() for w in re.split(r'[\s\-,\.]+', m["name"]) if len(w) >= 5]
            matching_words = [w for w in m_name_words if w[:5] in page_text[:1000].lower()]
            if len(matching_words) >= 2 or (len(m_name_words) == 1 and len(matching_words) == 1):
                task_number = m["number"]
                measurement_id = m["id"]
                break

    # If still not found, check regex in text
    if task_number is None:
        m_task = re.search(r'(?:Úloha|Meranie|Uloha)\s*(?:č\.?)?\s*(\d+)', page_text, re.I)
        if m_task:
            task_number = int(m_task.group(1))
        else:
            m_task2 = re.search(r'(?:^|\n)\s*(\d{1,2})\s*-\s*[A-Z]', page_text)
            if m_task2:
                task_number = int(m_task2.group(1))

        if task_number is not None:
            for m in course_meas:
                if m["number"] == task_number:
                    measurement_id = m["id"]
                    break

    # 4. Slot ID
    slot_id = None
    day_map = {
        'po': 'Pondělí', 'pondělí': 'Pondělí', 'pondelok': 'Pondělí',
        'út': 'Úterý', 'ut': 'Úterý', 'úterý': 'Úterý', 'utorok': 'Úterý',
        'st': 'Středa', 'středa': 'Středa', 'streda': 'Středa',
        'čt': 'Čtvrtek', 'ct': 'Čtvrtek', 'čtvrtek': 'Čtvrtek', 'štvrtok': 'Čtvrtek',
        'pá': 'Pátek', 'pa': 'Pátek', 'pátek': 'Pátek', 'piatok': 'Pátek'
    }
    m_day = re.search(r'\b(pondělí|pondelok|úterý|utorok|středa|streda|čtvrtek|štvrtok|pátek|piatok|po|út|st|čt|pá)\b', page_text[:800], re.I)
    m_time = re.search(r'\b(\d{1,2}[:.]\d{2})\b', page_text[:800])
    detected_day = day_map.get(m_day.group(1).lower()) if m_day else None
    detected_time = m_time.group(1).replace('.', ':') if m_time else None

    if detected_day:
        cur.execute("SELECT id, time_start FROM slots WHERE course_code = ? AND day_of_week = ?", (course_code, detected_day))
        rows = cur.fetchall()
        if rows:
            slot_id = rows[0]["id"]
            if detected_time and len(rows) > 1:
                for r in rows:
                    if detected_time in str(r["time_start"] or ""):
                        slot_id = r["id"]
                        break
        else:
            cur.execute("SELECT id FROM slots WHERE day_of_week = ? LIMIT 1", (detected_day,))
            r = cur.fetchone()
            if r:
                slot_id = r["id"]

    # 5. Semester ID
    cur.execute("SELECT id FROM semesters ORDER BY id DESC LIMIT 1")
    sem_row = cur.fetchone()
    semester_id = sem_row["id"] if sem_row else 1

    conn.close()

    return AutodetectResponse(
        student_name=student_name,
        course_code=course_code,
        task_number=task_number,
        measurement_number=task_number,
        measurement_id=measurement_id,
        slot_id=slot_id,
        semester_id=semester_id,
        raw_text_preview=preview
    )

# AI Assisted Protocol Analysis
@app.post("/api/protocols/{proto_id}/ai-analyze")
async def ai_analyze_protocol_endpoint(
    proto_id: int, 
    mode: str = "merge",
    language: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    try:
        custom_key = user.get("custom_gemini_api_key")
        result = await analyze_protocol(proto_id, custom_key=custom_key, language=language)
        
        # Persist to database so proposals are never lost on reload
        conn = get_db()
        cur = conn.cursor()
        
        # If mode == 'merge', combine with existing unapproved proposals if any
        if mode == "merge":
            cur.execute("SELECT ai_proposals_json FROM protocols WHERE id = ?", (proto_id,))
            existing_row = cur.fetchone()
            if existing_row and existing_row["ai_proposals_json"]:
                try:
                    existing_data = json.loads(existing_row["ai_proposals_json"])
                    result = merge_ai_results(existing_data, result)
                except Exception as ex:
                    print("Error merging AI proposals:", ex)

        dumped = result.model_dump() if hasattr(result, "model_dump") else result.dict()
        cur.execute(
            "UPDATE protocols SET ai_proposals_json = ?, ai_status = 'ready' WHERE id = ?",
            (json.dumps(dumped, ensure_ascii=False), proto_id)
        )
        conn.commit()
        conn.close()

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def calculate_grade_mark(points: float, manual_override: Optional[str] = None) -> str:
    if manual_override:
        return manual_override
    if points >= 9.00 - 1e-6:
        return "A"
    if points >= 8.00 - 1e-6:
        return "B"
    if points >= 6.00 - 1e-6:
        return "C"
    if points >= 4.00 - 1e-6:
        return "D"
    if points >= 2.00 - 1e-6:
        return "E"
    return "F"

@app.post("/api/protocols/{proto_id}/ai-proposals/action")
def ai_proposal_action(
    proto_id: int, 
    req: AIProposalActionRequest, 
    user: dict = Depends(get_current_user)
):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, ai_proposals_json, evaluator_id FROM protocols WHERE id = ?", (proto_id,))
        p_row = cur.fetchone()
        if not p_row:
            raise HTTPException(status_code=404, detail="Protokol nenalezen")

        ai_proposals = json.loads(p_row["ai_proposals_json"]) if p_row["ai_proposals_json"] else {"deductions": [], "annotations": []}
        if not isinstance(ai_proposals, dict):
            ai_proposals = {"deductions": [], "annotations": []}
        if "deductions" not in ai_proposals:
            ai_proposals["deductions"] = []
        if "annotations" not in ai_proposals:
            ai_proposals["annotations"] = []

        now = datetime.now().isoformat()
        action = req.action
        target_id = req.proposal_id
        created_annotation = None
        created_annotations = []
        deduction_added = None
        deductions_added = []

        if action == "approve_annotation":
            found_idx = -1
            found_item = None
            tid = str(target_id or "")
            for idx, a in enumerate(ai_proposals["annotations"]):
                p_id = str(a.get("proposal_id") or "")
                if (p_id and p_id == tid) or f"annot_{proto_id}_{idx+1}" == tid or f"ai_prop_{idx}" == tid or f"annot_{idx}" == tid:
                    found_idx = idx
                    found_item = a
                    break

            if found_item:
                ai_proposals["annotations"].pop(found_idx)
                raw_rect = found_item.get("rect")
                raw_point = found_item.get("point")
                created_annotation = req.annotation_data or {
                    "id": f"annot_{proto_id}_{int(time.time()*1000)}",
                    "page": int(found_item.get("page", 1)),
                    "type": "highlight",
                    "rect": raw_rect,
                    "rects": [raw_rect] if raw_rect else [],
                    "point": raw_point or ([raw_rect[0], raw_rect[1]] if raw_rect else [80, 80]),
                    "content": found_item.get("comment", ""),
                    "author": user.get("full_name") or "Vyučující",
                    "color": "#ef4444",
                    "created_at": now
                }
                cur.execute("SELECT annotations_json FROM annotations WHERE protocol_id = ?", (proto_id,))
                annot_row = cur.fetchone()
                existing_annots = json.loads(annot_row[0]) if annot_row and annot_row[0] else []
                # Check duplicate by ID
                if not any(ea.get("id") == created_annotation.get("id") for ea in existing_annots):
                    existing_annots.append(created_annotation)

                cur.execute("""
                INSERT INTO annotations (protocol_id, annotations_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(protocol_id) DO UPDATE SET
                    annotations_json = excluded.annotations_json,
                    updated_at = excluded.updated_at
                """, (proto_id, json.dumps(existing_annots, ensure_ascii=False), now))

        elif action == "reject_annotation":
            found_idx = -1
            tid = str(target_id or "")
            for idx, a in enumerate(ai_proposals["annotations"]):
                p_id = str(a.get("proposal_id") or "")
                if (p_id and p_id == tid) or f"annot_{proto_id}_{idx+1}" == tid or f"ai_prop_{idx}" == tid or f"annot_{idx}" == tid:
                    found_idx = idx
                    break
            if found_idx != -1:
                ai_proposals["annotations"].pop(found_idx)

        elif action == "approve_deduction":
            found_idx = -1
            found_d = None
            tid = str(target_id or "")
            for idx, d in enumerate(ai_proposals["deductions"]):
                p_id = str(d.get("proposal_id") or "")
                if (p_id and p_id == tid) or f"ded_{proto_id}_{idx+1}" == tid or f"ded_{idx}" == tid:
                    found_idx = idx
                    found_d = d
                    break

            if found_d:
                ai_proposals["deductions"].pop(found_idx)
                pts = float(found_d.get("pts", found_d.get("points", 0.25)))
                cat = found_d.get("category", "format")
                reason = found_d.get("reason", "Chyba v protokolu")
                deduction_added = {"category": cat, "pts": pts, "reason": reason}

                cur.execute("SELECT * FROM evaluations WHERE protocol_id = ?", (proto_id,))
                eval_row = cur.fetchone()
                existing_deds = json.loads(eval_row["deductions_json"]) if eval_row and eval_row["deductions_json"] else []
                existing_deds.append(deduction_added)

                v_score = max(0.0, 3.0 - sum(d["pts"] for d in existing_deds if d.get("category") == "vysledky"))
                d_score = max(0.0, 3.0 - sum(d["pts"] for d in existing_deds if d.get("category") == "diskuze"))
                f_score = max(0.0, 2.0 - sum(d["pts"] for d in existing_deds if d.get("category") == "format"))
                c_score = max(0.0, 2.0 - sum(d["pts"] for d in existing_deds if d.get("category") == "chyby"))
                tot = round(v_score + d_score + f_score + c_score, 3)
                grade_mark = calculate_grade_mark(tot)

                cur.execute("""
                INSERT INTO evaluations (
                    protocol_id, vysledky_score, diskuze_score, format_score, chyby_score,
                    total_points, grade, deductions_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(protocol_id) DO UPDATE SET
                    vysledky_score = excluded.vysledky_score,
                    diskuze_score = excluded.diskuze_score,
                    format_score = excluded.format_score,
                    chyby_score = excluded.chyby_score,
                    total_points = excluded.total_points,
                    grade = excluded.grade,
                    deductions_json = excluded.deductions_json,
                    updated_at = excluded.updated_at
                """, (proto_id, v_score, d_score, f_score, c_score, tot, grade_mark, json.dumps(existing_deds, ensure_ascii=False), now))

                cur.execute("UPDATE protocols SET total_points = ?, grade = ?, updated_at = ? WHERE id = ?",
                            (tot, grade_mark, now, proto_id))

        elif action == "reject_deduction":
            found_idx = -1
            for idx, d in enumerate(ai_proposals["deductions"]):
                p_id = d.get("proposal_id") or f"ded_{proto_id}_{idx+1}"
                if p_id == target_id or f"ded_{idx}" == target_id:
                    found_idx = idx
                    break
            if found_idx != -1:
                ai_proposals["deductions"].pop(found_idx)

        elif action == "approve_all_annotations":
            cur.execute("SELECT annotations_json FROM annotations WHERE protocol_id = ?", (proto_id,))
            annot_row = cur.fetchone()
            existing_annots = json.loads(annot_row[0]) if annot_row and annot_row[0] else []
            for idx, a in enumerate(ai_proposals["annotations"]):
                raw_rect = a.get("rect")
                raw_point = a.get("point")
                c_ann = {
                    "id": f"annot_{proto_id}_{int(time.time()*1000)}_{idx}",
                    "page": int(a.get("page", 1)),
                    "type": "highlight",
                    "rect": raw_rect,
                    "rects": [raw_rect] if raw_rect else [],
                    "point": raw_point or ([raw_rect[0], raw_rect[1]] if raw_rect else [80, 80]),
                    "content": a.get("comment", ""),
                    "author": user.get("full_name") or "Vyučující",
                    "color": "#ef4444",
                    "created_at": now
                }
                existing_annots.append(c_ann)
                created_annotations.append(c_ann)

            ai_proposals["annotations"] = []
            cur.execute("""
            INSERT INTO annotations (protocol_id, annotations_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(protocol_id) DO UPDATE SET
                annotations_json = excluded.annotations_json,
                updated_at = excluded.updated_at
            """, (proto_id, json.dumps(existing_annots, ensure_ascii=False), now))

        elif action == "approve_all_deductions":
            cur.execute("SELECT * FROM evaluations WHERE protocol_id = ?", (proto_id,))
            eval_row = cur.fetchone()
            existing_deds = json.loads(eval_row["deductions_json"]) if eval_row and eval_row["deductions_json"] else []

            for d in ai_proposals["deductions"]:
                pts = float(d.get("pts", d.get("points", 0.25)))
                cat = d.get("category", "format")
                reason = d.get("reason", "Chyba v protokolu")
                item = {"category": cat, "pts": pts, "reason": reason}
                existing_deds.append(item)
                deductions_added.append(item)

            ai_proposals["deductions"] = []
            v_score = max(0.0, 3.0 - sum(d["pts"] for d in existing_deds if d.get("category") == "vysledky"))
            d_score = max(0.0, 3.0 - sum(d["pts"] for d in existing_deds if d.get("category") == "diskuze"))
            f_score = max(0.0, 2.0 - sum(d["pts"] for d in existing_deds if d.get("category") == "format"))
            c_score = max(0.0, 2.0 - sum(d["pts"] for d in existing_deds if d.get("category") == "chyby"))
            tot = round(v_score + d_score + f_score + c_score, 3)
            grade_mark = calculate_grade_mark(tot)

            cur.execute("""
            INSERT INTO evaluations (
                protocol_id, vysledky_score, diskuze_score, format_score, chyby_score,
                total_points, grade, deductions_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(protocol_id) DO UPDATE SET
                vysledky_score = excluded.vysledky_score,
                diskuze_score = excluded.diskuze_score,
                format_score = excluded.format_score,
                chyby_score = excluded.chyby_score,
                total_points = excluded.total_points,
                grade = excluded.grade,
                deductions_json = excluded.deductions_json,
                updated_at = excluded.updated_at
            """, (proto_id, v_score, d_score, f_score, c_score, tot, grade_mark, json.dumps(existing_deds, ensure_ascii=False), now))

            cur.execute("UPDATE protocols SET total_points = ?, grade = ?, updated_at = ? WHERE id = ?",
                        (tot, grade_mark, now, proto_id))

        cur.execute("UPDATE protocols SET ai_proposals_json = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(ai_proposals, ensure_ascii=False), now, proto_id))
        conn.commit()

        return {
            "status": "ok",
            "action": action,
            "proposal_id": target_id,
            "created_annotation": created_annotation,
            "created_annotations": created_annotations,
            "deduction": deduction_added,
            "deductions": deductions_added,
            "ai_proposals": ai_proposals
        }
    finally:
        conn.close()

# Interactive AI Chat Endpoints
@app.post("/api/protocols/{proto_id}/ai/chat", response_model=AIChatResponse)
async def ai_chat_endpoint(
    proto_id: int,
    req: AIChatRequest,
    user: dict = Depends(get_current_user)
):
    try:
        custom_key = user.get("custom_gemini_api_key")
        resp = await chat_with_ai(
            proto_id,
            user_message=req.message,
            custom_key=custom_key,
            language=req.language
        )
        return resp
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/protocols/{proto_id}/ai/chat", response_model=List[AIChatMessage])
def get_ai_chat_endpoint(
    proto_id: int,
    user: dict = Depends(get_current_user)
):
    return get_protocol_chat_history(proto_id)

@app.delete("/api/protocols/{proto_id}/ai/chat")
def clear_ai_chat_endpoint(
    proto_id: int,
    user: dict = Depends(get_current_user)
):
    clear_protocol_chat_history(proto_id)
    return {"status": "ok", "message": "Historie chatu byla vymazána."}



@app.get("/api/settings/ai")
def get_ai_settings(user: dict = Depends(get_current_user)):
    global_key = get_gemini_api_key()
    personal_key = user.get("custom_gemini_api_key") or ""
    active_key = personal_key or global_key
    masked_key = f"{active_key[:6]}...{active_key[-4:]}" if len(active_key) > 10 else ("***" if active_key else "")
    model_name = get_ai_setting("gemini_model") or get_ai_setting("ai_model", "gemini-3.5-flash-lite")
    auto_analyze = get_ai_setting("auto_analyze_on_upload", "true").lower() in ("true", "1", "yes")
    ai_language = get_ai_setting("ai_language", "cs")
    return {
        "has_key": bool(active_key),
        "masked_key": masked_key,
        "gemini_api_key": global_key if user["role"] == "admin" else personal_key,
        "personal_gemini_api_key": personal_key,
        "model_name": model_name,
        "auto_analyze_on_upload": auto_analyze,
        "ai_language": ai_language,
        "ai_enabled": True,
        "is_admin": user["role"] == "admin"
    }

@app.post("/api/settings/ai")
def set_ai_settings(req: AISettingsRequest, user: dict = Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    # Personal key can be updated by any user
    raw_personal = req.personal_gemini_api_key if req.personal_gemini_api_key is not None else (req.gemini_api_key if user["role"] == "assistant" else None)
    if raw_personal is not None:
        p_key = raw_personal.strip() or None
        cur.execute("UPDATE users SET custom_gemini_api_key = ? WHERE id = ?", (p_key, user["id"]))
        conn.commit()

    # Admin can update global keys and model settings
    if user["role"] == "admin":
        key = req.gemini_api_key if req.gemini_api_key is not None else (req.api_key if req.api_key is not None else None)
        if key is not None:
            save_gemini_api_key(key)
        if req.model_name is not None:
            m_name = req.model_name.strip()
            save_ai_setting("gemini_model", m_name)
            save_ai_setting("ai_model", m_name)
        if req.auto_analyze_on_upload is not None:
            save_ai_setting("auto_analyze_on_upload", "true" if req.auto_analyze_on_upload else "false")
        if req.ai_language is not None:
            save_ai_setting("ai_language", req.ai_language.strip().lower())
    else:
        if req.ai_language is not None:
            save_ai_setting("ai_language", req.ai_language.strip().lower())
    conn.close()

    global_key = get_gemini_api_key()
    personal_key = raw_personal if raw_personal is not None else (user.get("custom_gemini_api_key") or "")
    active_key = (personal_key or "").strip() or global_key

    return {
        "status": "ok",
        "message": "Nastavení AI asistenta bylo uloženo",
        "has_key": bool(active_key),
        "gemini_api_key": global_key if user["role"] == "admin" else personal_key,
        "personal_gemini_api_key": personal_key,
        "model_name": get_ai_setting("gemini_model", "gemini-3.5-flash-lite"),
        "auto_analyze_on_upload": get_ai_setting("auto_analyze_on_upload", "true").lower() in ("true", "1", "yes"),
        "ai_language": get_ai_setting("ai_language", "cs"),
        "ai_enabled": req.ai_enabled if req.ai_enabled is not None else True,
        "is_admin": user["role"] == "admin"
    }

# Changelog API
@app.get("/api/changelog")
def get_changelog():
    changelog_path = BASE_DIR / "CHANGELOG.md"
    if changelog_path.is_file():
        return {"content": changelog_path.read_text(encoding="utf-8")}
    return {"content": "# Changelog\nSoubor changelogu nebyl nalezen."}

# Bulk ZIP Export of corrected PDFs and bodovani.txt
@app.get("/api/export/zip")
def export_protocols_zip(
    semester_id: Optional[int] = None,
    slot_id: Optional[int] = None,
    measurement_id: Optional[int] = None,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    conn = get_db()
    cur = conn.cursor()
    query = """
    SELECT p.id, p.student_name, p.status, p.corrected_path, p.source_path,
           p.source_filename, p.corrected_filename,
           s.code AS semester_code, sl.name AS slot_name, sl.day_of_week, sl.time_start,
           m.code AS measurement_code, m.number AS measurement_number
    FROM protocols p
    JOIN semesters s ON p.semester_id = s.id
    JOIN slots sl ON p.slot_id = sl.id
    JOIN measurements m ON p.measurement_id = m.id
    WHERE 1=1
    """
    params = []
    if semester_id:
        query += " AND p.semester_id = ?"
        params.append(semester_id)
    if slot_id:
        query += " AND p.slot_id = ?"
        params.append(slot_id)
    if measurement_id:
        query += " AND p.measurement_id = ?"
        params.append(measurement_id)
    if status:
        query += " AND p.status = ?"
        params.append(status)
    if user["role"] != "admin":
        query += " AND (p.evaluator_id = ? OR p.evaluator_id IS NULL)"
        params.append(user["id"])

    cur.execute(query, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    zip_buffer = io.BytesIO()
    added_arcnames = set()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in rows:
            student_slug = slugify(r["student_name"])
            prefix = f"{student_slug}_Uloha_{r['measurement_number']}"
            
            # 1. Corrected PDF if available
            if r["corrected_path"] and os.path.isfile(r["corrected_path"]):
                c_fname = r["corrected_filename"] or f"{prefix}_opravene.pdf"
                arc = f"{prefix}/{c_fname}"
                if arc in added_arcnames:
                    arc = f"{prefix}_{r['id']}/{c_fname}"
                zf.write(r["corrected_path"], arcname=arc)
                added_arcnames.add(arc)
            # 2. bodovani.txt in corrected folder
            if r["corrected_path"]:
                bodovani_path = Path(r["corrected_path"]).parent / "bodovani.txt"
                if bodovani_path.is_file():
                    arc = f"{prefix}/bodovani.txt"
                    if arc in added_arcnames:
                        arc = f"{prefix}_{r['id']}/bodovani.txt"
                    zf.write(bodovani_path, arcname=arc)
                    added_arcnames.add(arc)
            # 3. Source PDF fallback if not yet corrected
            if not r["corrected_path"] and r["source_path"] and os.path.isfile(r["source_path"]):
                s_fname = r["source_filename"] or f"{prefix}_original.pdf"
                arc = f"{prefix}/{s_fname}"
                if arc in added_arcnames:
                    arc = f"{prefix}_{r['id']}/{s_fname}"
                zf.write(r["source_path"], arcname=arc)
                added_arcnames.add(arc)

    zip_buffer.seek(0)
    filename = f"praktika_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# CSV Export for University IS / Excel
@app.get("/api/export/csv")
def export_protocols_csv(
    semester_id: Optional[int] = None,
    slot_id: Optional[int] = None,
    measurement_id: Optional[int] = None,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    conn = get_db()
    cur = conn.cursor()
    query = """
    SELECT p.student_name, m.number AS meas_num, m.name AS meas_name,
           sl.day_of_week, sl.time_start, sl.time_end, sl.room,
           p.status, p.total_points, p.grade,
           e.vysledky_score, e.diskuze_score, e.format_score, e.chyby_score,
           u.full_name AS evaluator_name
    FROM protocols p
    JOIN semesters s ON p.semester_id = s.id
    JOIN slots sl ON p.slot_id = sl.id
    JOIN measurements m ON p.measurement_id = m.id
    LEFT JOIN evaluations e ON e.protocol_id = p.id
    LEFT JOIN users u ON p.evaluator_id = u.id
    WHERE 1=1
    """
    params = []
    if semester_id:
        query += " AND p.semester_id = ?"
        params.append(semester_id)
    if slot_id:
        query += " AND p.slot_id = ?"
        params.append(slot_id)
    if measurement_id:
        query += " AND p.measurement_id = ?"
        params.append(measurement_id)
    if status:
        query += " AND p.status = ?"
        params.append(status)
    if user["role"] != "admin":
        query += " AND (p.evaluator_id = ? OR p.evaluator_id IS NULL)"
        params.append(user["id"])

    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    conn.close()

    output = io.StringIO()
    # Write UTF-8 BOM for Microsoft Excel
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Student", "Úloha", "Termín", "Místnost", "Stav",
        "Výsledky (max 3)", "Diskuze (max 3)", "Formát (max 2)", "Chyby (max 2)",
        "Celkem bodů (max 10)", "Známka", "Opravil"
    ])

    for r in rows:
        st_text = "Opraveno" if r[7] == "graded" else ("K přepracování" if r[7] == "revision" else ("Rozpracováno" if r[7] == "in_progress" else "Nový"))
        slot_text = f"{r[3]} {r[4]}–{r[5]}"
        writer.writerow([
            r[0],
            f"Úloha {r[1]}: {r[2]}",
            slot_text,
            r[6] or "",
            st_text,
            format_points(r[10]).replace(".", ",") if r[10] is not None else "",
            format_points(r[11]).replace(".", ",") if r[11] is not None else "",
            format_points(r[12]).replace(".", ",") if r[12] is not None else "",
            format_points(r[13]).replace(".", ",") if r[13] is not None else "",
            format_points(r[8]).replace(".", ",") if r[8] is not None else "",
            r[9] or "",
            r[14] or "Nepřiřazeno"
        ])

    csv_data = output.getvalue().encode("utf-8")
    filename = f"praktika_vysledky_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ==========================================
# DATABASE MANAGEMENT & BACKUPS (ADMIN ONLY)
# ==========================================

@app.get("/api/database/stats")
def get_database_stats(user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Pouze administrátor má přístup k databázi.")
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM protocols")
    protocols_cnt = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM evaluations")
    evaluations_cnt = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM annotations")
    annotations_cnt = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users")
    users_cnt = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM measurements")
    measurements_cnt = cur.fetchone()[0]
    cur.execute("PRAGMA journal_mode")
    journal_mode = cur.fetchone()[0]
    conn.close()

    db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    wal_path = DB_PATH.parent / f"{DB_PATH.name}-wal"
    wal_size = wal_path.stat().st_size if wal_path.exists() else 0

    backups = sorted(BACKUPS_DIR.glob("*.sqlite"), key=lambda p: p.stat().st_mtime, reverse=True)
    latest_backup = None
    if backups:
        b = backups[0]
        latest_backup = {
            "filename": b.name,
            "size_bytes": b.stat().st_size,
            "created_at": datetime.fromtimestamp(b.stat().st_mtime).isoformat()
        }

    return {
        "db_size_bytes": db_size,
        "wal_size_bytes": wal_size,
        "total_size_bytes": db_size + wal_size,
        "journal_mode": str(journal_mode).upper(),
        "protocols_count": protocols_cnt,
        "evaluations_count": evaluations_cnt,
        "annotations_count": annotations_cnt,
        "users_count": users_cnt,
        "measurements_count": measurements_cnt,
        "backups_count": len(backups),
        "latest_backup": latest_backup
    }

@app.get("/api/database/backup")
def download_database_backup(background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Pouze administrátor může stahovat zálohu databázi.")
    
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"Praktika_backup_{now_str}.sqlite"
    temp_target = BACKUPS_DIR / f"download_{backup_filename}"
    try:
        create_sqlite_backup(temp_target)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při vytváření zálohy: {str(e)}")
    
    background_tasks.add_task(temp_target.unlink, missing_ok=True)
    return FileResponse(
        path=str(temp_target),
        filename=backup_filename,
        media_type="application/x-sqlite3"
    )

@app.post("/api/database/optimize")
def optimize_database(user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Pouze administrátor může optimalizovat databázi.")
    
    conn = get_db()
    before_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        conn.execute("VACUUM;")
        conn.execute("ANALYZE;")
        conn.commit()
    finally:
        conn.close()

    after_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    return {
        "status": "ok",
        "before_bytes": before_size,
        "after_bytes": after_size,
        "freed_bytes": max(0, before_size - after_size),
        "message": "Databáze byla úspěšně optimalizována (VACUUM & ANALYZE provedeno)."
    }

@app.post("/api/database/restore")
async def restore_database(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Pouze administrátor může obnovovat databázi.")
    
    content = await file.read()
    if len(content) < 100 or not content.startswith(b"SQLite format 3\x00"):
        raise HTTPException(status_code=400, detail="Nahraný soubor není platnou SQLite databází.")
    
    # Safety: create pre-restore backup first!
    safety_name = f"safety_pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite"
    try:
        create_sqlite_backup(BACKUPS_DIR / safety_name)
    except Exception as ex:
        print("Safety backup warning:", ex)

    # Write restored content to temp file first
    temp_restored = BACKUPS_DIR / "temp_restored.sqlite"
    with open(temp_restored, "wb") as f:
        f.write(content)

    # Verify temp file can be opened and queried
    try:
        import sqlite3
        t_conn = sqlite3.connect(str(temp_restored))
        t_cur = t_conn.cursor()
        t_cur.execute("SELECT COUNT(*) FROM users")
        u_cnt = t_cur.fetchone()[0]
        t_conn.close()
        if u_cnt == 0:
            raise ValueError("V nahrané databázi chybí uživatelé.")
    except Exception as e:
        if temp_restored.exists():
            temp_restored.unlink()
        raise HTTPException(status_code=400, detail=f"Nahraná databáze je neplatná nebo poškozená: {str(e)}")

    # Overwrite DB_PATH with safe online backup from temp
    try:
        src_conn = sqlite3.connect(str(temp_restored))
        dest_conn = get_db()
        with dest_conn:
            src_conn.backup(dest_conn)
        src_conn.close()
        dest_conn.close()
        if temp_restored.exists():
            temp_restored.unlink()
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Chyba při obnově databáze: {str(ex)}")

    return {"status": "ok", "message": "Databáze byla úspěšně obnovena ze zálohy.", "safety_backup": safety_name}

# ==========================================
# SYSTEM DIAGNOSTICS & GEMINI TEST (ADMIN ONLY)
# ==========================================

@app.get("/api/system/diagnostics")
def get_system_diagnostics(user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Pouze administrátor má přístup k diagnostice.")
    
    import platform
    import sys
    import sqlite3

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT sqlite_version()")
    sqlite_ver = cur.fetchone()[0]
    cur.execute("PRAGMA journal_mode")
    j_mode = cur.fetchone()[0]
    conn.close()

    api_key = get_gemini_api_key()
    masked_key = f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else ("Nastaven" if api_key else "Není nastaven")

    return {
        "python_version": sys.version.split(" ")[0],
        "python_full": sys.version,
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "pymupdf_version": getattr(pymupdf, "__version__", "N/A"),
        "sqlite_version": sqlite_ver,
        "journal_mode": str(j_mode).upper(),
        "gemini_api_key_status": masked_key,
        "gemini_preferred_model": get_ai_setting("gemini_model") or get_ai_setting("ai_model", "gemini-3.5-flash-lite"),
        "db_path": str(DB_PATH),
        "backups_path": str(BACKUPS_DIR)
    }

@app.post("/api/system/test-gemini")
async def test_gemini_connection(user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Pouze administrátor může testovat spojení.")
    
    api_key = get_gemini_api_key()
    if not api_key:
        raise HTTPException(status_code=400, detail="Není nastaven platný Gemini API klíč.")
    
    import httpx
    model_name = get_ai_setting("gemini_model") or get_ai_setting("ai_model", "gemini-3.5-flash-lite")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json={
                "contents": [{"parts": [{"text": "Odpověz jedním slovem: OK"}]}],
                "generationConfig": {"temperature": 0.0, "maxOutputTokens": 10}
            })
            latency_ms = int((time.time() - t0) * 1000)
            if resp.status_code == 200:
                data = resp.json()
                reply = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                return {
                    "success": True,
                    "status_code": 200,
                    "latency_ms": latency_ms,
                    "model": model_name,
                    "reply": reply,
                    "message": f"Spojení s Google Gemini je plně funkční (odezva {latency_ms} ms)."
                }
            else:
                return {
                    "success": False,
                    "status_code": resp.status_code,
                    "latency_ms": latency_ms,
                    "model": model_name,
                    "error": resp.text[:120],
                    "message": f"Chyba od Gemini API: HTTP {resp.status_code} ({resp.text[:120]})"
                }
    except Exception as e:
        latency_ms = int((time.time() - t0) * 1000)
        return {
            "success": False,
            "latency_ms": latency_ms,
            "model": model_name,
            "error": str(e),
            "message": f"Chyba spojení s Gemini: {str(e)}"
        }

# ==========================================
# PUBLIC STUDENT VIEW (SECURE SHARE TOKEN)
# ==========================================

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

@app.get("/v/{share_token}", response_class=HTMLResponse)
def view_student_protocol(share_token: str, request: Request):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    SELECT p.*, s.name as semester_name, sl.name as slot_name,
           m.code as measurement_code, m.name as measurement_name,
           u.full_name as evaluator_name,
           e.vysledky_score, e.diskuze_score, e.format_score, e.chyby_score,
           e.total_points as eval_total_points, e.grade as eval_grade,
           e.deductions_json, e.general_comment, e.updated_at as eval_updated_at,
           a.annotations_json
    FROM protocols p
    LEFT JOIN semesters s ON p.semester_id = s.id
    LEFT JOIN slots sl ON p.slot_id = sl.id
    LEFT JOIN measurements m ON p.measurement_id = m.id
    LEFT JOIN users u ON p.evaluator_id = u.id
    LEFT JOIN evaluations e ON p.id = e.protocol_id
    LEFT JOIN annotations a ON p.id = a.protocol_id
    WHERE p.share_token = ?
    """, (share_token,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Protokol nebyl nalezen nebo odkaz není platný.")

    proto_dict = dict(row)
    
    # Parse deductions
    raw_deds = []
    try:
        raw_deds = json.loads(proto_dict.get("deductions_json") or "[]")
    except Exception:
        raw_deds = []

    # Parse annotations to build indexed notes list
    raw_annots = []
    try:
        raw_annots = json.loads(proto_dict.get("annotations_json") or "[]")
    except Exception:
        raw_annots = []

    indexed_notes = []
    for item in raw_annots:
        content = (item.get("content") or item.get("comment") or "").strip()
        if content:
            item_type = item.get("type", "highlight")
            type_label = "Zvýrazněný text" if item_type == "highlight" else ("Volná poznámka" if item_type == "note" else "Anotace v textu")
            p_num = int(item.get("page", 1))
            rect_c = item.get("rect") or (item.get("rects")[0] if item.get("rects") else None)
            pt_c = item.get("point")
            y_pos = float(rect_c[1]) if rect_c and len(rect_c) >= 2 else (float(pt_c[1]) if pt_c and len(pt_c) >= 2 else 0.0)
            x_pos = float(rect_c[0]) if rect_c and len(rect_c) >= 1 else (float(pt_c[0]) if pt_c and len(pt_c) >= 1 else 0.0)

            indexed_notes.append({
                "page_num": p_num,
                "x": x_pos,
                "y": y_pos,
                "type_label": type_label,
                "author": item.get("author") or proto_dict.get("evaluator_name") or "Asistent",
                "content": content,
                "color": item.get("color", "#ef4444"),
                "context_snippet": ""
            })

    indexed_notes.sort(key=lambda n: (n["page_num"], n["y"], n["x"]))
    for i, n in enumerate(indexed_notes):
        n["index"] = i + 1

    total_pts = float(proto_dict.get("eval_total_points") or proto_dict.get("total_points") or 10.0)
    grade = proto_dict.get("eval_grade") or proto_dict.get("grade") or calculate_grade_letter(total_pts)
    eval_date_str = datetime.now().strftime("%d.%m.%Y")
    if proto_dict.get("eval_updated_at"):
        try:
            eval_date_str = datetime.fromisoformat(proto_dict["eval_updated_at"]).strftime("%d.%m.%Y")
        except Exception:
            pass

    return templates.TemplateResponse(
        request=request,
        name="student_view.html",
        context={
            "share_token": share_token,
            "student_name": proto_dict.get("student_name", "Student"),
            "measurement_code": proto_dict.get("measurement_code", "Úloha"),
            "measurement_name": proto_dict.get("measurement_name", "Měření"),
            "semester_name": proto_dict.get("semester_name", "Semestr"),
            "slot_name": proto_dict.get("slot_name", ""),
            "evaluator_name": proto_dict.get("evaluator_name", "Cvičící"),
            "eval_date": eval_date_str,
            "grade": grade,
            "total_points": format_points(total_pts),
            "vysledky_score": format_points(proto_dict.get("vysledky_score", 0.0)),
            "diskuze_score": format_points(proto_dict.get("diskuze_score", 0.0)),
            "format_score": format_points(proto_dict.get("format_score", 0.0)),
            "chyby_score": format_points(proto_dict.get("chyby_score", 0.0)),
            "general_comment": (proto_dict.get("general_comment") or "").strip(),
            "deductions": raw_deds,
            "indexed_notes": indexed_notes,
            "annotations_json": proto_dict.get("annotations_json") or "[]",
            "has_exported": bool(proto_dict.get("corrected_path") and Path(proto_dict["corrected_path"]).exists()),
            "has_source": bool(proto_dict.get("source_path") and Path(proto_dict["source_path"]).exists())
        }
    )

@app.get("/api/public/protocol/{share_token}/pdf")
def get_public_pdf(share_token: str, mode: str = "source"):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT corrected_path, corrected_filename, source_path, source_filename FROM protocols WHERE share_token = ?", (share_token,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Protokol nebyl nalezen")

    if mode == "exported":
        pdf_path = row["corrected_path"] if (row["corrected_path"] and Path(row["corrected_path"]).exists()) else row["source_path"]
        filename = row["corrected_filename"] or row["source_filename"] or "opraveny_protokol.pdf"
    else:
        pdf_path = row["source_path"] if (row["source_path"] and Path(row["source_path"]).exists()) else row["corrected_path"]
        filename = row["source_filename"] or row["corrected_filename"] or "protokol.pdf"

    if not pdf_path or not Path(pdf_path).exists():
        raise HTTPException(status_code=404, detail="PDF soubor nebyl na serveru nalezen")

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )

@app.get("/api/public/protocol/{share_token}")
def get_public_protocol_data(share_token: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    SELECT p.student_name, p.status, m.code as measurement_code, m.name as measurement_name,
           u.full_name as evaluator_name, e.total_points, e.grade, e.deductions_json, e.updated_at
    FROM protocols p
    JOIN measurements m ON p.measurement_id = m.id
    LEFT JOIN users u ON p.evaluator_id = u.id
    LEFT JOIN evaluations e ON p.id = e.protocol_id
    WHERE p.share_token = ?
    """, (share_token,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Protokol nenalezen")
    d = dict(row)
    try:
        d["deductions"] = json.loads(d.get("deductions_json") or "[]")
    except Exception:
        d["deductions"] = []
    return d

# ==========================================
# FRONTEND SPA ENTRY POINT & VERSION
# ==========================================

@app.get("/api/version")
def get_version():
    return {"version": VERSION}

@app.get("/{full_path:path}", response_class=HTMLResponse)
def serve_spa(request: Request, full_path: str):
    template_path = BASE_DIR / "app" / "templates" / "index.html"
    if template_path.exists():
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
            return content.replace("{{ version }}", VERSION).replace("{{version}}", VERSION)
    return "<h1>Aplikace se načítá...</h1>"
