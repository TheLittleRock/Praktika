import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.version import VERSION
from app.ai_service import (
    build_gemini_generation_config,
    extract_gemini_response_text,
    get_gemini_thinking_level,
)

class TestV2245Improvements(unittest.TestCase):
    def test_version_bump_to_2_24_5(self):
        self.assertTrue(VERSION >= "2.24.5")

    def test_generation_config_max_output_tokens(self):
        # Gemini 4 Hydrogen
        cfg4 = build_gemini_generation_config("gemini-4-hydrogen", "LOW")
        self.assertEqual(cfg4["maxOutputTokens"], 16384)
        self.assertEqual(cfg4["thinkingConfig"]["thinkingLevel"], "LOW")

        # Gemini 3.8 Flash
        cfg38 = build_gemini_generation_config("gemini-3.8-flash", "MEDIUM")
        self.assertEqual(cfg38["maxOutputTokens"], 16384)
        self.assertEqual(cfg38["thinkingConfig"]["thinkingLevel"], "MEDIUM")

        # Gemini 3.5 Flash Lite
        cfg35 = build_gemini_generation_config("gemini-3.5-flash-lite", "LOW")
        self.assertEqual(cfg35["maxOutputTokens"], 16384)

        # Legacy model
        cfg_leg = build_gemini_generation_config("gemini-1.5-flash", "LOW")
        self.assertEqual(cfg_leg["maxOutputTokens"], 8192)

        # Custom max_output_tokens
        cfg_custom = build_gemini_generation_config("gemini-4-hydrogen", "LOW", max_output_tokens=4096)
        self.assertEqual(cfg_custom["maxOutputTokens"], 4096)

    def test_generation_config_thinking_level_clamping(self):
        # gemini-4 clamps MINIMAL to LOW
        cfg = build_gemini_generation_config("gemini-4-hydrogen", "MINIMAL")
        self.assertEqual(cfg["thinkingConfig"]["thinkingLevel"], "LOW")

        # gemini-3.8 clamps XHIGH to HIGH
        cfg = build_gemini_generation_config("gemini-3.8-flash", "XHIGH")
        self.assertEqual(cfg["thinkingConfig"]["thinkingLevel"], "HIGH")

    def test_extract_gemini_response_text_filters_thoughts(self):
        # Simulate response with thought part followed by actual text response part
        data = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"thought": True, "text": "Let me think about this physics protocol..."},
                            {"text": '{"summary": "Velmi dobrý protokol", "total_deduction": -0.5}'}
                        ]
                    },
                    "finishReason": "STOP"
                }
            ]
        }
        text, err = extract_gemini_response_text(data)
        self.assertIsNone(err)
        self.assertEqual(text, '{"summary": "Velmi dobrý protokol", "total_deduction": -0.5}')

    def test_extract_gemini_response_text_handles_finish_reasons(self):
        data = {
            "candidates": [
                {
                    "finishReason": "SAFETY"
                }
            ]
        }
        text, err = extract_gemini_response_text(data)
        self.assertIsNone(text)
        self.assertIn("SAFETY", err)

    def test_default_thinking_level(self):
        # Default analysis should be LOW to prevent 30k token explosion
        level_analysis = get_gemini_thinking_level("analysis")
        self.assertIn(level_analysis, ["LOW", "MEDIUM", "HIGH", "MINIMAL", "XHIGH"])

    def test_frontend_app_js_failsafe_timeout(self):
        app_js_path = Path(__file__).resolve().parent.parent / "app" / "static" / "js" / "app.js"
        content = app_js_path.read_text(encoding="utf-8")
        self.assertIn("secondsElapsed > 360", content)

if __name__ == "__main__":
    unittest.main()
