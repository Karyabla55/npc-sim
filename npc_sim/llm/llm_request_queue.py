# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Priority request queue for LLM calls.

H3 Fix — prevents API/VRAM flooding when many NPCs try to call LLM simultaneously.
All LLM calls are funnelled through this singleton queue, which:
  - Prioritises important NPCs (interrupt=0, focused=1, low-hp=2, normal=5, bg=10)
  - Caps concurrent workers (4 for remote APIs, 1 for local Ollama serial inference)
  - Drops overflow requests silently (NPC falls back to UtilityEvaluator that tick)
"""

from __future__ import annotations
import heapq
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Optional


class LLMRequest:
    """A single queued LLM call."""
    __slots__ = ("priority", "npc_id", "payload_json", "timeout",
                 "callback", "_seq")

    # sequence counter for stable heap ordering (same priority → FIFO)
    _counter = 0
    _lock = threading.Lock()

    def __init__(self, npc_id: str, payload_json: str, priority: int,
                 timeout: float, callback: Callable):
        self.npc_id = npc_id
        self.payload_json = payload_json
        self.priority = priority
        self.timeout = timeout
        self.callback = callback
        with LLMRequest._lock:
            LLMRequest._counter += 1
            self._seq = LLMRequest._counter

    def __lt__(self, other):
        if self.priority != other.priority:
            return self.priority < other.priority
        return self._seq < other._seq  # FIFO within same priority


# ── Priority constants ─────────────────────────────────────────────────────────
class Priority:
    INTERRUPT = 0    # High-threat / sudden HP drop
    FOCUSED   = 1    # NPC selected in UI
    LOW_HP    = 2    # HP < 30%
    NORMAL    = 5    # Regular LLM tick
    BACKGROUND = 10  # No active percepts, idle NPC


class LLMRequestQueue:
    """
    Thread-safe priority queue with a background worker pool.

    Usage:
        queue = LLMRequestQueue(backend, max_concurrent=1)
        queue.submit("npc_01", payload_json, Priority.INTERRUPT, timeout=3.0,
                     callback=lambda r, err: ...)
    """

    def __init__(self, backend, max_concurrent: int = 1,
                 max_queue_size: int = 64):
        self._backend = backend
        self._max_queue = max_queue_size
        self._heap: list[LLMRequest] = []
        self._heap_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(
            max_workers=max_concurrent,
            thread_name_prefix="llm_worker"
        )
        self._stats = {
            "submitted": 0, "executed": 0, "dropped": 0,
            "errors": 0, "total_latency_ms": 0.0,
        }
        self._stats_lock = threading.Lock()
        self._worker_future: Optional[Future] = None
        self._running = True
        # background dispatcher thread
        self._dispatcher = threading.Thread(
            target=self._dispatch_loop, daemon=True, name="llm_dispatcher")
        self._dispatcher.start()

    # ── Public API ─────────────────────────────────────────────────────────────

    def submit(self, npc_id: str, payload_json: str, priority: int,
               timeout: float, callback: Callable) -> bool:
        """
        Queue a request. Returns False (dropped) if queue is full.
        callback(response: LLMResponse | None, error: Exception | None)
        """
        with self._heap_lock:
            if len(self._heap) >= self._max_queue:
                with self._stats_lock:
                    self._stats["dropped"] += 1
                return False
            req = LLMRequest(npc_id, payload_json, priority, timeout, callback)
            heapq.heappush(self._heap, req)
            with self._stats_lock:
                self._stats["submitted"] += 1
        return True

    def get_stats(self) -> dict:
        with self._stats_lock:
            s = dict(self._stats)
        s["queue_depth"] = len(self._heap)
        avg = (s["total_latency_ms"] / s["executed"]) if s["executed"] else 0
        s["avg_latency_ms"] = round(avg, 1)
        return s

    def shutdown(self) -> None:
        self._running = False
        self._executor.shutdown(wait=False)

    # ── Internal ───────────────────────────────────────────────────────────────

    def _dispatch_loop(self) -> None:
        while self._running:
            req = self._pop_highest()
            if req is not None:
                self._executor.submit(self._execute, req)
            else:
                time.sleep(0.005)  # 5ms idle poll

    def _pop_highest(self) -> Optional[LLMRequest]:
        with self._heap_lock:
            if self._heap:
                return heapq.heappop(self._heap)
        return None

    def _execute(self, req: LLMRequest) -> None:
        t0 = time.perf_counter()
        try:
            response = self._backend.call(req.npc_id, req.payload_json, req.timeout)
            latency = (time.perf_counter() - t0) * 1000
            with self._stats_lock:
                self._stats["executed"] += 1
                self._stats["total_latency_ms"] += latency
            req.callback(response, None)
        except Exception as e:
            with self._stats_lock:
                self._stats["errors"] += 1
            req.callback(None, e)

    def __repr__(self) -> str:
        s = self.get_stats()
        return (f"[LLMRequestQueue] depth:{s['queue_depth']} "
                f"exec:{s['executed']} drop:{s['dropped']} "
                f"avg:{s['avg_latency_ms']}ms")
