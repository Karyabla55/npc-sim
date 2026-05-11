# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""A2: BeliefSystem eviction invariants — threshold prune + LRU cap."""

from npc_sim.events.sim_event import SimEvent
from npc_sim.npc.beliefs import BeliefSystem


def _event(impact: float) -> SimEvent:
    return SimEvent(
        event_type="Test",
        initiator_id="a",
        target_id="b",
        description="t",
        impact=impact,
        timestamp=0.0,
    )


def test_decay_all_prunes_below_threshold():
    bs = BeliefSystem(max_nodes=200, prune_threshold=0.05)
    bs.process_event(_event(0.5), ["weak"], current_time=0.0, learning_rate=0.05)
    bs.process_event(_event(0.5), ["strong"], current_time=0.0, learning_rate=0.5)
    bs.decay_all(decay_rate=0.10)
    assert "weak" not in bs.nodes
    assert "strong" in bs.nodes


def test_get_or_create_evicts_at_cap():
    bs = BeliefSystem(max_nodes=10, prune_threshold=0.05)
    for i in range(10):
        bs.process_event(_event(0.5), [f"s{i}"], current_time=float(i),
                         learning_rate=0.9 if i == 5 else 0.1)
    assert len(bs.nodes) == 10
    bs.get_or_create("new_subject")
    assert len(bs.nodes) == 10
    assert "new_subject" in bs.nodes
    assert "s5" in bs.nodes


def test_cap_holds_under_flood():
    bs = BeliefSystem(max_nodes=50, prune_threshold=0.05)
    for i in range(500):
        bs.get_or_create(f"flood_{i}")
    assert len(bs.nodes) == 50


def test_tie_break_prefers_oldest():
    bs = BeliefSystem(max_nodes=2, prune_threshold=0.05)
    bs.get_or_create("a").last_updated = 1.0
    bs.get_or_create("b").last_updated = 2.0
    bs.get_or_create("c")
    assert "a" not in bs.nodes
    assert "b" in bs.nodes
    assert "c" in bs.nodes
