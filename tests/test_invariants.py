# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""A7: invariant checker reports bounds violations correctly."""

import math
from types import SimpleNamespace

from npc_sim.diagnostics.invariants import (
    check_invariants,
    InvariantViolation,
    _check_inventory,
    _check_vitals,
    _check_emotions,
)


def _fake_npc(**vital_overrides):
    vitals = SimpleNamespace(
        health=80.0, max_health=100.0,
        hunger=0.3, thirst=0.3, energy=80.0, max_energy=100.0, stress=0.4,
    )
    for k, v in vital_overrides.items():
        setattr(vitals, k, v)
    psychology = SimpleNamespace(fear=0.1, anger=0.1, happiness=0.5)
    inventory = SimpleNamespace(stacks=[])
    beliefs = SimpleNamespace(nodes={})
    social = SimpleNamespace(relations={})
    memory = SimpleNamespace(count=0, capacity=50)
    identity = SimpleNamespace(npc_id="npc_1")
    return SimpleNamespace(
        identity=identity, vitals=vitals, psychology=psychology,
        inventory=inventory, beliefs=beliefs, social=social, memory=memory,
    )


def test_healthy_npc_yields_no_violations():
    npc = _fake_npc()
    mgr = SimpleNamespace(world=SimpleNamespace(all_npcs=[npc]))
    assert check_invariants(mgr) == []


def test_nan_hp_flagged():
    npc = _fake_npc(health=float("nan"))
    mgr = SimpleNamespace(world=SimpleNamespace(all_npcs=[npc]))
    out = check_invariants(mgr)
    assert any(v.check == "vital_finite" for v in out)


def test_out_of_range_stress_flagged():
    npc = _fake_npc(stress=1.5)
    mgr = SimpleNamespace(world=SimpleNamespace(all_npcs=[npc]))
    out = check_invariants(mgr)
    assert any(v.check == "vital_range" for v in out)


def test_inventory_cap_violation_flagged():
    npc = _fake_npc()
    npc.inventory.stacks = [SimpleNamespace(item_id="gold", amount=150)]
    mgr = SimpleNamespace(world=SimpleNamespace(all_npcs=[npc]))
    out = check_invariants(mgr)
    assert any(v.check == "inventory_cap" for v in out)


def test_belief_overflow_flagged():
    npc = _fake_npc()
    npc.beliefs.nodes = {f"k{i}": None for i in range(250)}
    mgr = SimpleNamespace(world=SimpleNamespace(all_npcs=[npc]))
    out = check_invariants(mgr)
    assert any(v.check == "belief_cap" for v in out)


def test_relation_overflow_flagged():
    npc = _fake_npc()
    npc.social.relations = {f"t{i}": None for i in range(250)}
    mgr = SimpleNamespace(world=SimpleNamespace(all_npcs=[npc]))
    out = check_invariants(mgr)
    assert any(v.check == "relation_cap" for v in out)


def test_memory_overflow_flagged():
    npc = _fake_npc()
    npc.memory.count = 60
    npc.memory.capacity = 50
    mgr = SimpleNamespace(world=SimpleNamespace(all_npcs=[npc]))
    out = check_invariants(mgr)
    assert any(v.check == "memory_overflow" for v in out)


def test_violation_repr_includes_id_and_check():
    v = InvariantViolation(npc_id="npc_1", check="x", detail="d")
    s = str(v)
    assert "npc_1" in s and "[x]" in s
