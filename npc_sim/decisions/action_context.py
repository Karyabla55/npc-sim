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

        if day_length_seconds > 0:
            self.sim_day_hour = (current_time % day_length_seconds) / day_length_seconds * 24.0
        else:
            self.sim_day_hour = 12.0

    @property
    def goals(self):
        return self.self_npc.goals

    # ── Perception helpers ──

    def has_percept(self, tag: str) -> bool:
        tag_lower = tag.lower()
        return any(p.tag.lower() == tag_lower for p in self.active_percepts)

    def get_top_percept(self, tag: str) -> PerceivedObject | None:
        tag_lower = tag.lower()
        best = None
        best_sal = -1.0
        for p in self.active_percepts:
            if p.tag.lower() != tag_lower:
                continue
            if p.salience > best_sal:
                best_sal = p.salience
                best = p
        return best

    def get_all_percepts(self, tag: str) -> list[PerceivedObject]:
        tag_lower = tag.lower()
        return [p for p in self.active_percepts if p.tag.lower() == tag_lower]

    # ── Goal helpers ──

    def has_goal(self, goal_type: str) -> bool:
        return self.goals.has_active_goal(goal_type)

    def get_top_goal_of_type(self, goal_type: str):
        lst = self.goals.get_by_type(goal_type)
        return lst[0] if lst else None

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

    def __repr__(self) -> str:
        return (f"[ActionContext] {self.self_npc.identity.display_name} "
                f"percepts:{len(self.active_percepts)} hour:{self.sim_day_hour:.1f}h")
