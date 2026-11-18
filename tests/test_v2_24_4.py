import os
import sys
import json
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.version import VERSION
from app.database import init_db, get_db
from app.auth import create_access_token
from app.main import app
from app.ai_service import run_background_ai_analysis
from starlette.testclient import TestClient

class TestV2244Improvements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, username, role FROM users WHERE role = 'admin' LIMIT 1")
        row = cur.fetchone()
        conn.close()
        cls.admin_token = create_access_token({"sub": row["username"], "role": row["role"], "id": row["id"]})
        cls.auth_headers = {"Authorization": f"Bearer {cls.admin_token}"}

    def test_version_bump_to_2_24_4(self):
        self.assertTrue(VERSION >= "2.24.4")

    def test_html_contains_column_visibility_controls(self):
        index_html_path = Path(__file__).resolve().parent.parent / "app" / "templates" / "index.html"
        content = index_html_path.read_text(encoding="utf-8")
        self.assertIn('id="btn-toggle-columns"', content)
        self.assertIn('id="table-columns-dropdown"', content)
        self.assertIn('id="protocols-main-table"', content)
        self.assertIn('col-toggle-measurement', content)
        self.assertIn('col-toggle-slot', content)
        self.assertIn('col-toggle-submitted', content)
        self.assertIn('col-toggle-status', content)
        self.assertIn('col-toggle-score', content)
        self.assertIn('col-toggle-evaluator', content)
        self.assertIn('col-toggle-views', content)

    def test_css_contains_column_visibility_and_score_alignment_rules(self):
        app_css_path = Path(__file__).resolve().parent.parent / "app" / "static" / "css" / "app.css"
        css = app_css_path.read_text(encoding="utf-8")
        self.assertIn('.hide-col-slot', css)
        self.assertIn('.hide-col-evaluator', css)
        self.assertIn('.hide-col-views', css)
        self.assertIn('.score-cell-container', css)
        self.assertIn('.score-points-wrapper', css)

    def test_ai_status_endpoint_not_found(self):
        resp = self.client.get("/api/protocols/999999/ai-status", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 404)

    def test_ai_status_endpoint_returns_status(self):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM protocols LIMIT 1")
        row = cur.fetchone()
        proto_id = row["id"] if row else None

        if not proto_id:
            cur.execute("INSERT OR IGNORE INTO semesters (code, name, is_active) VALUES ('TEST_SEM', 'Test', 1)")
            cur.execute("SELECT id FROM semesters WHERE code = 'TEST_SEM'")
            sem_id = cur.fetchone()["id"]
            cur.execute("INSERT INTO measurements (semester_id, number, name, code) VALUES (?, 1, 'M', 'C')", (sem_id,))
            meas_id = cur.lastrowid
            cur.execute("INSERT INTO slots (semester_id, day_of_week, time_start, time_end) VALUES (?, 'Po', '08:00', '10:00')", (sem_id,))
            slot_id = cur.lastrowid
            cur.execute("""
                INSERT INTO protocols (student_name, source_filename, measurement_id, slot_id, semester_id, ai_status, ai_proposals_json)
                VALUES ('Test Student', 'test.pdf', ?, ?, ?, 'ready', '{"summary": "Vše v pořádku"}')
            """, (meas_id, slot_id, sem_id))
            proto_id = cur.lastrowid
            conn.commit()
        else:
            cur.execute("UPDATE protocols SET ai_status = 'ready', ai_proposals_json = '{\"summary\": \"Test\"}' WHERE id = ?", (proto_id,))
            conn.commit()

        conn.close()

        resp = self.client.get(f"/api/protocols/{proto_id}/ai-status", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ready")
        self.assertIsNotNone(data["proposals"])

    def test_ai_analyze_endpoint_background_mode(self):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM protocols LIMIT 1")
        row = cur.fetchone()
        proto_id = row["id"]
        conn.close()

        with patch("app.main.run_background_ai_analysis", new_callable=AsyncMock) as mock_bg:
            resp = self.client.post(f"/api/protocols/{proto_id}/ai-analyze?background=true", headers=self.auth_headers)
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "analyzing")
            self.assertEqual(data["protocol_id"], proto_id)

            # Check DB updated to analyzing
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT ai_status FROM protocols WHERE id = ?", (proto_id,))
            status_row = cur.fetchone()
            conn.close()
            self.assertEqual(status_row["ai_status"], "analyzing")

if __name__ == "__main__":
    unittest.main()
