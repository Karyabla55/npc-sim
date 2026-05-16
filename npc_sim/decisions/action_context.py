# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Immutable snapshot of all information an action needs to evaluate or execute."""

from __future__ import annotations
from typing import TYPE_CHECKING
from npc_sim.perception.perceived_object import PerceivedObject
from npc_sim.core.sim_rng import SimRng

if TYPE_CHECKING:
    from npc_sim.npc.npc import NPC
    from npc_sim.npc.goals import NPCGoals, Goal


class ActionContext:
    """
    Immutable snapshot passed to every action candidate each tick.
    """

    def __init__(self, npc, percepts: list[PerceivedObject],
                 current_time: float, delta_time: float,
                 world, rng: SimRng,
                 day_length_seconds: float = 1440.0):
        self.self_npc = npc
        self.active_percepts = percepts or []
        self.current_time = current_time
        self.delta_time = delta_time
        self.world = world
        self.rng = rng
        # Retain day length so downstream consumers (e.g. NPCSerializer for the
        # LLM "day" field) don't have to poke npc._config.
        self.day_length_seconds = day_length_seconds if day_length_seconds > 0 else 1440.0

        if day_length_seconds > 0:
            self.sim_day_hour = (current_time % day_length_seconds) / day_length_seconds * 24.0
        else:
            self.sim_day_hour = 12.0

        # Build tag-grouped cache once per tick for O(1) percept lookups
        self._percepts_by_tag: dict[str, list[PerceivedObject]] = {}
        for p in self.active_percepts:
            self._percepts_by_tag.setdefault(p.tag.lower(), []).append(p)

    @property
    def goals(self):
        return self.self_npc.goals

    # ── Perception helpers ──

    def has_percept(self, tag: str) -> bool:
        return bool(self._percepts_by_tag.get(tag.lower()))

    def get_top_percept(self, tag: str) -> PerceivedObject | None:
        candidates = self._percepts_by_tag.get(tag.lower(), [])
        return max(candidates, key=lambda p: p.salience, default=None)

    def get_all_percepts(self, tag: str) -> list[PerceivedObject]:
        return list(self._percepts_by_tag.get(tag.lower(), []))

    # ── Goal helpers ──

    def has_goal(self, goal_type: str) -> bool:
        return self.goals.has_active_goal(goal_type)

    def get_top_goal_of_type(self, goal_type: str):
        lst = self.goals.get_by_type(goal_type)
        return lst[0] if lst else None

    def goal_bonus(self, goal_type: str, amount: float = 0.25) -> float:
        """Additive score bonus when an active goal of this type exists.

        Used by action evaluate() functions to bias scoring toward needs the
        goal pipeline has already flagged as relevant (G6 integration).
        """
        return amount if self.has_goal(goal_type) else 0.0

    # ── Memory helpers ──

    def get_memory_threat_bias(self, subject_id: str) -> float:
        """
        Returns a [-1, +1] bias from past experiences with this subject.
        Positive = NPC has successfully dealt with this type of threat before (confidence).
        Negative = NPC was hurt by it before (extra fear / flee tendency).
        Returns 0.0 if no relevant memories exist.
        """
        try:
            relevant = self.self_npc.memory.get_related_to(subject_id)
        except Exception:
            return 0.0
        if not relevant:
            return 0.0
        total_ew = sum(m.emotional_weight for m in relevant)
        return max(-1.0, min(total_ew / max(1, len(relevant)), 1.0))

    # ── Faction helpers ──

    def faction_disposition(self, target_id: str) -> float:
        """Inter-faction disposition between self_npc and the named target.

        Returns the registered value in [-1, +1] (0.0 if either side has no
        faction, the two NPCs share a faction, the target can't be resolved,
        or no FactionRegistry is attached). Used by AttackAction /
        SocializeAction to bias toward enemies / allies (B4 integration).
        """
        fr = getattr(self, "_faction_registry", None)
        if fr is None or not target_id or self.world is None:
            return 0.0
        target = self.world.get_npc_by_id(target_id)
        if target is None:
            return 0.0
        self_fac = getattr(self.self_npc.identity, "faction", "") or ""
        target_fac = getattr(target.identity, "faction", "") or ""
        if not self_fac or not target_fac or self_fac == target_fac:
            return 0.0
        return fr.get_disposition(self_fac, target_fac)

    # ── Belief helpers ──

    def belief_score(self, subject: str) -> float:
        """
        Returns valence * confidence in [-1, +1] for a given subject (npc_id, zone,
        topic, …). 0.0 if the belief is unknown or confidence is zero. Used by
        actions to bias scoring toward / away from subjects the NPC has formed
        opinions about (G1/G2/G3 integration).
        """
        if not subject:
            return 0.0
        try:
            nodes = self.self_npc.beliefs.nodes
            node = nodes.get(subject)
        except Exception:
            return 0.0
        if node is None or node.confidence <= 0.0:
            return 0.0
        return max(-1.0, min(node.valence * node.confidence, 1.0))

    def __repr__(self) -> str:
        return (f"[ActionContext] {self.self_npc.identity.display_name} "
                f"percepts:{len(self.active_percepts)} hour:{self.sim_day_hour:.1f}h")
