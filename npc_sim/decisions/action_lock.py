# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Action Lock mechanism for ensuring action durations."""

from __future__ import annotations
from typing import Callable
from npc_sim.decisions.action_context import ActionContext

class ActionLock:
    """Represents a commitment to an action for a duration of time."""
    def __init__(self, action_id: str, min_duration_sim_seconds: float,
                 exit_condition: Callable[[ActionContext], bool],
                 interrupt_allowed: bool = True):
        self.action_id = action_id
        self.min_duration_sim_seconds = min_duration_sim_seconds
        self.exit_condition = exit_condition
        self.interrupt_allowed = interrupt_allowed

    def __repr__(self) -> str:
        return f"[ActionLock] {self.action_id} (min: {self.min_duration_sim_seconds}s)"
