# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""
Tests for DualLLMBackend — Phase 4 / G9 (v1.6.0).

All HTTP calls are intercepted via unittest.mock so no Ollama instance is needed.
"""

from __future__ import annotations
import json
import unittest
from io import BytesIO
from unittest.mock import MagicMock, patch

from npc_sim.llm.llm_backend import DualLLMBackend, LLMResponse


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _ollama_response(content: str) -> bytes:
    """Mimic Ollama /api/chat JSON wrapper."""
    return json.dumps({"message": {"role": "assistant", "content": content}}).encode()


def _mock_urlopen(reasoner_content: str, formatter_content: str):
    """
    Return a context-manager factory that alternates between two responses:
    first call → reasoner_content, second call → formatter_content.
    """
    calls = [0]

    class _FakeResp:
        def __init__(self, data: bytes):
            self._data = data

        def read(self):
            return self._data

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    def _urlopen(req, timeout=None):
        idx = calls[0]
        calls[0] += 1
        data = reasoner_content if idx == 0 else formatter_content
        return _FakeResp(_ollama_response(data))

    return _urlopen


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestDualLLMBackendHappyPath(unittest.TestCase):
    def test_dual_chain_happy_path(self):
        """Reasoner → valid CoT → Formatter → valid JSON → LLMResponse."""
        cot = "Tehdit yüksek, ama cesaretim beni ileriye itiyor. Saldırmalıyım."
        formatter_json = json.dumps({
            "reasoning": cot,
            "selected_action": {"action_id": "attack", "target_id": "wolf", "dialogue": None},
            "emotion": "Aggressive",
        })

        backend = DualLLMBackend(timeout=3.0)
        with patch("urllib.request.urlopen", side_effect=_mock_urlopen(cot, formatter_json)):
            resp = backend.call("npc_abc", '{"state": "test"}')

        self.assertIsInstance(resp, LLMResponse)
        self.assertEqual(resp.action_id, "attack")
        self.assertEqual(resp.npc_id, "npc_abc")       # injected post-parse
        self.assertEqual(resp.target_id, "wolf")
        self.assertEqual(resp.emotion, "Aggressive")
        self.assertTrue(resp.reasoning)   # non-empty


class TestDualLLMH6Fallback(unittest.TestCase):
    def test_reasoner_failure_triggers_h6_fallback(self):
        """If Reasoner emits JSON-like output, H6 gate fires and fallback takes over."""
        bad_cot = '{"action_id": "flee"}'   # Reasoner leaked JSON — triggers H6
        fallback_json = json.dumps({
            "npc_id": "npc_abc",
            "reasoning": "Fallback single-pass reasoning",
            "selected_action": {"action_id": "flee", "target_id": None, "dialogue": None},
            "emotion": "Fearful",
        })

        backend = DualLLMBackend(timeout=3.0)
        calls = [0]

        class _FakeResp:
            def __init__(self, data): self._data = data
            def read(self): return self._data
            def __enter__(self): return self
            def __exit__(self, *_): pass

        def _urlopen(req, timeout=None):
            idx = calls[0]; calls[0] += 1
            # First call = Reasoner (bad JSON cot), second call = Fallback
            data = bad_cot if idx == 0 else fallback_json
            return _FakeResp(_ollama_response(data))

        with patch("urllib.request.urlopen", side_effect=_urlopen):
            resp = backend.call("npc_abc", '{"state": "test"}')

        self.assertEqual(resp.action_id, "flee")
        # H6 fallback goes through OllamaBackend._parse which reads "selected_action"
        self.assertEqual(resp.npc_id, "npc_abc")

    def test_cot_too_short_triggers_fallback(self):
        """CoT under 50 chars should fail H6 validation → fallback."""
        backend = DualLLMBackend(timeout=3.0)
        self.assertFalse(backend._validate_cot("kısa"))
        self.assertFalse(backend._validate_cot(""))
        self.assertFalse(backend._validate_cot("{" + "x" * 60 + "}"))  # JSON-like

    def test_cot_too_long_fails_validation(self):
        self.assertFalse(DualLLMBackend._validate_cot("a" * 601))

    def test_valid_cot_passes_h6(self):
        cot = "Bu tehdit çok ciddi. Cesaretim beni ileri çekiyor ama sayıları fazla. Geri çekilmeliyim."
        self.assertTrue(DualLLMBackend._validate_cot(cot))


class TestDualLLMFormatterInvalidJSON(unittest.TestCase):
    def test_formatter_invalid_json_raises(self):
        """Formatter returning malformed JSON propagates as ValueError."""
        cot = "Tehdit var, saldırmam gerekiyor. Cesaretimle ilerliyorum."
        bad_fmt = "Bu JSON değil, sadece metin"

        backend = DualLLMBackend(timeout=3.0)
        with patch("urllib.request.urlopen", side_effect=_mock_urlopen(cot, bad_fmt)):
            with self.assertRaises((ValueError, json.JSONDecodeError)):
                backend.call("npc_xyz", '{"state": "test"}')


class TestDualLLMNpcIdInjection(unittest.TestCase):
    def test_npc_id_injected_post_parse(self):
        """npc_id must come from the call() parameter, not the Formatter JSON."""
        cot = "Açlık dayanılmaz oldu. Çantamdaki ekmeği yemeliyim. Başka şeye gerek yok."
        fmt = json.dumps({
            # Deliberately omit npc_id — Formatter schema doesn't include it
            "reasoning": cot,
            "selected_action": {"action_id": "eat", "target_id": None, "dialogue": None},
            "emotion": "Calm",
        })

        backend = DualLLMBackend(timeout=3.0)
        with patch("urllib.request.urlopen", side_effect=_mock_urlopen(cot, fmt)):
            resp = backend.call("npc_injected_id", '{"state": "test"}')

        self.assertEqual(resp.npc_id, "npc_injected_id")
        self.assertEqual(resp.action_id, "eat")


class TestDualLLMTimeout(unittest.TestCase):
    def test_http_error_propagates(self):
        """URLError from either stage bubbles up (queue handles and calls callback with error)."""
        import urllib.error

        backend = DualLLMBackend(timeout=1.0)
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
            with self.assertRaises(urllib.error.URLError):
                backend.call("npc_timeout", '{"state": "test"}')


if __name__ == "__main__":
    unittest.main()
