# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""C4 / #18: interrupt preempts in-flight lower-priority LLM requests."""

import threading
import time
from npc_sim.llm.llm_backend import LLMResponse
from npc_sim.llm.llm_request_queue import LLMRequestQueue, Priority


class _BlockingBackend:
    """A backend whose call() blocks on a barrier so we can race submissions."""

    def __init__(self):
        self._enter = threading.Event()
        self._release = threading.Event()

    def call(self, npc_id, payload_json, timeout):
        self._enter.set()
        self._release.wait(timeout=5.0)
        return LLMResponse(
            npc_id=npc_id, reasoning="r", action_id="work", target_id=None,
            dialogue=None, emotion=None, raw="{}", latency_ms=0.0,
        )


def _await(event: threading.Event, timeout=2.0):
    assert event.wait(timeout=timeout), "timed out waiting"


def test_interrupt_preempts_in_flight_normal_request():
    backend = _BlockingBackend()
    q = LLMRequestQueue(backend, max_concurrent=1)

    normal_done = threading.Event()
    normal_args: list = []

    def normal_cb(resp, err):
        normal_args.append((resp, err))
        normal_done.set()

    q.submit("alice", "{}", Priority.NORMAL, timeout=5.0, callback=normal_cb)
    _await(backend._enter)

    interrupt_done = threading.Event()
    interrupt_args: list = []

    def interrupt_cb(resp, err):
        interrupt_args.append((resp, err))
        interrupt_done.set()

    q.submit("alice", "{}", Priority.INTERRUPT, timeout=5.0, callback=interrupt_cb)

    stats = q.get_stats()
    assert stats["preempted"] >= 1

    backend._release.set()
    _await(normal_done)
    _await(interrupt_done)

    assert normal_args[0] == (None, None)
    assert interrupt_args[0][0] is not None
    q.shutdown()


def test_no_preemption_when_only_low_priority_in_flight():
    backend = _BlockingBackend()
    q = LLMRequestQueue(backend, max_concurrent=1)

    done = threading.Event()
    args: list = []

    def cb(resp, err):
        args.append((resp, err))
        done.set()

    q.submit("alice", "{}", Priority.NORMAL, timeout=5.0, callback=cb)
    _await(backend._enter)

    assert q.get_stats()["preempted"] == 0
    backend._release.set()
    _await(done)
    assert args[0][0] is not None
    q.shutdown()


def test_request_carries_cancelled_flag():
    from npc_sim.llm.llm_request_queue import LLMRequest
    req = LLMRequest("a", "{}", 5, 1.0, lambda _r, _e: None, seq=1)
    assert req._cancelled is False
    req._cancelled = True
    assert req._cancelled is True
