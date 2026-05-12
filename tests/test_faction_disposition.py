# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""B4: faction disposition reaches Utility AI (helper + Attack/Socialize)."""

from types import SimpleNamespace
from npc_sim.decisions.action_context import ActionContext
from npc_sim.simulation.faction_registry import FactionRegistry


class _FakeWorld:
    def __init__(self, by_id):
        self._npcs = by_id

    def get_npc_by_id(self, nid):
        return self._npcs.get(nid)


def _make_ctx(self_faction: str, target_faction: str | None,
              disposition_value: float = 0.0,
              attach_registry: bool = True):
    self_npc = SimpleNamespace(
        identity=SimpleNamespace(faction=self_faction, npc_id="me"),
    )
    target = None
    if target_faction is not None:
        target = SimpleNamespace(identity=SimpleNamespace(faction=target_faction, npc_id="tgt"))
    world = _FakeWorld({"tgt": target})
    fr = FactionRegistry()
    if self_faction:
        fr.register_faction(self_faction)
    if target_faction:
        fr.register_faction(target_faction)
    if disposition_value != 0.0 and self_faction and target_faction:
        fr.set_mutual_disposition(self_faction, target_faction, disposition_value)
    ctx = ActionContext(npc=self_npc, percepts=[], current_time=0.0,
                        delta_time=0.1, world=world, rng=None)
    if attach_registry:
        ctx._faction_registry = fr
    return ctx


def test_disposition_returns_zero_when_no_registry():
    ctx = _make_ctx("FactionA", "FactionB", -0.5, attach_registry=False)
    assert ctx.faction_disposition("tgt") == 0.0


def test_disposition_returns_zero_for_same_faction():
    ctx = _make_ctx("FactionA", "FactionA", -0.5)
    assert ctx.faction_disposition("tgt") == 0.0


def test_disposition_returns_zero_for_unknown_target():
    ctx = _make_ctx("FactionA", None)
    assert ctx.faction_disposition("ghost") == 0.0


def test_disposition_returns_registered_value():
    ctx = _make_ctx("FactionA", "FactionB", -0.7)
    assert abs(ctx.faction_disposition("tgt") + 0.7) < 1e-6


def test_disposition_honors_missing_self_faction():
    ctx = _make_ctx("", "FactionB", -0.5)
    assert ctx.faction_disposition("tgt") == 0.0
