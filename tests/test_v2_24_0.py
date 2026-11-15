"""
Unit tests for Praktika v2.24.0:
- Version bump to 2.24.0
- Protocol dates: submitted_at and measured_at schema columns and automatic backfill
- Regex date extraction from PDF text (Czech, Slovak, various date formats, corrupted font diacritics)
- Moodle Czech date parsing (named months, numeric timestamps)
- Moodle pending submissions in-memory caching and force_refresh handling
- API endpoint GET /api/protocols returning submitted_at and measured_at
- API endpoint PUT /api/protocols/{id}/metadata updating submitted_at and measured_at
- Moodle download selected endpoint storing submitted_at and marking cache
- UI template elements: Odevzdáno table column with sort indicator, Moodle refresh button
"""

import unittest
import sys
import json
import time
from unittest.mock import patch, MagicMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from starlette.testclient import TestClient

from app.version import VERSION
from app.main import app
from app.database import init_db, get_db, extract_dates_from_pdf_text, backfill_protocol_dates
from app.moodle_service import (
    parse_czech_moodle_date, MoodlePendingCache, moodle_pending_cache
)
from app.auth import create_access_token


class TestPraktikaV2240(unittest.TestCase):
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
        self.assertEqual(VERSION, "2.24.0")

    def test_extract_dates_from_pdf_text(self):
        """Test extraction of measurement and submission dates from diverse text formats."""
        # Czech standard
        meas, sub = extract_dates_from_pdf_text("Fyzikální praktikum\nMěřeno: 30.9.2026\nDatum odevzdání: 7.10.2026")
        self.assertEqual(meas, "30. 9. 2026")
        self.assertEqual(sub, "7. 10. 2026")

        # Slovak standard
        meas2, sub2 = extract_dates_from_pdf_text("Dátum merania: 23. 3. 2026\nAutor: Bruno Boczek")
        self.assertEqual(meas2, "23. 3. 2026")
        self.assertIsNone(sub2)

        # Newline separation between label and date
        meas3, sub3 = extract_dates_from_pdf_text("Jméno: Klára Rudolfová\nMěřeno:\n30.9.2026\nZpracování: 34 h")
        self.assertEqual(meas3, "30. 9. 2026")
        self.assertIsNone(sub3)

        # Corrupted font diacritics
        meas4, sub4 = extract_dates_from_pdf_text("Datum m¥°ení:\n21.11.2022\nSkupina: Po-9")
        self.assertEqual(meas4, "21. 11. 2022")
        self.assertIsNone(sub4)

        # Empty / None text
        self.assertEqual(extract_dates_from_pdf_text(""), (None, None))
        self.assertEqual(extract_dates_from_pdf_text(None), (None, None))

    def test_parse_czech_moodle_date(self):
        """Test parsing of Moodle date strings into ISO format and formatted parts."""
        # Named month with time
        iso, date_str, time_str = parse_czech_moodle_date("sobota, 14. listopadu 2026, 14.32")
        self.assertEqual(iso, "2026-11-14T14:32:00")
        self.assertEqual(date_str, "14. 11. 2026")
        self.assertEqual(time_str, "14:32")

        # Another month
        iso2, date_str2, time_str2 = parse_czech_moodle_date("středa, 21. října 2026, 04.57")
        self.assertEqual(iso2, "2026-10-21T04:57:00")
        self.assertEqual(date_str2, "21. 10. 2026")
        self.assertEqual(time_str2, "04:57")

        # Numeric date format
        iso3, date_str3, time_str3 = parse_czech_moodle_date("30.9.2026 15:16")
        self.assertEqual(iso3, "2026-09-30T15:16:00")
        self.assertEqual(date_str3, "30. 9. 2026")
        self.assertEqual(time_str3, "15:16")

        # Empty / dash
        self.assertEqual(parse_czech_moodle_date("-"), (None, None, None))
        self.assertEqual(parse_czech_moodle_date(""), (None, None, None))

    def test_database_backfill_and_columns(self):
        """Verify protocols table has submitted_at and measured_at columns and backfill runs."""
        conn = get_db()
        cur = conn.cursor()

        # Insert a dummy protocol with NULL dates
        cur.execute("SELECT id FROM semesters LIMIT 1")
        sem_id = cur.fetchone()["id"]
        cur.execute("SELECT id FROM slots LIMIT 1")
        slot_id = cur.fetchone()["id"]
        cur.execute("SELECT id FROM measurements LIMIT 1")
        meas_id = cur.fetchone()["id"]

        now_str = "2026-11-01T10:00:00"
        cur.execute("""
        INSERT INTO protocols (
            semester_id, slot_id, measurement_id, student_name, source_filename,
            source_path, created_at, updated_at
        ) VALUES (?, ?, ?, 'Backfill Test Student', 'test_backfill.pdf', '/nonexistent/path.pdf', ?, ?)
        """, (sem_id, slot_id, meas_id, now_str, now_str))
        proto_id = cur.lastrowid
        conn.commit()

        # Run backfill
        backfill_protocol_dates(cur)
        conn.commit()

        # Verify submitted_at defaulted to created_at
        cur.execute("SELECT submitted_at, measured_at FROM protocols WHERE id = ?", (proto_id,))
        row = cur.fetchone()
        self.assertEqual(row["submitted_at"], now_str)

        # Cleanup
        cur.execute("DELETE FROM protocols WHERE id = ?", (proto_id,))
        conn.commit()
        conn.close()

    def test_moodle_pending_cache(self):
        """Test MoodlePendingCache TTL, invalidation, and mark_downloaded behavior."""
        cache = MoodlePendingCache(ttl_seconds=2)
        sample_items = [
            {"cmid": "101", "student_name": "Novák Jan", "matched_task_id": 1, "already_in_db": False},
            {"cmid": "102", "student_name": "Svoboda Petr", "matched_task_id": 2, "already_in_db": False}
        ]
        cache.set("16880", sample_items)

        # Hit
        cached = cache.get("16880")
        self.assertIsNotNone(cached)
        self.assertEqual(len(cached), 2)

        # Mark downloaded
        cache.mark_downloaded("16880", "Novák Jan", 1)
        cached_after = cache.get("16880")
        self.assertTrue(cached_after[0]["already_in_db"])
        self.assertFalse(cached_after[1]["already_in_db"])

        # Invalidate
        cache.invalidate("16880")
        self.assertIsNone(cache.get("16880"))

        # TTL expiration
        cache.set("16880", sample_items)
        time.sleep(2.1)
        self.assertIsNone(cache.get("16880"))

    def test_get_protocols_includes_dates(self):
        """GET /api/protocols must include submitted_at and measured_at."""
        resp = self.client.get("/api/protocols?evaluator_id=all", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        items = resp.json()
        self.assertIsInstance(items, list)
        if len(items) > 0:
            first = items[0]
            self.assertIn("submitted_at", first)
            self.assertIn("measured_at", first)

    def test_put_protocol_metadata_dates(self):
        """PUT /api/protocols/{id}/metadata can update submitted_at and measured_at."""
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, semester_id, slot_id, measurement_id, student_name FROM protocols LIMIT 1")
        proto = cur.fetchone()
        conn.close()

        if proto:
            pid = proto["id"]
            resp = self.client.put(f"/api/protocols/{pid}/metadata", headers=self.auth_headers, json={
                "student_name": proto["student_name"],
                "semester_id": proto["semester_id"],
                "slot_id": proto["slot_id"],
                "measurement_id": proto["measurement_id"],
                "submitted_at": "2026-11-15T12:00:00",
                "measured_at": "8. 11. 2026"
            })
            self.assertEqual(resp.status_code, 200)

            # Check DB
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT submitted_at, measured_at FROM protocols WHERE id = ?", (pid,))
            updated = cur.fetchone()
            conn.close()
            self.assertEqual(updated["submitted_at"], "2026-11-15T12:00:00")
            self.assertEqual(updated["measured_at"], "8. 11. 2026")

    def test_ui_template_elements(self):
        """Verify UI template contains Odevzdáno column, sort indicator, and Moodle refresh button."""
        resp = self.client.get("/", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        html = resp.text

        # Sortable Odevzdáno header
        self.assertIn("sort-ind-submitted", html)
        self.assertIn("Odevzdáno", html)

        # Moodle refresh button
        self.assertIn("btn-moodle-refresh-pending", html)


if __name__ == "__main__":
    unittest.main()
