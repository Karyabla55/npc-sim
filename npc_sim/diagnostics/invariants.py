# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Long-run simulation invariants — runtime safety net for years-long runs.

Each check enforces a bound that, if violated, indicates a bug rather than
an interesting emergent behavior (e.g. NaN in a vital, runaway inventory,
dict growing past its eviction cap). Cheap enough to run every N ticks
inside run_diagnostic.py --strict.
"""

from __future__ import annotations
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class InvariantViolation:
    npc_id: str
    check: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.check}] npc={self.npc_id}: {self.detail}"


_VITAL_NORM_FIELDS = ("hunger", "thirst", "stress")
_EMOTION_FIELDS = ("fear", "anger", "happiness")
_INVENTORY_STACK_CAP = 100
_BELIEF_CAP = 200
_RELATION_CAP = 200


def check_invariants(sim_manager) -> list[InvariantViolation]:
    """Walk every NPC and report bounds violations. Empty list = healthy."""
    violations: list[InvariantViolation] = []
    for npc in sim_manager.world.all_npcs:
        nid = npc.identity.npc_id
        _check_vitals(nid, npc, violations)
        _check_emotions(nid, npc, violations)
        _check_inventory(nid, npc, violations)
        _check_beliefs(nid, npc, violations)
        _check_relations(nid, npc, violations)
        _check_memory(nid, npc, violations)
    return violations


def _is_finite(x: float) -> bool:
    return not (math.isnan(x) or math.isinf(x))


def _check_vitals(nid, npc, out):
    v = npc.vitals
    if not _is_finite(v.health):
        out.append(InvariantViolation(nid, "vital_finite", f"hp={v.health}"))
    if v.health < 0 or v.health > v.max_health:
        out.append(InvariantViolation(
            nid, "vital_range", f"hp={v.health:.3f} max={v.max_health}"))
    if not _is_finite(v.energy):
        out.append(InvariantViolation(nid, "vital_finite", f"energy={v.energy}"))
    elif v.energy < 0.0 or v.energy > v.max_energy:
        out.append(InvariantViolation(
            nid, "vital_range",
            f"energy={v.energy:.3f} max={v.max_energy}"))
    for fld in _VITAL_NORM_FIELDS:
        val = getattr(v, fld)
        if not _is_finite(val):
            out.append(InvariantViolation(nid, "vital_finite", f"{fld}={val}"))
        elif val < 0.0 or val > 1.0:
            out.append(InvariantViolation(
                nid, "vital_range", f"{fld}={val:.4f} out of [0,1]"))


def _check_emotions(nid, npc, out):
    p = npc.psychology
    for fld in _EMOTION_FIELDS:
        val = getattr(p, fld)
        if not _is_finite(val):
            out.append(InvariantViolation(nid, "emotion_finite", f"{fld}={val}"))
        elif val < 0.0 or val > 1.0:
            out.append(InvariantViolation(
                nid, "emotion_range", f"{fld}={val:.4f} out of [0,1]"))


def _check_inventory(nid, npc, out):
    for stack in npc.inventory.stacks:
        if stack.amount > _INVENTORY_STACK_CAP:
            out.append(InvariantViolation(
                nid, "inventory_cap",
                f"{stack.item_id}×{stack.amount} > {_INVENTORY_STACK_CAP}"))
        if stack.amount < 0:
            out.append(InvariantViolation(
                nid, "inventory_negative", f"{stack.item_id}×{stack.amount}"))


def _check_beliefs(nid, npc, out):
    bs = getattr(npc, "beliefs", None)
    if bs is None:
        return
    n = len(bs.nodes)
    if n > _BELIEF_CAP:
        out.append(InvariantViolation(
            nid, "belief_cap", f"{n} nodes > {_BELIEF_CAP}"))


def _check_relations(nid, npc, out):
    soc = getattr(npc, "social", None)
    if soc is None:
        return
    n = len(soc.relations)
    if n > _RELATION_CAP:
        out.append(InvariantViolation(
            nid, "relation_cap", f"{n} relations > {_RELATION_CAP}"))


def _check_memory(nid, npc, out):
    mem = getattr(npc, "memory", None)
    if mem is None:
        return
    if mem.count > mem.capacity:
        out.append(InvariantViolation(
            nid, "memory_overflow",
            f"count={mem.count} > capacity={mem.capacity}"))
