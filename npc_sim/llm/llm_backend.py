# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Abstract LLM backend interface + Ollama implementation for locally hosted custom models.

Architecture:
    ILLMBackend  ← abstract base
    OllamaBackend ← primary (local custom model via /api/chat)
    MockBackend   ← for unit tests / fallback testing
"""

from __future__ import annotations
import json
import re
import time
import urllib.request
import urllib.error
from abc import ABC, abstractmethod

# Dual-LLM prompts — must match training SYSTEM_PROMPT_REASONER / _FORMATTER
_SYSTEM_PROMPT_REASONER = (
    "Sen bir ortaçağ simülasyonundaki NPC'nin iç ses motorusun.\n"
    "Sana NPC'nin anlık durumunu JSON olarak göndereceğim.\n"
    "Görevin: NPC'nin ne yapması gerektiğini ve NEDEN yapması gerektiğini\n"
    "3-5 cümlelik Türkçe iç monolog olarak yaz.\n"
    "ASLA JSON üretme. ASLA action_id adı kullanma. Sadece düşün.\n"
    "Kişilik özellikleri, hayatta kalma ihtiyaçları, tehdit algısı,\n"
    "duygusal durum, hafıza ve sosyal bağlamı değerlendir."
)

_SYSTEM_PROMPT_FORMATTER = (
    "Sen bir NPC simülasyonu için JSON dönüştürücüsün.\n"
    "Sana bir NPC'nin ne yapmak istediğini Türkçe olarak anlatacağım.\n"
    'Bunu aşağıdaki JSON şemasına dönüştür:\n'
    '{"reasoning":"<girdiyi kopyala>",'
    '"selected_action":{"action_id":"<listeden>","target_id":null,"dialogue":null},'
    '"emotion":"<tek kelime>"}\n'
    'valid_actions: ["eat","drink","sleep","flee","gather","heal",'
    '"attack","socialize","trade","work","pray","walk_to"]\n'
    "SADECE JSON yaz. Kod bloğu veya açıklama ekleme."
)


# ─────────────────────────────────────────────────────────────────────────────
# Response dataclass
# ─────────────────────────────────────────────────────────────────────────────

class LLMResponse:
    __slots__ = ("npc_id", "reasoning", "action_id", "target_id",
                 "dialogue", "emotion", "raw", "latency_ms")

    def __init__(self, npc_id: str, reasoning: str, action_id: str,
                 target_id: str | None = None, dialogue: str | None = None,
                 emotion: str | None = None, raw: str = "",
                 latency_ms: float = 0.0):
        self.npc_id = npc_id
        self.reasoning = reasoning
        self.action_id = action_id
        self.target_id = target_id
        self.dialogue = dialogue
        self.emotion = emotion
        self.raw = raw
        self.latency_ms = latency_ms

    def __repr__(self) -> str:
        return (f"[LLMResponse] npc={self.npc_id} action={self.action_id} "
                f"({self.latency_ms:.0f}ms)")


# ─────────────────────────────────────────────────────────────────────────────
# Abstract interface
# ─────────────────────────────────────────────────────────────────────────────

class ILLMBackend(ABC):
    """Contract for all LLM backends."""

    SYSTEM_PROMPT = (
        "You are the cognitive decision engine of an NPC in a civilisation simulation.\n"
        "I will send you the NPC's current state as JSON.\n"
        "Your task: produce exactly one action decision, returned as JSON.\n\n"
        "Rules:\n"
        "- action_id MUST be one of the values in valid_actions\n"
        "- reasoning: first-person inner monologue, 1-3 sentences\n"
        "- dialogue: fill only for socialize/trade actions, otherwise null\n"
        "- emotion: NPC's dominant emotional state right now (single word)\n"
        "- Return ONLY JSON — no code blocks, no explanation\n\n"
        "Decision priority (apply in strict order):\n"
        "1. If interrupt=true and a Threat percept exists:\n"
        "     - Brave / Aggressive trait AND fear < 0.5 → action_id = 'attack'\n"
        "     - Otherwise → action_id = 'flee'\n"
        "2. If hun > 0.75 AND food is in inventory → action_id = 'eat'\n"
        "3. If thi > 0.75 AND water is in inventory → action_id = 'drink'\n"
        "4. If hp < 30 AND medicine is in inventory → action_id = 'heal'\n"
        "5. All other cases: reason from context, personality (b5), and memories.\n\n"
        "Trait behaviour rules:\n"
        "- Brave / Loyal: will not flee from threats unless fear > 0.6 or hp < 20\n"
        "- Fearful / Anxious / Cautious: prefer flee or walk_to over attack\n"
        "- Aggressive: attack score is elevated; may attack even without interrupt\n"
        "- Devout: pray when stressed; prioritises Temple zone\n"
        "- Greedy: trade score is elevated; hoards food/gold\n\n"
        "Expected output format:\n"
        '{"npc_id":"...","reasoning":"...","selected_action":{"action_id":"...",'
        '"target_id":null,"dialogue":null},"emotion":"..."}'
    )

    @abstractmethod
    def call(self, npc_id: str, payload_json: str,
             timeout: float = 3.0) -> LLMResponse:
        """Send payload to LLM, return parsed response. Raises on error."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Health check — used before deciding whether to queue a request."""
        ...


