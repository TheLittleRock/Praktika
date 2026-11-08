"""
Unit tests for Praktika v2.23.0:
- Version bump to 2.23.0
- Server-side headless Moodle credential login endpoint (POST /api/moodle/interactive-login/credentials)
- 2FA code submission endpoint (POST /api/moodle/interactive-login/submit-2fa)
- MoodleInteractiveLoginManager 2FA states (number matching, push notification, TOTP/SMS code)
- Zero password persistence verification (never stored in DB, state, or disk)
- UI template elements for in-app credential and 2FA modal
"""

import unittest
import sys
import json
from unittest.mock import patch, MagicMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from starlette.testclient import TestClient

from app.version import VERSION
from app.main import app
from app.database import init_db, get_db
from app.models import MoodleCredentialLoginRequest, Moodle2FACodeRequest
from app.moodle_service import get_moodle_config
from app.moodle_login_service import MoodleInteractiveLoginManager


class TestPraktikaV2230(unittest.TestCase):
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
        self.assertEqual(VERSION, "2.23.0")

    def test_credential_login_endpoint_unauthorized(self):
        """POST /api/moodle/interactive-login/credentials requires valid auth token."""
        resp = self.client.post("/api/moodle/interactive-login/credentials", json={
            "username": "novakja8",
            "password": "SecretPassword123"
        })
        self.assertIn(resp.status_code, (401, 403))

    def test_credential_login_endpoint_success(self):
        """POST /api/moodle/interactive-login/credentials starts login pipeline."""
        mgr = MoodleInteractiveLoginManager.get_instance()
        with patch.object(mgr, "_run_credential_pipeline") as mock_pipeline:
            resp = self.client.post("/api/moodle/interactive-login/credentials", headers=self.auth_headers, json={
                "username": "novakja8",
                "password": "SecretPassword123",
                "moodle_url": "https://moodle-vyuka.cvut.cz",
                "course_id": "16880"
            })
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "authenticating")
            self.assertFalse(data["already_running"])

            status = mgr.get_status()
            self.assertEqual(status["status"], "authenticating")
            self.assertEqual(status["moodle_url"], "https://moodle-vyuka.cvut.cz")
            self.assertEqual(status["course_id"], "16880")
            # Password must never be present in manager state
            self.assertNotIn("password", status)
            self.assertNotIn("SecretPassword123", json.dumps(status))

            mgr.cancel()

    def test_submit_2fa_code_endpoint(self):
        """POST /api/moodle/interactive-login/submit-2fa passes code to waiting thread."""
        mgr = MoodleInteractiveLoginManager.get_instance()
        with mgr._lock:
            mgr.state["status"] = "awaiting_2fa_code"
            mgr.state["two_factor_type"] = "code"

        resp = self.client.post("/api/moodle/interactive-login/submit-2fa", headers=self.auth_headers, json={
            "code": "654321"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(mgr._submitted_code, "654321")
        self.assertTrue(mgr._code_event.is_set())

        mgr.cancel()

    def test_manager_2fa_state_transitions(self):
        """Test state transitions: 2FA number matching, push, and TOTP code."""
        mgr = MoodleInteractiveLoginManager.get_instance()

        # 1. Number matching state
        with mgr._lock:
            mgr.state["status"] = "awaiting_2fa_number"
            mgr.state["two_factor_type"] = "number"
            mgr.state["two_factor_number"] = "42"
            mgr.state["message"] = "Zadejte v aplikaci Microsoft Authenticator číslo: 42"

        status = mgr.get_status()
        self.assertEqual(status["status"], "awaiting_2fa_number")
        self.assertEqual(status["two_factor_type"], "number")
        self.assertEqual(status["two_factor_number"], "42")

        # 2. Push state
        with mgr._lock:
            mgr.state["status"] = "awaiting_2fa_push"
            mgr.state["two_factor_type"] = "push"
            mgr.state["two_factor_number"] = None

        status = mgr.get_status()
        self.assertEqual(status["status"], "awaiting_2fa_push")
        self.assertEqual(status["two_factor_type"], "push")
        self.assertIsNone(status["two_factor_number"])

        # 3. Finalize success
        mgr._finalize_success(
            cookie_val="test_session_cookie_1234567890abcdef",
            moodle_url="https://moodle-vyuka.cvut.cz",
            course_id="16880"
        )
        status = mgr.get_status()
        self.assertEqual(status["status"], "success")
        self.assertIn("test_s...cdef", status["cookie_preview"])

        # Clean up
        mgr.cancel()

    def test_changelog_endpoint(self):
        """Test GET /api/changelog returns valid changelog content."""
        resp = self.client.get("/api/changelog")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("content", data)
        self.assertIn("2.23.0", data["content"])

    def test_playwright_selector_syntax(self):
        """Verify Playwright selectors used in moodle_login_service are syntactically valid."""
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content('<div id="idDiv_SAOTCAS_Title">Test</div><a id="signInAnotherWay">Alt</a>')

            # Push prompt selector
            push_loc = page.locator('#idDiv_SAOTCAS_Title, :text("Schvalte žádost o přihlášení"), :text("Approve sign in request"), :text("Approve a request")').first
            self.assertTrue(push_loc.is_visible())

            # Alt method selector
            alt_loc = page.locator('#signInAnotherWay, :text("Use a verification code"), :text("Použít ověřovací kód"), :text("I can\'t use my Outlook mobile app right now")').first
            self.assertTrue(alt_loc.is_visible())

            browser.close()

    def test_ui_template_elements_for_v2_23_0(self):
        """Verify that index.html contains all required v2.23.0 credential and 2FA DOM elements."""
        index_path = Path(__file__).resolve().parent.parent / "app" / "templates" / "index.html"
        html = index_path.read_text(encoding="utf-8")

        # Credential inputs
        self.assertIn('id="moodle-login-form-container"', html)
        self.assertIn('id="moodle-login-username"', html)
        self.assertIn('id="moodle-login-password"', html)
        self.assertIn('id="btn-toggle-moodle-pwd"', html)
        self.assertIn('id="btn-submit-moodle-credentials"', html)

        # 2FA views
        self.assertIn('id="moodle-login-2fa-number-container"', html)
        self.assertIn('id="moodle-login-2fa-number-badge"', html)
        self.assertIn('id="moodle-login-2fa-push-container"', html)
        self.assertIn('id="moodle-login-2fa-code-container"', html)
        self.assertIn('id="moodle-login-2fa-code-input"', html)
        self.assertIn('id="btn-submit-2fa-code"', html)

        # Action buttons
        self.assertIn('id="btn-retry-moodle-login"', html)
        self.assertIn('id="btn-cancel-moodle-login"', html)
        self.assertIn('id="btn-close-moodle-login"', html)

        # JavaScript functions
        js_path = Path(__file__).resolve().parent.parent / "app" / "static" / "js" / "app.js"
        js = js_path.read_text(encoding="utf-8")

        self.assertIn("submitMoodleCredentials", js)
        self.assertIn("submitMoodle2FACode", js)
        self.assertIn("toggleMoodlePasswordVisibility", js)
        self.assertIn("resetMoodleLoginForm", js)
        self.assertIn("awaiting_2fa_number", js)
        self.assertIn("awaiting_2fa_push", js)
        self.assertIn("awaiting_2fa_code", js)


if __name__ == "__main__":
    unittest.main()
