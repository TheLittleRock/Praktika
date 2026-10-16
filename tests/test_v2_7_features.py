import os
import io
import time
import json
import sqlite3
import pymupdf
from starlette.testclient import TestClient
from app.main import app
from app.database import perform_daily_auto_backup, DB_PATH
from app.config import BACKUPS_DIR

client = TestClient(app)

def create_sample_pdf_with_text(text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 100), text, fontsize=12)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()

def test_v2_7_admin_and_assistant_permissions():
    # 1. Login as admin
    login_admin = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert login_admin.status_code == 200

    # Create assistant
    u_name = f"asist_v27_{int(time.time())}"
    u_resp = client.post("/api/users", json={
        "username": u_name,
        "full_name": "Asistent Test v2.7",
        "password": "heslo123",
        "role": "assistant"
    })
    assert u_resp.status_code == 200

    # 2. Check admin access to database endpoints
    stats_resp = client.get("/api/database/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert "db_size_bytes" in stats
    assert "users_count" in stats
    assert "journal_mode" in stats
    assert stats.get("users_count", 0) >= 1

    backup_resp = client.get("/api/database/backup")
    assert backup_resp.status_code == 200
    assert backup_resp.headers.get("content-type") == "application/x-sqlite3"
    assert len(backup_resp.content) > 1000

    optimize_resp = client.post("/api/database/optimize")
    assert optimize_resp.status_code == 200
    assert optimize_resp.json()["status"] == "ok"

    diag_resp = client.get("/api/system/diagnostics")
    assert diag_resp.status_code == 200
    diag = diag_resp.json()
    assert "python_version" in diag
    assert "os" in diag
    assert "pymupdf_version" in diag

    gemini_resp = client.post("/api/system/test-gemini")
    assert gemini_resp.status_code in [200, 400]
    if gemini_resp.status_code == 200:
        assert "success" in gemini_resp.json()
    else:
        assert "detail" in gemini_resp.json()

    # 3. Login as assistant and verify 403 Forbidden on all management endpoints
    login_asist = client.post("/api/auth/login", json={"username": u_name, "password": "heslo123"})
    assert login_asist.status_code == 200

    assert client.get("/api/database/stats").status_code == 403
    assert client.get("/api/database/backup").status_code == 403
    assert client.post("/api/database/optimize").status_code == 403
    assert client.post("/api/database/restore", files={"file": ("fake.sqlite", b"fake", "application/octet-stream")}).status_code == 403
    assert client.get("/api/system/diagnostics").status_code == 403
    assert client.post("/api/system/test-gemini").status_code == 403

def test_database_backup_and_restore():
    # Login as admin
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})

    # 1. Download valid backup
    backup_resp = client.get("/api/database/backup")
    assert backup_resp.status_code == 200
    backup_bytes = backup_resp.content

    # 2. Test invalid restore (not a sqlite DB)
    bad_restore = client.post(
        "/api/database/restore",
        files={"file": ("corrupt.sqlite", b"This is not a sqlite database file at all!", "application/octet-stream")}
    )
    assert bad_restore.status_code == 400

    # 3. Test valid restore
    good_restore = client.post(
        "/api/database/restore",
        files={"file": ("backup.sqlite", backup_bytes, "application/octet-stream")}
    )
    assert good_restore.status_code == 200
    res_data = good_restore.json()
    assert res_data["status"] == "ok"
    assert "safety_backup" in res_data

def test_daily_auto_backup_rotation():
    # Call perform_daily_auto_backup
    backup_path = perform_daily_auto_backup()
    assert backup_path is not None
    assert os.path.exists(backup_path)
    assert os.path.getsize(backup_path) > 0
    assert "praktika_auto_" in os.path.basename(backup_path)

def test_batch_upload_student_name_autodetection():
    # Login as admin
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})

    sem_resp = client.get("/api/semesters")
    active_sem = [s for s in sem_resp.json() if s["is_active"]][0]

    slot_resp = client.get(f"/api/slots?semester_id={active_sem['id']}")
    slot_id = slot_resp.json()[0]["id"]

    meas_resp = client.get("/api/measurements")
    meas_id = meas_resp.json()[0]["id"]

    # Create PDF with embedded student name
    pdf_content = create_sample_pdf_with_text("Fyzikální praktikum II\nJméno a příjmení: Rostislav Krásný\nDatum: 16.10.2026")

    # Upload with generic filename and empty student_name
    upload_resp = client.post(
        "/api/protocols/upload",
        data={
            "semester_id": active_sem["id"],
            "slot_id": slot_id,
            "measurement_id": meas_id,
            "student_name": ""
        },
        files={"file": ("mereni_01.pdf", pdf_content, "application/pdf")}
    )
    assert upload_resp.status_code == 200
    proto = upload_resp.json()
    assert proto["student_name"] == "Rostislav Krásný", f"Expected 'Rostislav Krásný', got {proto.get('student_name')}"

if __name__ == "__main__":
    print("Running v2.7 tests...")
    test_v2_7_admin_and_assistant_permissions()
    print("  ✓ test_v2_7_admin_and_assistant_permissions PASSED")
    test_database_backup_and_restore()
    print("  ✓ test_database_backup_and_restore PASSED")
    test_daily_auto_backup_rotation()
    print("  ✓ test_daily_auto_backup_rotation PASSED")
    test_batch_upload_student_name_autodetection()
    print("  ✓ test_batch_upload_student_name_autodetection PASSED")
    print("ALL v2.7 TESTS PASSED SUCCESSFULLY!")