# ─────────────────────────────────────────────────────────────────────────────
# Ollama backend  (local custom model)
# ─────────────────────────────────────────────────────────────────────────────

class OllamaBackend(ILLMBackend):
    """
    Communicates with a locally running Ollama server that hosts the custom
    fine-tuned NPC decision model.

    API: POST {base_url}/api/chat
    Body: {"model": ..., "messages": [...], "stream": false, "format": "json"}
    """

    def __init__(self, model: str = "hermes-lora",
                 base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._chat_url = f"{self.base_url}/api/chat"
        self._health_url = f"{self.base_url}/api/tags"

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(self._health_url, method="GET")
            with urllib.request.urlopen(req, timeout=1.0):
                return True
        except Exception:
            return False

    @staticmethod
    def _post_chat(
        model: str,
        messages: list[dict],
        chat_url: str,
        timeout: float,
        response_format: str | None = "json",
    ) -> tuple[str, str]:
        """POST to Ollama /api/chat. Returns (content, raw_str). Raises on HTTP error."""
        body_dict: dict = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"stop": ["<|eot_id|>", "<|end_of_text|>", "<|eot"]},
        }
        if response_format:
            body_dict["format"] = response_format
        body = json.dumps(body_dict, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            chat_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_bytes = resp.read()
        raw_str = raw_bytes.decode("utf-8")
        outer = json.loads(raw_str)
        content = outer.get("message", {}).get("content", raw_str)
        return content, raw_str

    def call(self, npc_id: str, payload_json: str,
             timeout: float = 3.0) -> LLMResponse:
        t0 = time.perf_counter()
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user",   "content": payload_json},
        ]
        content, raw_str = OllamaBackend._post_chat(
            self.model, messages, self._chat_url, timeout, response_format="json"
        )
        latency = (time.perf_counter() - t0) * 1000
        return self._parse(npc_id, content, raw_str, latency)

    def _parse(self, npc_id: str, content: str, raw: str,
               latency: float) -> LLMResponse:
        """Parse model output JSON → LLMResponse. Raises ValueError on schema error."""
        # Strip any EOS token artifacts that leaked past Ollama's stop list.
        # Mirrors the `stop` list configured on the chat request body above.
        content = re.sub(r'<\|eot_id\|>|<\|end_of_text\|>|<\|eot\b', '', content)
        content = content.strip()

        data = json.loads(content)
        sa = data.get("selected_action", {})
        action_id = sa.get("action_id") or data.get("action_id") or ""
        if not action_id:
            raise ValueError(f"Missing action_id in LLM response: {content[:200]}")
        return LLMResponse(
            npc_id=data.get("npc_id", npc_id),
            reasoning=data.get("reasoning", ""),
            action_id=action_id,
            target_id=sa.get("target_id"),
            dialogue=sa.get("dialogue"),
            emotion=data.get("emotion"),
            raw=raw,
            latency_ms=latency,
        )

    def __repr__(self) -> str:
        return f"[OllamaBackend] {self.model} @ {self.base_url}"


# ─────────────────────────────────────────────────────────────────────────────
# Dual-LLM backend  (Reasoner → CoT → Formatter → JSON) — G9 / v1.6.0
# ─────────────────────────────────────────────────────────────────────────────

