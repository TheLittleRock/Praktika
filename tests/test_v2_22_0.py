"""
Unit tests for Praktika v2.22.0:
- Version bump to 2.22.0
- Interactive Moodle login endpoints (start, status, cancel)
- Keep-Alive heartbeat endpoint and function (moodle_keepalive_ping)
- MoodleInteractiveLoginManager state machine and thread safety
- UI template elements for interactive login modal and session alert banner
"""

import unittest
import sys
import json
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from starlette.testclient import TestClient
import httpx

from app.version import VERSION
from app.main import app
from app.database import init_db, get_db
from app.moodle_service import (
    moodle_keepalive_ping,
    get_moodle_config,
    save_moodle_setting
)
from app.moodle_login_service import MoodleInteractiveLoginManager


class TestPraktikaV2220(unittest.TestCase):
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
        self.assertEqual(VERSION, "2.22.0")

    def test_interactive_login_endpoints_status_and_cancel(self):
        """Test GET /api/moodle/interactive-login/status and POST /api/moodle/interactive-login/cancel."""
        # Check initial status
        resp = self.client.get("/api/moodle/interactive-login/status", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("status", data)
        self.assertIn("message", data)

        # Cancel while idle
        cancel_resp = self.client.post("/api/moodle/interactive-login/cancel", headers=self.auth_headers)
        self.assertEqual(cancel_resp.status_code, 200)
        c_data = cancel_resp.json()
        self.assertIn("status", c_data)

    def test_interactive_login_manager_start_mock(self):
        """Test MoodleInteractiveLoginManager starting and state reporting without launching real browser."""
        mgr = MoodleInteractiveLoginManager.get_instance()
        with patch.object(mgr, "_run_login_pipeline") as mock_pipeline:
            res = mgr.start_login(moodle_url="https://moodle-vyuka.cvut.cz", course_id="16880")
            self.assertFalse(res.get("already_running"))
            self.assertEqual(res.get("status"), "starting")

            status = mgr.get_status()
            self.assertEqual(status["moodle_url"], "https://moodle-vyuka.cvut.cz")
            self.assertEqual(status["course_id"], "16880")

            # Cancel
            c_res = mgr.cancel()
            self.assertEqual(c_res["status"], "cancelled")

    def test_moodle_keepalive_ping_success(self):
        """Test moodle_keepalive_ping with mocked successful 200 response."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.headers = {}
            mock_get.return_value = mock_resp

            import asyncio
            alive, msg = asyncio.run(moodle_keepalive_ping(
                moodle_url="https://moodle-vyuka.cvut.cz",
                session_cookie="dummy_cookie_abc123"
            ))

            self.assertTrue(alive)
            self.assertIn("aktivní", msg)

    def test_moodle_keepalive_ping_expired_redirect(self):
        """Test moodle_keepalive_ping detecting expired session redirecting to login."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 302
            mock_resp.headers = {"location": "https://moodle-vyuka.cvut.cz/login/index.php"}
            mock_get.return_value = mock_resp

            import asyncio
            alive, msg = asyncio.run(moodle_keepalive_ping(
                moodle_url="https://moodle-vyuka.cvut.cz",
                session_cookie="expired_cookie_xyz"
            ))

            self.assertFalse(alive)
            self.assertIn("vypršela", msg)

    def test_moodle_keepalive_endpoint(self):
        """Test POST /api/moodle/keepalive endpoint."""
        with patch("app.main.moodle_keepalive_ping", new_callable=AsyncMock) as mock_ping:
            mock_ping.return_value = (True, "Relace je aktivní a byla úspěšně obnovena.")

            resp = self.client.post("/api/moodle/keepalive", headers=self.auth_headers)
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "ok")
            self.assertTrue(data["alive"])

    def test_ui_template_elements_for_interactive_login(self):
        """Verify that index.html contains the interactive login button, modal, and alert banner."""
        index_path = Path(__file__).resolve().parent.parent / "app" / "templates" / "index.html"
        html = index_path.read_text(encoding="utf-8")

        # Start button in settings
        self.assertIn("btn-start-interactive-moodle-login", html)
        self.assertIn("App.startInteractiveMoodleLogin()", html)

        # Interactive login modal
        self.assertIn("modal-moodle-interactive-login", html)
        self.assertIn("moodle-login-modal-title", html)
        self.assertIn("btn-cancel-moodle-login", html)

        # Session alert banner in Moodle modal
        self.assertIn("moodle-session-alert-banner", html)
        self.assertIn("Moodle relace vypršela nebo je neplatná", html)

        # Keep-alive button
        self.assertIn("App.triggerMoodleKeepalive()", html)


if __name__ == "__main__":
    unittest.main()
