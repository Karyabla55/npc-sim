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
import time
import urllib.request
import urllib.error
from abc import ABC, abstractmethod


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
        "Sen bir medeniyet simülasyonundaki NPC'nin bilişsel karar motorusun.\n"
        "Sana NPC'nin anlık durumunu JSON formatında göndereceğim.\n"
        "Görevin: Yalnızca tek bir eylem kararı üret, JSON formatında döndür.\n"
        "Kurallar:\n"
        "- action_id MUTLAKA valid_actions listesindeki değerlerden biri olmalıdır\n"
        "- reasoning: birinci şahıs iç monolog, 1-3 cümle\n"
        "- dialogue: yalnızca socialize/trade eylemlerinde doldur, diğerlerinde null\n"
        "- emotion: NPC'nin şu anki baskın duygu durumu (tek kelime)\n"
        "- Yanıtın SADECE JSON olsun — kod bloğu, açıklama yok\n"
        "Beklenen format:\n"
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

    def call(self, npc_id: str, payload_json: str,
             timeout: float = 3.0) -> LLMResponse:
        t0 = time.perf_counter()

        body = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": payload_json},
            ],
            "stream": False,
            "format": "json",
        }, ensure_ascii=False).encode("utf-8")

        req = urllib.request.Request(
            self._chat_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_bytes = resp.read()

        latency = (time.perf_counter() - t0) * 1000
        raw_str = raw_bytes.decode("utf-8")
        outer = json.loads(raw_str)

        # Ollama wraps response in {"message": {"content": "..."}}
        content = outer.get("message", {}).get("content", raw_str)
        return self._parse(npc_id, content, raw_str, latency)

    def _parse(self, npc_id: str, content: str, raw: str,
               latency: float) -> LLMResponse:
        """Parse model output JSON → LLMResponse. Raises ValueError on schema error."""
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