class DualLLMBackend(ILLMBackend):
    """
    Two-stage pipeline:
      1. Reasoner (3B, port 11434) receives NPC state → Turkish CoT prose
      2. Formatter (1B-Instruct, port 11435) receives CoT → JSON LLMResponse

    H6 gate: if Reasoner output fails CoT validation (JSON-like, too short/long),
    falls back to single-pass OllamaBackend (Reasoner acting as combined model).

    npc_id is injected post-parse because the Formatter's training schema drops it
    (runtime always knows the id from the request payload).
    """

    def __init__(
        self,
        reasoner_model: str = "reasoner-lora-v5",
        reasoner_url: str = "http://localhost:11434",
        formatter_model: str = "formatter-lora-v5",
        formatter_url: str = "http://localhost:11435",
        timeout: float = 6.0,
    ):
        self.reasoner_model  = reasoner_model
        self.formatter_model = formatter_model
        self._reasoner_chat  = f"{reasoner_url.rstrip('/')}/api/chat"
        self._formatter_chat = f"{formatter_url.rstrip('/')}/api/chat"
        self._reasoner_health = f"{reasoner_url.rstrip('/')}/api/tags"
        self._timeout = timeout

        # Fallback backend: single-pass through Reasoner with JSON forced
        self._fallback = OllamaBackend(model=reasoner_model, base_url=reasoner_url)

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(self._reasoner_health, method="GET")
            with urllib.request.urlopen(req, timeout=1.0):
                return True
        except Exception:
            return False

    @staticmethod
    def _validate_cot(cot: str) -> bool:
        """H6 gate: CoT must be Turkish prose, not JSON, within 50-600 chars."""
        cot = cot.strip()
        return bool(cot) and 50 <= len(cot) <= 600 and not cot.startswith("{")

    def call(self, npc_id: str, payload_json: str,
             timeout: float | None = None) -> LLMResponse:
        t0 = time.perf_counter()
        timeout = timeout or self._timeout

        # ── Stage 1: Reasoner → Turkish CoT ────────────────────────────────
        reasoner_msgs = [
            {"role": "system", "content": _SYSTEM_PROMPT_REASONER},
            {"role": "user",   "content": payload_json},
        ]
        cot_text, _ = OllamaBackend._post_chat(
            self.reasoner_model, reasoner_msgs, self._reasoner_chat,
            timeout, response_format=None,   # CoT is prose, not JSON
        )
        cot_text = cot_text.strip()

        # ── H6: CoT validation ─────────────────────────────────────────────
        if not self._validate_cot(cot_text):
            # Reasoner leaked JSON or produced nonsense; single-pass fallback
            return self._fallback.call(npc_id, payload_json, timeout)

        # ── Stage 2: Formatter → JSON ──────────────────────────────────────
        formatter_msgs = [
            {"role": "system", "content": _SYSTEM_PROMPT_FORMATTER},
            {"role": "user",   "content": cot_text},
        ]
        json_text, raw_str = OllamaBackend._post_chat(
            self.formatter_model, formatter_msgs, self._formatter_chat,
            timeout, response_format="json",
        )
        latency = (time.perf_counter() - t0) * 1000

        # ── Parse Formatter output + inject npc_id ─────────────────────────
        json_text = re.sub(r'<\|eot_id\|>|<\|end_of_text\|>|<\|eot\b', '', json_text).strip()
        data = json.loads(json_text)
        sa = data.get("selected_action", {})
        action_id = sa.get("action_id") or data.get("action_id") or ""
        if not action_id:
            raise ValueError(f"DualLLM: missing action_id in Formatter output: {json_text[:200]}")

        return LLMResponse(
            npc_id=npc_id,                          # injected: not in Formatter schema
            reasoning=data.get("reasoning", cot_text),
            action_id=action_id,
            target_id=sa.get("target_id"),
            dialogue=sa.get("dialogue"),
            emotion=data.get("emotion"),
            raw=raw_str,
            latency_ms=latency,
        )

    def __repr__(self) -> str:
        return (f"[DualLLMBackend] reasoner={self.reasoner_model} "
                f"formatter={self.formatter_model}")


# ─────────────────────────────────────────────────────────────────────────────
# Mock backend  (deterministic, for tests)
# ─────────────────────────────────────────────────────────────────────────────

class MockBackend(ILLMBackend):
    """Returns a fixed canned response. Use for unit tests and CI."""

    def __init__(self, fixed_action: str = "walk_to"):
        self.fixed_action = fixed_action
        self.call_count = 0

    def is_available(self) -> bool:
        return True

    def call(self, npc_id: str, payload_json: str,
             timeout: float = 3.0) -> LLMResponse:
        self.call_count += 1
        return LLMResponse(
            npc_id=npc_id,
            reasoning=f"[Mock] Always selecting {self.fixed_action}.",
            action_id=self.fixed_action,
            emotion="Calm",
            raw="{}",
            latency_ms=0.1,
        )
