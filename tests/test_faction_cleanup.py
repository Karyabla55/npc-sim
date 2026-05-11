# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""A4: FactionRegistry cleanup threshold raised from 1e-6 → 0.01."""

from npc_sim.simulation.faction_registry import FactionRegistry


def test_cleanup_threshold_value():
    assert FactionRegistry._CLEANUP_THRESHOLD == 0.01


def test_decay_removes_dispositions_below_threshold():
    fr = FactionRegistry()
    fr.register_faction("A")
    fr.register_faction("B")
    fr.set_mutual_disposition("A", "B", 0.005)
    fr.tick_decay(delta_time=1.0)
    assert fr.get_disposition("A", "B") == 0.0
    assert ("A", "B") not in fr._dispositions
    assert ("B", "A") not in fr._dispositions


def test_decay_preserves_above_threshold():
    fr = FactionRegistry()
    fr.set_mutual_disposition("A", "B", 0.5)
    fr.tick_decay(delta_time=1.0)
    assert abs(fr.get_disposition("A", "B")) >= 0.01


def test_decay_eventually_clears_old_dispositions():
    fr = FactionRegistry()
    fr.set_mutual_disposition("A", "B", 0.05)
    for _ in range(2000):
        fr.tick_decay(delta_time=1.0)
    assert fr.get_disposition("A", "B") == 0.0
    assert len(fr._dispositions) == 0
