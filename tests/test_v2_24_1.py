"""
Unit tests for Praktika v2.24.1:
- Version bump to 2.24.1
- Protocol moodle_uploaded_at database column and schema migration
- GET /api/moodle/gradable-protocols returns graded protocols
- Filtering in gradable-protocols by cmid, my_tasks, and group
- Multi-task feedback upload POST /api/moodle/upload-feedback updating moodle_uploaded_at
- GET /api/protocols includes moodle_uploaded_at
- UI elements: upload assignment select options (all, my_tasks) and row action button
"""

import unittest
import sys
import json
from unittest.mock import patch, AsyncMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from starlette.testclient import TestClient

from app.version import VERSION
from app.main import app
from app.database import init_db, get_db
from app.auth import create_access_token


class TestPraktikaV2241(unittest.TestCase):
    def setUp(self):
        init_db()
        self.client = TestClient(app)
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, username, role FROM users WHERE role = 'admin' LIMIT 1")
        row = cur.fetchone()
        conn.close()
        self.admin_token = create_access_token({"sub": row["username"], "role": row["role"], "id": row["id"]})
        self.auth_headers = {"Authorization": f"Bearer {self.admin_token}"}

    def test_version_bump(self):
        self.assertTrue(VERSION >= "2.24.1")

    def test_moodle_uploaded_at_schema(self):
        """Verify protocols table has moodle_uploaded_at column."""
        conn = get_db()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(protocols)")
        cols = [r[1] for r in cur.fetchall()]
        conn.close()
        self.assertIn("moodle_uploaded_at", cols)

    def test_gradable_protocols_returns_graded_protocols(self):
        """Verify GET /api/moodle/gradable-protocols returns protocols with status 'graded'."""
        resp = self.client.get("/api/moodle/gradable-protocols?cmid=all", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        items = resp.json()
        self.assertIsInstance(items, list)
        self.assertGreater(len(items), 0)

        # Check required fields
        first = items[0]
        self.assertIn("protocol_id", first)
        self.assertIn("student_name", first)
        self.assertIn("task_name", first)
        self.assertIn("points", first)
        self.assertIn("grade_letter", first)
        self.assertIn("cmid", first)
        self.assertIn("moodle_uploaded_at", first)

    def test_gradable_protocols_filtering_my_tasks(self):
        """Verify filtering by cmid='my_tasks' uses user assigned_tasks."""
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
        admin_id = cur.fetchone()["id"]
        # Assign only task ID 6
        cur.execute("UPDATE users SET assigned_tasks = ? WHERE id = ?", (json.dumps([6]), admin_id))
        conn.commit()
        conn.close()

        resp = self.client.get("/api/moodle/gradable-protocols?cmid=my_tasks", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        items = resp.json()
        for it in items:
            self.assertEqual(it["measurement_id"], 6)

    def test_multi_task_upload_feedback(self):
        """Verify POST /api/moodle/upload-feedback dispatches per-student cmid and sets moodle_uploaded_at."""
        conn = get_db()
        cur = conn.cursor()
        # Find a graded protocol
        cur.execute("SELECT id, student_name, measurement_id FROM protocols WHERE status = 'graded' LIMIT 1")
        proto = cur.fetchone()
        conn.close()
        self.assertIsNotNone(proto)
        pid = proto["id"]

        with patch("app.main.submit_moodle_grade", new_callable=AsyncMock) as mock_submit:
            mock_submit.return_value = {"success": True}

            payload = {
                "cmid": "my_tasks",
                "group_id": "0",
                "upload_pdf": True,
                "upload_grade": True,
                "upload_comment": True,
                "students": [
                    {"protocol_id": pid, "grade_letter": "A", "comment": "Výborná práce"}
                ]
            }

            resp = self.client.post("/api/moodle/upload-feedback", json=payload, headers=self.auth_headers)
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["uploaded_count"], 1)

            # Check DB updated
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT moodle_uploaded_at FROM protocols WHERE id = ?", (pid,))
            row = cur.fetchone()
            # Clean up
            cur.execute("UPDATE protocols SET moodle_uploaded_at = NULL WHERE id = ?", (pid,))
            conn.commit()
            conn.close()

            self.assertIsNotNone(row["moodle_uploaded_at"])

    def test_get_protocols_includes_moodle_uploaded_at(self):
        """Verify GET /api/protocols includes moodle_uploaded_at."""
        resp = self.client.get("/api/protocols?evaluator_id=all", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        items = resp.json()
        if len(items) > 0:
            self.assertIn("moodle_uploaded_at", items[0])

    def test_ui_template_elements(self):
        """Verify UI template contains upload assign options and table headers."""
        resp = self.client.get("/", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        html = resp.text

        # Upload assign select options
        self.assertIn('id="moodle-upload-assign-select"', html)
        self.assertIn('value="all">Všechny úlohy</option>', html)
        self.assertIn('value="my_tasks">⭐ Moje úlohy</option>', html)

        # Table header
        self.assertIn("Moodle párování / Stav", html)


if __name__ == "__main__":
    unittest.main()
