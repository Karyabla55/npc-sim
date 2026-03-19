# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""NPC goal system: priority-sorted, need-driven goal pipeline."""

from __future__ import annotations
import threading


class GoalType:
    """Well-known goal type strings used by actions and the need system."""
    SURVIVE = "Survive"
    FIND_FOOD = "FindFood"
    FIND_WATER = "FindWater"
    REST = "Rest"
    SOCIALIZE = "Socialize"
    WORK = "Work"
    EXPLORE = "Explore"
    TRADE = "Trade"
    ATTACK = "Attack"
    PRAY = "Pray"
    HEAL = "Heal"
    GO_HOME = "GoHome"


class Goal:
    """A single NPC goal with priority, progress, and optional expiry."""
    _counter = 0
    _lock = threading.Lock()

    def __init__(self, goal_type: str, description: str, priority: float, expires_at: float = 0.0):
        with Goal._lock:
            Goal._counter += 1
            self.goal_id = f"goal_{Goal._counter:06d}"
        self.goal_type = goal_type
        self.description = description
        self.priority = max(0.0, min(priority, 1.0))
        self.is_active = True
        self.progress: float = 0.0
        self.expires_at = expires_at

    def set_progress(self, value: float) -> None:
        self.progress = max(0.0, min(value, 1.0))

    def set_priority(self, value: float) -> None:
        self.priority = max(0.0, min(value, 1.0))

    def complete(self) -> None:
        self.is_active = False

    def abandon(self) -> None:
        self.is_active = False

    def is_expired(self, current_time: float) -> bool:
        if not self.is_active:
            return True
        if self.expires_at > 0.0 and current_time > self.expires_at:
            return True
        return False

    def __repr__(self) -> str:
        state = "Active" if self.is_active else "Done"
        return f"[Goal] {self.goal_type} | {self.description} | P:{self.priority:.2f} | {state}"


class NPCGoals:
    """Manages goals and their priorities for an NPC."""

    def __init__(self):
        self._goals: list[Goal] = []

    @property
    def goals(self) -> list[Goal]:
        return self._goals

    def add_goal(self, goal: Goal) -> None:
        if goal is None:
            return
        self._goals.append(goal)
        self._sort_goals()

    def remove_goal(self, goal_id: str) -> bool:
        before = len(self._goals)
        self._goals = [g for g in self._goals if g.goal_id != goal_id]
        return len(self._goals) < before

    def get_top_goal(self) -> Goal | None:
        for g in self._goals:
            if g.is_active:
                return g
        return None

    def get_by_type(self, goal_type: str) -> list[Goal]:
        return [g for g in self._goals if g.goal_type == goal_type and g.is_active]

    def has_active_goal(self, goal_type: str) -> bool:
        return any(g.goal_type == goal_type and g.is_active for g in self._goals)

    def prune_expired(self, current_time: float) -> None:
        self._goals = [g for g in self._goals if not g.is_expired(current_time)]

    def _sort_goals(self) -> None:
        self._goals.sort(key=lambda g: g.priority, reverse=True)

    def __repr__(self) -> str:
        top = self.get_top_goal()
        return f"[Goals] {len(self._goals)} goal(s) | Top: {top.goal_type if top else 'None'}"
