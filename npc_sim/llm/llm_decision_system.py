# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""LLMDecisionSystem: drop-in replacement for DecisionSystem using a local LLM.

Implements all 4 hardening mechanisms:
  H1 - Semantic spatial context via WorldRegistry (in NPCSerializer)
  H2 - Event-driven interrupt: skips tick counter on high-threat or sudden HP drop
  H3 - Priority queue via LLMRequestQueue (avoids VRAM/API flooding)
  H4 - Guided one-shot retry before falling back to UtilityEvaluator
"""

from __future__ import annotations
import json
import threading
import time
from npc_sim.decisions.action import IAction
from npc_sim.decisions.action_library import ActionLibrary
from npc_sim.decisions.action_context import ActionContext
from npc_sim.decisions.utility_evaluator import UtilityEvaluator
from npc_sim.llm.llm_backend import ILLMBackend, LLMResponse
from npc_sim.llm.llm_request_queue import LLMRequestQueue, Priority
from npc_sim.llm.npc_serializer import NPCSerializer


class LLMDecisionSystem:
    """
    Per-NPC LLM-driven decision system.
    On each tick it checks whether to call the LLM (tick counter / interrupt).
    The LLM call is async (queued). Until response arrives, UtilityEvaluator
    fills in so the NPC never freezes.
    """

    def __init__(self, library: ActionLibrary, backend: ILLMBackend,
                 queue: LLMRequestQueue, serializer: NPCSerializer,
                 evaluator: UtilityEvaluator = None,
                 llm_tick_every: int = 5,
                 timeout_seconds: float = 3.0,
                 interrupt_threat_threshold: float = 0.8,
                 interrupt_hp_drop: float = 15.0):

        self._library = library
        self._backend = backend
        self._queue = queue
        self._serializer = serializer
        self._evaluator = evaluator or UtilityEvaluator()

        # Config
        self._llm_tick_every = llm_tick_every  # kept for API compat, no longer used
        self._timeout = timeout_seconds
        self._interrupt_threat = interrupt_threat_threshold
        self._interrupt_hp_drop = interrupt_hp_drop

        # Per-NPC state (accessed from multiple threads)
        self._last_hp: float = -1.0
        self._pending: bool = False        # LLM call in flight
        self._pending_lock = threading.Lock()

        # Last LLM result (applied next tick if arrived)
        self._pending_response: LLMResponse | None = None
        self._pending_action_id: str | None = None

        # Diagnostics
        self.llm_call_count: int = 0
        self.fallback_count: int = 0
        self.retry_count: int = 0

        # Last decision for UI
        self.last_selected_action: IAction | None = None
        self.last_reasoning: str = ""
        self.last_dialogue: str | None = None
        self.last_emotion: str | None = None
        self.last_score: float = 0.0
        self.llm_active: bool = False

    # ── Helper: is this a focused NPC? ────────────────────────────────────────
    @property
    def focused(self) -> bool:
        return self._focused

    @focused.setter
    def focused(self, v: bool):
        self._focused = v

    _focused: bool = False

    # ── Main tick ─────────────────────────────────────────────────────────────

    def tick(self, ctx: ActionContext) -> IAction | None:
        npc = ctx.self_npc

        # Apply any pending LLM result from previous async call
        action = self._apply_pending(ctx)

        # Decide whether to fire a new LLM call this tick
        interrupt = self._check_interrupt(ctx)
        if interrupt:
            self._tick_counter = 0       # H2: reset counter, call immediately

        if self._should_call_llm(interrupt):
            self._fire_llm_call(npc, ctx, interrupt)

        # Update HP tracking for next interrupt check
        self._last_hp = npc.vitals.health

        # If we got an LLM action this tick, execute it
        if action is not None:
            action.execute(ctx)
            self.last_selected_action = action
            self.llm_active = True
            return action

        # Fall back to UtilityEvaluator for this tick
        self.fallback_count += 1
        self.llm_active = False
        return self._utility_fallback(ctx)

    # ── Interrupt detection (H2) ──────────────────────────────────────────────

    def _check_interrupt(self, ctx: ActionContext) -> bool:
        # High-threat stimulus
        threat = ctx.get_top_percept("Threat")
        if threat and threat.threat_level >= self._interrupt_threat:
            return True
        # Sudden HP drop (took damage since last tick)
        if (self._last_hp > 0 and
                (self._last_hp - ctx.self_npc.vitals.health) >= self._interrupt_hp_drop):
            return True
        return False

    def _should_call_llm(self, interrupt: bool) -> bool:
        """LLM is only called on explicit triggers (H2 interrupt). Never on a timer."""
        with self._pending_lock:
            if self._pending:
                return False   # already one in flight
        return interrupt

    # ── Fire async LLM request (H3) ───────────────────────────────────────────

    def _fire_llm_call(self, npc, ctx: ActionContext, interrupt: bool) -> None:
        payload = self._serializer.build_payload(npc, ctx, interrupt)
        priority = self._compute_priority(ctx, interrupt)

        with self._pending_lock:
            self._pending = True

        ok = self._queue.submit(
            npc_id=npc.identity.npc_id,
            payload_json=payload,
            priority=priority,
            timeout=self._timeout,
            callback=self._on_response,
        )
        if not ok:
            # Queue full — release pending flag, will fall back this tick
            with self._pending_lock:
                self._pending = False
            self.fallback_count += 1

        self.llm_call_count += 1

    def _compute_priority(self, ctx: ActionContext, interrupt: bool) -> int:
        if interrupt:
            return Priority.INTERRUPT
        if self._focused:
            return Priority.FOCUSED
        if ctx.self_npc.vitals.health < ctx.self_npc.vitals.max_health * 0.3:
            return Priority.LOW_HP
        if not ctx.active_percepts:
            return Priority.BACKGROUND
        return Priority.NORMAL

    # ── Response callback (runs in worker thread) ──────────────────────────────

    def _on_response(self, response: LLMResponse | None, error: Exception | None) -> None:
        with self._pending_lock:
            self._pending = False

        if error is not None or response is None:
            # Failed — will fallback next tick
            return

        # Validate action_id is in library
        known = {a.action_id for a in self._library.get_all()}
        if response.action_id not in known:
            # H4: guided retry
            corrected = self._guided_retry(response)
            if corrected is None:
                return   # fallback
            response = corrected

        self._pending_response = response

    # ── Apply pending response ─────────────────────────────────────────────────

    def _apply_pending(self, ctx: ActionContext) -> IAction | None:
        resp = self._pending_response
        if resp is None:
            return None
        self._pending_response = None

        # Resolve action_id → IAction
        for action in self._library.get_all():
            if action.action_id == resp.action_id:
                if action.is_valid(ctx):
                    self.last_reasoning = resp.reasoning or ""
                    self.last_dialogue = resp.dialogue
                    self.last_emotion = resp.emotion
                    return action
        return None

    # ── H4: Guided retry ──────────────────────────────────────────────────────

    def _guided_retry(self, bad_resp: LLMResponse) -> LLMResponse | None:
        self.retry_count += 1
        known = [a.action_id for a in self._library.get_all()]
        correction_prompt = (
            f"Geçersiz action_id: '{bad_resp.action_id}'. "
            f"Yalnızca şu listeden birini seç: {known}. "
            f"Sadece JSON döndür, başka bir şey ekleme."
        )
        try:
            resp = self._backend.call(bad_resp.npc_id, correction_prompt,
                                      timeout=self._timeout)
            if resp.action_id in {a.action_id for a in self._library.get_all()}:
                return resp
        except Exception:
            pass
        return None

    # ── UtilityEvaluator fallback ──────────────────────────────────────────────

    def _utility_fallback(self, ctx: ActionContext) -> IAction | None:
        best_action = None
        best_score = 0.0
        for action in self._library.get_all():
            score = self._evaluator.evaluate(action, ctx)
            if score > best_score:
                best_score = score
                best_action = action
        if best_action is not None:
            best_action.execute(ctx)
            self.last_selected_action = best_action
            self.last_score = best_score
        return best_action

    def __repr__(self) -> str:
        mode = "LLM" if self.llm_active else "Utility"
        return (f"[LLMDecisionSystem] mode:{mode} calls:{self.llm_call_count} "
                f"fallbacks:{self.fallback_count} retries:{self.retry_count}")
