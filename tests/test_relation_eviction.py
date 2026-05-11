# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""A3: NPCSocial.Relation eviction — threshold prune + LRU cap."""

from npc_sim.npc.social import NPCSocial


def test_tick_decay_prunes_weak_relations():
    s = NPCSocial(max_relations=10, prune_threshold=0.05)
    weak = s.get_or_create_relation("me", "weak")
    weak.apply_interaction(0.02, 0.0, 0.0, current_time=0.0)
    strong = s.get_or_create_relation("me", "strong")
    strong.apply_interaction(0.5, 0.5, 0.5, current_time=0.0)
    s.tick_decay(delta_time=1.0, decay_rate=0.001)
    assert "weak" not in s.relations
    assert "strong" in s.relations


def test_get_or_create_evicts_at_cap():
    s = NPCSocial(max_relations=5, prune_threshold=0.05)
    for i in range(5):
        r = s.get_or_create_relation("me", f"t{i}")
        r.apply_interaction(0.6 if i == 2 else 0.1, 0.0, 0.0, current_time=float(i))
    assert len(s.relations) == 5
    s.get_or_create_relation("me", "newcomer")
    assert len(s.relations) == 5
    assert "newcomer" in s.relations
    assert "t2" in s.relations


def test_cap_holds_under_flood():
    s = NPCSocial(max_relations=20, prune_threshold=0.05)
    for i in range(500):
        s.get_or_create_relation("me", f"flood_{i}")
    assert len(s.relations) == 20


def test_negative_magnitude_counts_toward_eviction_protection():
    s = NPCSocial(max_relations=2, prune_threshold=0.05)
    enemy = s.get_or_create_relation("me", "enemy")
    enemy.apply_interaction(-0.7, 0.0, 0.0, current_time=0.0)
    weak = s.get_or_create_relation("me", "weak")
    weak.apply_interaction(0.1, 0.0, 0.0, current_time=1.0)
    s.get_or_create_relation("me", "newcomer")
    assert "enemy" in s.relations
    assert "newcomer" in s.relations
    assert "weak" not in s.relations
