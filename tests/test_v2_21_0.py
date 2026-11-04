"""
Unit tests for Praktika v2.21.0:
- Version bump to 2.21.0
- OpenAI-compatible LLM provider support (Groq Llama 3.3 70B, OpenRouter, DeepSeek, Ollama)
- Gemini 3.x model ecosystem stabilization and retirement of obsolete 1.5/2.x
- User assigned tasks ("Moje úlohy") endpoint GET/POST and DB persistence
- Moodle pending submissions filtering by "my_tasks"
- UI template elements for provider switching, presets, and assigned tasks modal
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
from app.ai_service import (
    get_candidate_models,
    get_ai_provider,
    get_openai_settings,
    call_openai_compatible
)
from app.moodle_service import fetch_pending_submissions


class TestPraktikaV2210(unittest.TestCase):
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
        self.admin_id = row["id"]

    def test_version_bump(self):
        self.assertEqual(VERSION, "2.21.0")

    def test_gemini_candidate_models_modern_only(self):
        """Only modern Gemini 3.x models must be included; obsolete 1.5 / 2.x models should be removed."""
        models = get_candidate_models("gemini-3.8-flash")
        self.assertIn("gemini-3.8-flash", models)
        self.assertIn("gemini-3.6-flash", models)
        self.assertIn("gemini-3.5-flash-lite", models)
        self.assertIn("gemini-3.1-flash-lite", models)

        for m in models:
            self.assertFalse(m.startswith("gemini-1.5"), f"Obsolete model found: {m}")
            self.assertFalse(m.startswith("gemini-2.0"), f"Obsolete model found: {m}")

    def test_user_assigned_tasks_endpoints(self):
        """Test GET and POST for /api/users/me/assigned-tasks."""
        # Test GET initial state
        resp = self.client.get("/api/users/me/assigned-tasks", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("assigned_ids", data)
        self.assertIn("measurements", data)
        self.assertIsInstance(data["assigned_ids"], list)
        self.assertIsInstance(data["measurements"], list)

        # Pick first two measurement IDs if available
        meas_ids = [m["id"] for m in data["measurements"][:2]] if data["measurements"] else [1, 2]

        # Test POST update
        post_resp = self.client.post(
            "/api/users/me/assigned-tasks",
            headers=self.auth_headers,
            json={"task_ids": meas_ids}
        )
        self.assertEqual(post_resp.status_code, 200)
        post_data = post_resp.json()
        self.assertEqual(post_data["status"], "ok")
        self.assertEqual(post_data["assigned_ids"], meas_ids)

        # Verify persisted via GET
        resp2 = self.client.get("/api/users/me/assigned-tasks", headers=self.auth_headers)
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.json()["assigned_ids"], meas_ids)

    def test_ai_settings_endpoint_with_provider(self):
        """Test GET and POST for /api/settings/ai with OpenAI-compatible configuration."""
        get_resp = self.client.get("/api/settings/ai", headers=self.auth_headers)
        self.assertEqual(get_resp.status_code, 200)
        data = get_resp.json()
        self.assertIn("ai_provider", data)
        self.assertIn("openai_base_url", data)
        self.assertIn("openai_model", data)

        # Test saving OpenAI settings
        post_payload = {
            "gemini_api_key": "AIzaSyTestGeminiKey",
            "ai_enabled": True,
            "model_name": "gemini-3.8-flash",
            "auto_analyze_on_upload": True,
            "ai_language": "cs",
            "ai_provider": "openai_compatible",
            "openai_base_url": "https://api.groq.com/openai/v1",
            "openai_api_key": "gsk_test1234567890",
            "openai_model": "llama-3.3-70b-versatile"
        }
        save_resp = self.client.post("/api/settings/ai", headers=self.auth_headers, json=post_payload)
        self.assertEqual(save_resp.status_code, 200)

        # Verify loaded settings
        get_resp2 = self.client.get("/api/settings/ai", headers=self.auth_headers)
        self.assertEqual(get_resp2.status_code, 200)
        data2 = get_resp2.json()
        self.assertEqual(data2["ai_provider"], "openai_compatible")
        self.assertEqual(data2["openai_model"], "llama-3.3-70b-versatile")
        self.assertTrue(data2["has_openai_key"])

    def test_openai_compatible_invocation_mock(self):
        """Test calling call_openai_compatible with mocked httpx response."""
        user = {
            "custom_ai_provider": "openai_compatible",
            "custom_openai_base_url": "https://api.groq.com/openai/v1",
            "custom_openai_api_key": "gsk_mock_test_key",
            "custom_openai_model": "llama-3.3-70b-versatile"
        }

        mock_response = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": json.dumps({"proposals": [], "summary": "Vše v pořádku"}, ensure_ascii=False)
                }
            }],
            "model": "llama-3.3-70b-versatile"
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_response
            mock_post.return_value = mock_resp

            import asyncio
            result = asyncio.run(call_openai_compatible(
                messages=[
                    {"role": "system", "content": "Jsi asistent fyzikálního praktika."},
                    {"role": "user", "content": "Analyzuj protokol."}
                ],
                user=user,
                json_mode=True
            ))

            self.assertEqual(result["model"], "llama-3.3-70b-versatile")
            self.assertIn("Vše v pořádku", result["content"])

    def test_moodle_pending_submissions_my_tasks_filtering(self):
        """Test fetch_pending_submissions filters by assigned_task_ids when cmid == 'my_tasks'."""
        import asyncio

        # Case 1: Empty assigned_task_ids returns empty list immediately
        res_empty = asyncio.run(fetch_pending_submissions(
            cmid="my_tasks",
            assigned_task_ids=[]
        ))
        self.assertEqual(res_empty, [])

        # Case 2: Assigned task ID that exists in measurements but no matching assignment in Moodle
        mock_assignments = [
            {"cmid": "1001", "name": "P1 – 01 - Vzduchová dráha", "is_protocol": True, "task_number": 1},
            {"cmid": "1002", "name": "P2 – 02 - Dynamika rotačního pohybu", "is_protocol": True, "task_number": 2}
        ]

        with patch("app.moodle_service.fetch_course_structure", new_callable=AsyncMock) as mock_struct, \
             patch("app.moodle_service.fetch_course_user_groups_map", new_callable=AsyncMock) as mock_maps, \
             patch("app.moodle_service.get_moodle_config") as mock_cfg:

            mock_cfg.return_value = {"moodle_session": "valid_cookie_123", "course_id": "16880", "moodle_url": "https://moodle-vyuka.cvut.cz"}
            mock_struct.return_value = {
                "course_id": "16880",
                "course_title": "Fyzikální praktikum",
                "assignments": mock_assignments,
                "groups": []
            }
            mock_maps.return_value = {"by_name": {}, "by_id": {}}

            # If user has only task number 99 (not in course assignments)
            res_none = asyncio.run(fetch_pending_submissions(
                cmid="my_tasks",
                assigned_task_ids=[99999]
            ))
            self.assertEqual(res_none, [])

    def test_index_html_v2210_ui_elements(self):
        """Verify that index.html contains the new provider selector, Groq preset, and 'Moje úlohy' modal."""
        index_path = Path(__file__).resolve().parent.parent / "app" / "templates" / "index.html"
        html = index_path.read_text(encoding="utf-8")

        # Provider radios & Groq button
        self.assertIn("ai-provider-radio", html)
        self.assertIn("Groq (Llama 3.3 70B", html)
        self.assertIn("ai-openai-base-url", html)
        self.assertIn("ai-openai-model-input", html)

        # Moodle task filter text updated
        self.assertIn("<option value=\"all\">Všechny úlohy</option>", html)
        self.assertIn("<option value=\"my_tasks\">⭐ Moje úlohy</option>", html)
        self.assertNotIn("Všechny protokoly P{n} s neohodnocenými pracemi", html)

        # Assigned tasks modal
        self.assertIn("id=\"modal-my-tasks\"", html)
        self.assertIn("btn-my-tasks-tab-FPRA1", html)
        self.assertIn("btn-my-tasks-tab-FPRA2", html)
        self.assertIn("btn-my-tasks-tab-ZFM2", html)


if __name__ == "__main__":
    unittest.main()
