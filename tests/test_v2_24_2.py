import unittest
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ai_service import robust_json_loads, repair_json_latex, clean_decoded_obj, get_candidate_models
from app.models import AIChatResponse, AIChatMessage, AIAnnotationSuggestion
from app.version import VERSION

class TestPraktikaV2242(unittest.TestCase):
    def test_version_bump(self):
        self.assertTrue(VERSION >= "2.24.2")

    def test_gemini_4_hydrogen_candidates(self):
        """gemini-4-hydrogen must be supported in get_candidate_models."""
        models = get_candidate_models("gemini-4-hydrogen")
        self.assertEqual(models[0], "gemini-4-hydrogen")
        self.assertIn("gemini-4-hydrogen", models)
        self.assertIn("gemini-3.8-flash", models)

        # Default candidates list must also include gemini-4-hydrogen
        default_models = get_candidate_models()
        self.assertIn("gemini-4-hydrogen", default_models)

    def test_robust_json_loads_single_backslash_latex(self):
        """
        Tests that LaTeX math expressions with single backslashes in JSON (e.g. \\frac, \\right, \\text, \\theta)
        do not corrupt into formfeed (\\x0c), tab (\\t), or carriage return (\\r).
        """
        raw = r"""{
            "reply": "\\sqrt{v^2 - v_0^2} = v \\sqrt{1 - \frac{v_0^2}{v^2}} \\approx v \\left(1 - \frac{v_0^2}{2v^2} \right) = v - \frac{v_0^2}{2v}\n\\sigma_{\\text{abs}} \\approx \\sigma_{\\text{syst}} \\approx \\frac{v_0^2}{2v} \\propto \\frac{1}{v}",
            "annotations": [
                {
                    "page": 1,
                    "type": "highlight",
                    "search_text": "text",
                    "comment": "Chyba ve vzorci \frac{a}{b}"
                }
            ]
        }"""
        parsed = robust_json_loads(raw)
        reply = parsed["reply"]
        
        # Verify no formfeed (0x0c) or corrupted rac
        self.assertNotIn("\x0c", reply)
        self.assertIn(r"\frac", reply)
        self.assertIn(r"\right", reply)
        self.assertIn(r"\text", reply)
        self.assertIn(r"\sigma", reply)
        self.assertIn(r"\propto", reply)
        self.assertEqual(parsed["annotations"][0]["comment"], r"Chyba ve vzorci \frac{a}{b}")

    def test_robust_json_loads_double_backslash_latex(self):
        """Tests that properly double-escaped JSON is parsed completely intact."""
        raw = r"""{
            "reply": "\\sqrt{x} + \\frac{1}{2} + \\theta \\cdot \\tau",
            "scores": {"total": 8.5}
        }"""
        parsed = robust_json_loads(raw)
        self.assertIn(r"\sqrt{x}", parsed["reply"])
        self.assertIn(r"\frac{1}{2}", parsed["reply"])
        self.assertIn(r"\theta", parsed["reply"])

    def test_chat_response_model_fields(self):
        """AIChatResponse must include model_used and model attributes."""
        res = AIChatResponse(
            reply="Test answer",
            annotations=[],
            history=[],
            model_used="gemini-4-hydrogen",
            model="gemini-4-hydrogen"
        )
        self.assertEqual(res.model_used, "gemini-4-hydrogen")
        self.assertEqual(res.model, "gemini-4-hydrogen")

    def test_format_moodle_comment_html(self):
        """Verify plain text feedback comments are converted to clean HTML with <br> for deductions."""
        from app.moodle_service import format_moodle_comment_html
        raw = "Výsledky: 3 / 3\n\nDiskuze: 2.875 / 3\n-0.125b Spousta věcí < 5 &\nChyby: 2 / 2"
        res = format_moodle_comment_html(raw)
        # Must escape < and &
        self.assertIn("&lt; 5 &amp;", res)
        # Must convert \n to <br>
        self.assertIn("<br>", res)
        self.assertIn("<br>\n-0.125b", res)
        self.assertIn("<br>\n<br>\nDiskuze", res)

    def test_submit_moodle_grade_calls_upload_and_lock(self):
        """Verify submit_moodle_grade uploads feedback PDF to repository and locks draft submission."""
        import asyncio
        from unittest.mock import AsyncMock, patch, MagicMock
        from app.moodle_service import submit_moodle_grade

        mock_resp_grade = MagicMock()
        mock_resp_grade.text = 'name="files_999_filemanager" value="123456" data-assignmentid="888" sesskey="mock_sess_1"'

        mock_resp_up = MagicMock()
        mock_resp_up.status_code = 200

        mock_resp_ajax = MagicMock()
        mock_resp_ajax.json.return_value = [{"data": "saved"}]

        mock_resp_lock = MagicMock()
        mock_resp_lock.status_code = 200

        async def fake_get(url, *args, **kwargs):
            if "action=grade" in url:
                return mock_resp_grade
            elif "action=lock" in url:
                return mock_resp_lock
            return MagicMock(status_code=200, text="")

        async def fake_post(url, *args, **kwargs):
            if "repository_ajax.php" in url:
                return mock_resp_up
            elif "mod_assign_submit_grading_form" in url:
                return mock_resp_ajax
            return MagicMock(status_code=200, json=lambda: [{"data": "ok"}])

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(side_effect=fake_get)
        mock_client_instance.post = AsyncMock(side_effect=fake_post)
        mock_client_instance.__aenter__.return_value = mock_client_instance

        with patch("httpx.AsyncClient", return_value=mock_client_instance):
            res = asyncio.run(submit_moodle_grade(
                cmid="482838",
                userid=999,
                grade_letter="A",
                comment_text="Výborně\n-0.125b drobná chyba",
                pdf_bytes=b"%PDF-1.4 mock",
                pdf_filename="test.pdf",
                lock_submission=True,
                session_cookie="mock_cookie"
            ))
            self.assertTrue(res["success"])
            self.assertTrue(res["pdf_uploaded"])
            self.assertTrue(res["locked"])

            # Verify upload POST was made
            post_urls = [c[0][0] for c in mock_client_instance.post.call_args_list if c[0]]
            self.assertTrue(any("repository_ajax.php?action=upload" in u for u in post_urls))
            self.assertTrue(any("mod_assign_submit_grading_form" in u for u in post_urls))

            # Verify lock GET was made
            get_urls = [c[0][0] for c in mock_client_instance.get.call_args_list if c[0]]
            self.assertTrue(any("action=lock" in u and "userid=999" in u for u in get_urls))

    def test_css_and_js_compact_table_artifacts(self):
        """Verify CSS and JS include compact table styling, action dropdown and helper functions."""
        css_path = Path(__file__).resolve().parent.parent / "app/static/css/app.css"
        css_content = css_path.read_text(encoding="utf-8")
        self.assertIn(".btn-xs", css_content)
        self.assertIn(".action-dropdown", css_content)
        self.assertIn(".action-dropdown-menu", css_content)
        self.assertIn(".table-card table", css_content)

        js_path = Path(__file__).resolve().parent.parent / "app/static/js/app.js"
        js_content = js_path.read_text(encoding="utf-8")
        self.assertIn("toggleRowActionMenu", js_content)
        self.assertIn("closeAllActionMenus", js_content)

if __name__ == "__main__":
    unittest.main()
