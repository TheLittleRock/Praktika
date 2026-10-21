"""
Unit tests for Praktika v2.20.1:
- ČVUT Moodle Course Structure & Tiles Scraping
- Pending Submissions Discovery & Task/Term Auto-matching
- Auto-creation of missing slot in active semester
- ČVUT ECTS Grade calculation (A-F, 90/80/70/60/50%)
- Gradable protocols listing with ECTS grades
- AppModal HTML support
"""

import unittest
import sys
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from starlette.testclient import TestClient

from app.version import VERSION
from app.main import app
from app.database import init_db, get_db
from app.moodle_service import (
    calculate_cvut_grade, moodle_grade_to_scale_id,
    normalize_student_name, parse_moodle_submission_filename,
    build_moodle_feedback_zip
)


class TestPraktikaV2201(unittest.TestCase):
    def setUp(self):
        init_db()
        self.client = TestClient(app)
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, username, role FROM users WHERE role = 'admin' LIMIT 1")
        row = cur.fetchone()
        conn.close()
        from app.auth import create_access_token
        from app.moodle_service import save_moodle_setting
        save_moodle_setting("moodle_session_cookie", "test_moodle_session_cookie_123")
        self.admin_token = create_access_token({"sub": row["username"], "role": row["role"], "id": row["id"]})
        self.auth_headers = {"Authorization": f"Bearer {self.admin_token}"}

    def test_version_bump(self):
        self.assertEqual(VERSION, "2.20.1")

    def test_cvut_grade_calculation(self):
        # A >= 90%
        self.assertEqual(calculate_cvut_grade(9.5, 10.0), ("A", 6))
        self.assertEqual(calculate_cvut_grade(9.0, 10.0), ("A", 6))
        # B >= 80%
        self.assertEqual(calculate_cvut_grade(8.5, 10.0), ("B", 5))
        self.assertEqual(calculate_cvut_grade(8.0, 10.0), ("B", 5))
        # C >= 70%
        self.assertEqual(calculate_cvut_grade(7.5, 10.0), ("C", 4))
        self.assertEqual(calculate_cvut_grade(7.0, 10.0), ("C", 4))
        # D >= 60%
        self.assertEqual(calculate_cvut_grade(6.5, 10.0), ("D", 3))
        self.assertEqual(calculate_cvut_grade(6.0, 10.0), ("D", 3))
        # E >= 50%
        self.assertEqual(calculate_cvut_grade(5.5, 10.0), ("E", 2))
        self.assertEqual(calculate_cvut_grade(5.0, 10.0), ("E", 2))
        # F < 50%
        self.assertEqual(calculate_cvut_grade(4.5, 10.0), ("F", 1))
        self.assertEqual(calculate_cvut_grade(0.0, 10.0), ("F", 1))

    def test_moodle_grade_to_scale_id(self):
        self.assertEqual(moodle_grade_to_scale_id("A"), 6)
        self.assertEqual(moodle_grade_to_scale_id("b"), 5)
        self.assertEqual(moodle_grade_to_scale_id("C"), 4)
        self.assertEqual(moodle_grade_to_scale_id("D"), 3)
        self.assertEqual(moodle_grade_to_scale_id("E"), 2)
        self.assertEqual(moodle_grade_to_scale_id("F"), 1)
        self.assertEqual(moodle_grade_to_scale_id("X"), -1)

    def test_normalize_student_name(self):
        self.assertEqual(normalize_student_name("AJ Adam Jaroslav"), "Adam Jaroslav")
        self.assertEqual(normalize_student_name("RK Rudolfová Klára"), "Rudolfová Klára")
        self.assertEqual(normalize_student_name("Pálková Emma"), "Pálková Emma")
        self.assertEqual(normalize_student_name("  Bořil Tomáš  "), "Bořil Tomáš")

    @patch("app.main.get_current_user")
    def test_moodle_pending_submissions_endpoint(self, mock_user):
        mock_user.return_value = {"id": 1, "username": "admin", "role": "admin"}
        
        with patch("app.main.fetch_pending_submissions", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [
                {
                    "cmid": "482838",
                    "task_title": "P1 - 01 Vzduchová dráha",
                    "student_name": "Klára Rudolfová",
                    "moodle_user_id": 52724,
                    "student_group": "Středa 8:00",
                    "filename": "FPRA1__rudolfova_1_.pdf",
                    "file_url": "https://moodle-vyuka.cvut.cz/pluginfile.php/123/FPRA1.pdf",
                    "status_text": "Návrh (neodesláno)",
                    "matched_task_id": 1,
                    "matched_task_name": "Vzduchová dráha - ZZE, srážky, impuls síly",
                    "matched_slot_id": 52,
                    "matched_slot_name": "Středa 8:00",
                    "can_auto_create_slot": False,
                    "already_in_db": False
                }
            ]
            
            resp = self.client.get("/api/moodle/pending-submissions?cmid=482838&group=all", headers=self.auth_headers)
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["student_name"], "Klára Rudolfová")
            self.assertEqual(data[0]["matched_task_id"], 1)

    @patch("app.main.get_current_user")
    def test_moodle_download_selected_auto_creates_slot(self, mock_user):
        mock_user.return_value = {"id": 1, "username": "admin", "role": "admin"}

        # Insert active semester and test measurement
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM semesters WHERE is_active = 1")
        row = cur.fetchone()
        if not row:
            cur.execute("INSERT INTO semesters (code, name, is_active) VALUES ('2026TEST', 'Test Semestr', 1)")
            sem_id = cur.lastrowid
        else:
            sem_id = row[0]

        cur.execute("SELECT id FROM measurements LIMIT 1")
        meas_row = cur.fetchone()
        meas_id = meas_row[0] if meas_row else 1
        conn.commit()
        conn.close()

        req_payload = {
            "items": [
                {
                    "cmid": "482838",
                    "student_name": "Testovací Nový Student",
                    "file_url": "https://moodle-vyuka.cvut.cz/test.pdf",
                    "filename": "test.pdf",
                    "measurement_id": meas_id,
                    "slot_id": None,
                    "group_name": "Pátek 10:00 Unikátní",
                    "auto_create_slot": True
                }
            ]
        }

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            # Valid PDF dummy content
            mock_resp.content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
            mock_get.return_value = mock_resp

            with patch("app.main.save_source_file") as mock_save:
                mock_save.return_value = Path("/tmp/test_source.pdf")
                resp = self.client.post("/api/moodle/download-selected", json=req_payload, headers=self.auth_headers)
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                self.assertEqual(data["status"], "ok")
                self.assertEqual(data["imported_count"], 1)

        # Verify that slot was created in DB
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM slots WHERE name = 'Pátek 10:00 Unikátní'")
        new_slot = cur.fetchone()
        self.assertIsNotNone(new_slot)
        # Clean up test slot
        cur.execute("DELETE FROM protocols WHERE student_name = 'Testovací Nový Student'")
        cur.execute("DELETE FROM slots WHERE name = 'Pátek 10:00 Unikátní'")
        conn.commit()
        conn.close()

    @patch("app.main.get_current_user")
    def test_moodle_gradable_protocols_endpoint(self, mock_user):
        mock_user.return_value = {"id": 1, "username": "admin", "role": "admin"}

        resp = self.client.get("/api/moodle/gradable-protocols", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)


if __name__ == "__main__":
    unittest.main()
