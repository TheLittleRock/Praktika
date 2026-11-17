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

if __name__ == "__main__":
    unittest.main()
