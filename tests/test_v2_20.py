"""
Comprehensive Automated Test Suite for Praktika v2.20.0
- Student view analytics & active reading heartbeat tracking
- Moodle integration service, filename parsing, feedback zip builder, endpoints
"""

import unittest
import sys
import json
import secrets
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.version import VERSION
from app.database import get_db, init_db
from app.main import app
from app.moodle_service import (
    parse_moodle_submission_filename,
    build_moodle_feedback_zip,
    get_moodle_config,
    save_moodle_setting
)
from starlette.testclient import TestClient

class TestPraktikaV220(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

        # Ensure an active admin user and auth token for testing authenticated endpoints
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, username, role FROM users WHERE role = 'admin' LIMIT 1")
        row = cur.fetchone()
        conn.close()

        from app.auth import create_access_token
        cls.admin_token = create_access_token({"sub": row["username"], "role": row["role"], "id": row["id"]})
        cls.auth_headers = {"Authorization": f"Bearer {cls.admin_token}"}

    def test_version(self):
        self.assertEqual(VERSION, "2.20.0")

    def test_database_schema(self):
        conn = get_db()
        cur = conn.cursor()

        # Check protocol_views table
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='protocol_views'")
        self.assertIsNotNone(cur.fetchone())

        # Check columns in protocols
        cur.execute("PRAGMA table_info(protocols)")
        cols = {r["name"] for r in cur.fetchall()}
        self.assertIn("student_view_count", cols)
        self.assertIn("student_view_total_seconds", cols)
        self.assertIn("student_view_first_at", cols)
        self.assertIn("student_view_last_at", cols)

        # Check default moodle settings in app_settings
        cur.execute("SELECT value FROM app_settings WHERE key = 'moodle_url'")
        self.assertEqual(cur.fetchone()[0], "https://moodle-vyuka.cvut.cz")
        cur.execute("SELECT value FROM app_settings WHERE key = 'moodle_course_id'")
        self.assertEqual(cur.fetchone()[0], "16880")
        conn.close()

    def test_student_heartbeat_and_analytics(self):
        # 1. Create a temporary test protocol in the database
        conn = get_db()
        cur = conn.cursor()
        tok = secrets.token_urlsafe(16)
        now = datetime.now().isoformat()
        cur.execute("SELECT id FROM semesters LIMIT 1")
        sem_id = cur.fetchone()[0]
        cur.execute("SELECT id FROM slots LIMIT 1")
        slot_id = cur.fetchone()[0]
        cur.execute("SELECT id FROM measurements LIMIT 1")
        meas_id = cur.fetchone()[0]

        cur.execute("""
        INSERT INTO protocols (
            semester_id, slot_id, measurement_id, student_name, status,
            source_filename, source_path, share_token, created_at, updated_at
        ) VALUES (?, ?, ?, 'Testovací Student Analytics', 'graded', 'test.pdf', '/tmp/test.pdf', ?, ?, ?)
        """, (sem_id, slot_id, meas_id, tok, now, now))
        proto_id = cur.lastrowid
        conn.commit()
        conn.close()

        # 2. Initial visit ping for Session A (delta = 0)
        res1 = self.client.post(
            f"/api/public/protocol/{tok}/heartbeat",
            json={"session_id": "test_sess_A", "duration_delta": 0, "is_new": True}
        )
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.json()["duration_seconds"], 0)

        # 3. Heartbeat for Session A (active for 15s)
        res2 = self.client.post(
            f"/api/public/protocol/{tok}/heartbeat",
            json={"session_id": "test_sess_A", "duration_delta": 15, "is_new": False}
        )
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json()["duration_seconds"], 15)

        # Another 15s in Session A -> total 30s
        res3 = self.client.post(
            f"/api/public/protocol/{tok}/heartbeat",
            json={"session_id": "test_sess_A", "duration_delta": 15, "is_new": False}
        )
        self.assertEqual(res3.status_code, 200)
        self.assertEqual(res3.json()["duration_seconds"], 30)

        # 4. New visit in another session/tab (Session B, active 20s)
        res4 = self.client.post(
            f"/api/public/protocol/{tok}/heartbeat",
            json={"session_id": "test_sess_B", "duration_delta": 20, "is_new": True}
        )
        self.assertEqual(res4.status_code, 200)
        self.assertEqual(res4.json()["duration_seconds"], 20)

        # 5. Check anti-cheat clamp (sending 9999 seconds is clamped to max 30s)
        res_clamp = self.client.post(
            f"/api/public/protocol/{tok}/heartbeat",
            json={"session_id": "test_sess_B", "duration_delta": 9999, "is_new": False}
        )
        self.assertEqual(res_clamp.status_code, 200)
        self.assertEqual(res_clamp.json()["duration_seconds"], 50) # 20 + 30 clamped

        # 6. Fetch views endpoint as teacher
        res_views = self.client.get(f"/api/protocols/{proto_id}/views", headers=self.auth_headers)
        self.assertEqual(res_views.status_code, 200)
        vdata = res_views.json()
        self.assertEqual(vdata["protocol_id"], proto_id)
        self.assertEqual(vdata["view_count"], 2) # Two distinct sessions: A and B
        self.assertEqual(vdata["total_seconds"], 80) # 30s (sess A) + 50s (sess B)
        self.assertEqual(len(vdata["sessions"]), 2)
        self.assertIsNotNone(vdata["first_viewed_at"])
        self.assertIsNotNone(vdata["last_viewed_at"])

        # 7. Check list_protocols includes student view aggregates
        res_list = self.client.get(f"/api/protocols?evaluator_id=all&search=Testovac%C3%AD+Student+Analytics", headers=self.auth_headers)
        self.assertEqual(res_list.status_code, 200)
        l_items = res_list.json()
        self.assertTrue(len(l_items) >= 1)
        target = next((p for p in l_items if p["id"] == proto_id), None)
        self.assertIsNotNone(target)
        self.assertEqual(target["student_view_count"], 2)
        self.assertEqual(target["student_view_total_seconds"], 80)

    def test_moodle_filename_parsing(self):
        # 1. Standard flat file format
        f1 = "Jakub Petržílek_123456_assignsubmission_file_protokol_6.pdf"
        p1 = parse_moodle_submission_filename(f1)
        self.assertEqual(p1["student_name"], "Jakub Petržílek")
        self.assertEqual(p1["moodle_user_id"], "123456")
        self.assertEqual(p1["raw_filename"], "Jakub Petržílek_123456_assignsubmission_file_protokol_6.pdf")

        # 2. Folder submission format
        f2 = "Tadeáš Světlík_987654_assignsubmission_file_/FPRA1_Uloha_10.pdf"
        p2 = parse_moodle_submission_filename(f2)
        self.assertEqual(p2["student_name"], "Tadeáš Světlík")
        self.assertEqual(p2["moodle_user_id"], "987654")
        self.assertEqual(p2["raw_filename"], "FPRA1_Uloha_10.pdf")

        # 3. Fallback format with names separated by spaces
        f3 = "Jan Novak_456789_file.pdf"
        p3 = parse_moodle_submission_filename(f3)
        self.assertEqual(p3["student_name"], "Jan Novak")
        self.assertEqual(p3["moodle_user_id"], "456789")

    def test_moodle_feedback_zip_builder(self):
        protocols = [
            {
                "student_name": "Jakub Petržílek",
                "moodle_user_id": "123456",
                "filename": "FPRA1_Uloha_06_Petrzilek_Jakub_opraveno.pdf",
                "pdf_bytes": b"%PDF-1.4 mock pdf content 1"
            },
            {
                "student_name": "Tadeáš Světlík",
                "moodle_user_id": "987654",
                "filename": "FPRA1_Uloha_10_Svetlik_Tadeas_opraveno.pdf",
                "pdf_bytes": b"%PDF-1.4 mock pdf content 2"
            }
        ]

        zip_bytes = build_moodle_feedback_zip(protocols)
        self.assertTrue(len(zip_bytes) > 0)
        self.assertEqual(zip_bytes[:4], b"PK\x03\x04")

        import zipfile
        import io
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
            names = z.namelist()
            self.assertEqual(len(names), 2)
            self.assertIn("Jakub Petržílek_123456_assignsubmission_file_FPRA1_Uloha_06_Petrzilek_Jakub_opraveno.pdf", names)
            self.assertIn("Tadeáš Světlík_987654_assignsubmission_file_FPRA1_Uloha_10_Svetlik_Tadeas_opraveno.pdf", names)
            self.assertEqual(z.read(names[0]), b"%PDF-1.4 mock pdf content 1")

    def test_moodle_endpoints(self):
        # 1. Config endpoint GET
        res_cfg = self.client.get("/api/moodle/config", headers=self.auth_headers)
        self.assertEqual(res_cfg.status_code, 200)
        cfg_data = res_cfg.json()
        self.assertEqual(cfg_data["course_id"], "16880")
        self.assertEqual(cfg_data["moodle_url"], "https://moodle-vyuka.cvut.cz")

        # 2. Config endpoint POST
        res_save = self.client.post("/api/moodle/config", json={
            "moodle_url": "https://moodle-vyuka.cvut.cz",
            "course_id": "16880",
            "moodle_session": "test_mock_cookie_12345"
        }, headers=self.auth_headers)
        self.assertEqual(res_save.status_code, 200)

        # Verify saved
        cfg = get_moodle_config()
        self.assertEqual(cfg["moodle_session"], "test_mock_cookie_12345")

        # Reset cookie to empty for safety
        save_moodle_setting("moodle_session_cookie", "")

if __name__ == "__main__":
    unittest.main()
