import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.version import VERSION
from app.ai_service import (
    build_gemini_generation_config,
    get_key_tiers_to_try,
    extract_gemini_response_text,
    get_gemini_api_key,
    get_gemini_paid_key,
    get_gemini_key_mode,
    save_gemini_key_mode,
    save_gemini_api_key,
    save_gemini_paid_key,
    get_gemini_thinking_level,
    save_gemini_thinking_level,
    analyze_protocol
)
from app.models import AIAnalysisResult, AIChatResponse, AISettingsRequest
from app.main import _is_valid_new_key

class TestV2243Improvements(unittest.TestCase):
    def test_version_bump(self):
        self.assertTrue(VERSION >= "2.24.3")

    def test_build_gemini_generation_config_gemini4(self):
        # Gemini 4: supports LOW, MEDIUM, HIGH, XHIGH. Clamps MINIMAL -> LOW. Omits temperature.
        cfg_min = build_gemini_generation_config("gemini-4-hydrogen", "MINIMAL")
        self.assertEqual(cfg_min["thinkingConfig"]["thinkingLevel"], "LOW")
        self.assertNotIn("temperature", cfg_min)

        cfg_xhigh = build_gemini_generation_config("gemini-4-hydrogen", "XHIGH")
        self.assertEqual(cfg_xhigh["thinkingConfig"]["thinkingLevel"], "XHIGH")
        self.assertNotIn("temperature", cfg_xhigh)

    def test_build_gemini_generation_config_gemini38(self):
        # Gemini 3.8: clamps MINIMAL -> LOW, XHIGH -> HIGH. Omits temperature.
        cfg_min = build_gemini_generation_config("gemini-3.8-flash", "MINIMAL")
        self.assertEqual(cfg_min["thinkingConfig"]["thinkingLevel"], "LOW")
        self.assertNotIn("temperature", cfg_min)

        cfg_xhigh = build_gemini_generation_config("gemini-3.8-flash", "XHIGH")
        self.assertEqual(cfg_xhigh["thinkingConfig"]["thinkingLevel"], "HIGH")
        self.assertNotIn("temperature", cfg_xhigh)

        cfg_med = build_gemini_generation_config("gemini-3.8-flash", "MEDIUM")
        self.assertEqual(cfg_med["thinkingConfig"]["thinkingLevel"], "MEDIUM")
        self.assertNotIn("temperature", cfg_med)

    def test_build_gemini_generation_config_gemini36_and_35(self):
        # Gemini 3.6 & 3.5: supports MINIMAL, LOW, MEDIUM, HIGH. Clamps XHIGH -> HIGH.
        cfg_min = build_gemini_generation_config("gemini-3.6-flash", "MINIMAL")
        self.assertEqual(cfg_min["thinkingConfig"]["thinkingLevel"], "MINIMAL")
        self.assertNotIn("temperature", cfg_min)

        cfg_xhigh = build_gemini_generation_config("gemini-3.5-flash-lite", "XHIGH")
        self.assertEqual(cfg_xhigh["thinkingConfig"]["thinkingLevel"], "HIGH")
        self.assertNotIn("temperature", cfg_xhigh)

    def test_get_key_tiers_to_try(self):
        with patch("app.ai_service.get_gemini_api_key", return_value="FREE_KEY_123"), \
             patch("app.ai_service.get_gemini_paid_key", return_value="PAID_KEY_456"):

            with patch("app.ai_service.get_gemini_key_mode", return_value="free_then_paid"):
                tiers = get_key_tiers_to_try()
                self.assertEqual(tiers, [("free", "FREE_KEY_123"), ("paid", "PAID_KEY_456")])

            with patch("app.ai_service.get_gemini_key_mode", return_value="free_only"):
                tiers = get_key_tiers_to_try()
                self.assertEqual(tiers, [("free", "FREE_KEY_123")])

            with patch("app.ai_service.get_gemini_key_mode", return_value="paid_only"):
                tiers = get_key_tiers_to_try()
                self.assertEqual(tiers, [("paid", "PAID_KEY_456")])

            # Custom key overrides
            tiers_custom = get_key_tiers_to_try(custom_key="CUSTOM_KEY_789")
            self.assertEqual(tiers_custom, [("custom", "CUSTOM_KEY_789")])

    def test_extract_gemini_response_text(self):
        # Valid response
        valid_data = {
            "candidates": [{
                "content": {
                    "parts": [{"text": '{"reply": "Ahoj"}'}]
                },
                "finishReason": "STOP"
            }]
        }
        text, err = extract_gemini_response_text(valid_data)
        self.assertEqual(text, '{"reply": "Ahoj"}')
        self.assertIsNone(err)

        # MAX_TOKENS error
        max_tokens_data = {
            "candidates": [{
                "finishReason": "MAX_TOKENS"
            }]
        }
        text, err = extract_gemini_response_text(max_tokens_data)
        self.assertIsNone(text)
        self.assertIn("MAX_TOKENS", err)

        # SAFETY block error
        safety_data = {
            "candidates": [{
                "finishReason": "SAFETY"
            }]
        }
        text, err = extract_gemini_response_text(safety_data)
        self.assertIsNone(text)
        self.assertIn("SAFETY", err)

        # Blocked prompt feedback
        blocked_feedback = {
            "promptFeedback": {"blockReason": "PROHIBITED_CONTENT"}
        }
        text, err = extract_gemini_response_text(blocked_feedback)
        self.assertIsNone(text)
        self.assertIn("PROHIBITED_CONTENT", err)

    def test_is_valid_new_key(self):
        # Empty or None should not update
        self.assertFalse(_is_valid_new_key(None))
        self.assertFalse(_is_valid_new_key(""))
        self.assertFalse(_is_valid_new_key("   "))

        # Masked strings should not overwrite
        self.assertFalse(_is_valid_new_key("AIzaSy...4xyz"))
        self.assertFalse(_is_valid_new_key("***"))
        self.assertFalse(_is_valid_new_key("••••••••"))

        # Real new key
        self.assertTrue(_is_valid_new_key("AIzaSyD-RandomNewApiKey123456789"))

    def test_models_support_new_fields(self):
        result = AIAnalysisResult(
            protocol_id=1,
            scores={"total_points": 8.0},
            deductions=[],
            annotations=[],
            summary="Test summary",
            key_tier_used="free",
            thinking_level_used="MEDIUM"
        )
        self.assertEqual(result.key_tier_used, "free")
        self.assertEqual(result.thinking_level_used, "MEDIUM")

        chat_resp = AIChatResponse(
            reply="Test reply",
            annotations=[],
            history=[],
            model_used="gemini-4-hydrogen",
            key_tier_used="paid",
            thinking_level_used="HIGH",
            fallback_note="Záložní klíč"
        )
        self.assertEqual(chat_resp.key_tier_used, "paid")
        self.assertEqual(chat_resp.thinking_level_used, "HIGH")
        self.assertEqual(chat_resp.fallback_note, "Záložní klíč")

if __name__ == "__main__":
    unittest.main()
