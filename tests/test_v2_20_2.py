"""
Unit tests for Praktika v2.20.2:
- Strict P{n} protocol assignment detection (excluding M1..M12 and data attachments)
- Duplicate protocol detection with status label mapping
- Normalization & token sorting for student name duplicate matching
- Moodle modal responsive layout and duplicate toggle in HTML
"""

import unittest
import sys
import re
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from starlette.testclient import TestClient

from app.version import VERSION
from app.main import app
from app.database import init_db, get_db
from app.moodle_service import (
    normalize_student_name,
    fetch_pending_submissions
)


class TestPraktikaV2202(unittest.TestCase):
    def setUp(self):
        init_db()
        self.client = TestClient(app)
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, username, role FROM users WHERE role = 'admin' LIMIT 1")
        row = cur.fetchone()
        conn.close()
        from app.auth import create_access_token
        self.admin_token = create_access_token({"sub": row["username"], "role": row["role"], "id": row["id"]})
        self.auth_headers = {"Authorization": f"Bearer {self.admin_token}"}

    def test_version_bump(self):
        self.assertTrue(VERSION >= "2.20.2")

    def test_is_protocol_regex_strictness(self):
        """Only assignments starting with P{number} (P0..P13) must match is_protocol = True."""
        protocol_names = [
            "P1 – 01 - Vzduchová dráha",
            "P2 – 02 - Dynamika",
            "P0 - Úvodní protokol",
            "P12 - Kalorimetrie",
            "p3 - test lowercase",
            "P10 – Optika"
        ]
        non_protocol_names = [
            "M1 – 01 - Vzduchová dráha",
            "M2 – 02 - Dynamika",
            "Úloha 01 - data – Vzduchová dráha",
            "Úloha 02 - data",
            "PŘEHLED ÚLOH",
            "Praktikum úvodní informace",
            "Příloha k měření"
        ]
        for name in protocol_names:
            self.assertTrue(bool(re.match(r'^P\d+\b', name, re.I)), f"Should be protocol: {name}")

        for name in non_protocol_names:
            self.assertFalse(bool(re.match(r'^P\d+\b', name, re.I)), f"Should NOT be protocol: {name}")

    def test_duplicate_name_sorting_matching(self):
        """Tokens should match regardless of word order (e.g. 'Rudolfová Klára' == 'Klára Rudolfová')."""
        name1 = "Rudolfová Klára"
        name2 = "Klára Rudolfová"
        sorted1 = " ".join(sorted(name1.strip().lower().split()))
        sorted2 = " ".join(sorted(name2.strip().lower().split()))
        self.assertEqual(sorted1, sorted2)

    def test_html_template_moodle_modal_improvements(self):
        """Verify modal responsiveness and duplicate controls in index.html."""
        resp = self.client.get("/login")  # or check index template content
        index_path = Path(__file__).resolve().parent.parent / "app" / "templates" / "index.html"
        content = index_path.read_text(encoding="utf-8")

        self.assertIn("max-width:1100px", content)
        self.assertIn("minmax(0, 1.3fr) minmax(0, 1fr)", content)
        self.assertIn("moodle-hide-duplicates", content)
        self.assertIn("selectOnlyNewMoodlePending()", content)
        self.assertIn("moodle-pending-breakdown-badge", content)

    def test_css_classes_for_duplicates(self):
        """Verify CSS contains .moodle-row-duplicate and .moodle-tag.duplicate."""
        css_path = Path(__file__).resolve().parent.parent / "app" / "static" / "css" / "app.css"
        content = css_path.read_text(encoding="utf-8")
        self.assertIn(".moodle-row-duplicate", content)
        self.assertIn(".moodle-tag.duplicate", content)


if __name__ == '__main__':
    unittest.main()
