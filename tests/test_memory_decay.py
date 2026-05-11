# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""A5: NPCMemory.emotional_weight uses multiplicative decay (preserves ordering)."""

import math
from npc_sim.core.sim_vector3 import SimVector3
from npc_sim.events.sim_event import SimEvent
from npc_sim.npc.memory import MemoryEntry


def _ev(impact: float = 0.5) -> SimEvent:
    return SimEvent(event_type="t", initiator_id="a", target_id="b",
                    description="d", impact=impact, timestamp=0.0)


def test_decay_preserves_sign_positive():
    m = MemoryEntry(_ev(), emotional_weight=0.8, recorded_at=0.0)
    for _ in range(50):
        m.decay(0.01)
    assert m.emotional_weight > 0.0


def test_decay_preserves_sign_negative():
    m = MemoryEntry(_ev(), emotional_weight=-0.6, recorded_at=0.0)
    for _ in range(50):
        m.decay(0.01)
    assert m.emotional_weight < 0.0


def test_decay_preserves_ordering_under_long_run():
    big = MemoryEntry(_ev(), emotional_weight=0.9, recorded_at=0.0)
    small = MemoryEntry(_ev(), emotional_weight=0.1, recorded_at=0.0)
    for _ in range(1000):
        big.decay(0.005)
        small.decay(0.005)
    assert abs(big.emotional_weight) > abs(small.emotional_weight)


def test_decay_never_yields_nan_or_overflow():
    m = MemoryEntry(_ev(), emotional_weight=1.0, recorded_at=0.0)
    for _ in range(100_000):
        m.decay(0.005)
    assert not math.isnan(m.emotional_weight)
    assert -1.0 <= m.emotional_weight <= 1.0


def test_zero_weight_stays_zero():
    m = MemoryEntry(_ev(), emotional_weight=0.0, recorded_at=0.0)
    for _ in range(100):
        m.decay(0.01)
    assert m.emotional_weight == 0.0
