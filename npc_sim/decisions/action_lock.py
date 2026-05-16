# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Action Lock mechanism for ensuring action durations."""

from __future__ import annotations
from typing import Callable
from npc_sim.decisions.action_context import ActionContext

class ActionLock:
    """Represents a commitment to an action for a duration of time.

    `interrupt_allowed` is retained for API compatibility but no longer
    consulted by `DecisionSystem.tick`. `hard_interrupt` (threat ≥ 0.8,
    HP ≤ 25 %, hunger/thirst ≥ 0.85) now preempts every lock unconditionally.
    """
    def __init__(self, action_id: str, min_duration_sim_seconds: float,
                 exit_condition: Callable[[ActionContext], bool],
                 interrupt_allowed: bool = True,
                 interrupt_predicate: Callable[[ActionContext], bool] | None = None):
        self.action_id = action_id
        self.min_duration_sim_seconds = min_duration_sim_seconds
        self.exit_condition = exit_condition
        self.interrupt_allowed = interrupt_allowed  # legacy; not consulted
        self.interrupt_predicate = interrupt_predicate

    def __repr__(self) -> str:
        return f"[ActionLock] {self.action_id} (min: {self.min_duration_sim_seconds}s)"
