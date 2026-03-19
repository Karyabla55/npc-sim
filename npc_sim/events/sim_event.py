# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Represents a meaningful occurrence in the simulation world."""

from __future__ import annotations
import threading
from npc_sim.core.sim_vector3 import SimVector3
from npc_sim.core.sim_rng import SimRng


class SimEvent:
    """
    A meaningful occurrence in the simulation world.
    NPCs can witness events, which update their memory and belief systems.
    """
    _global_counter = 0
    _lock = threading.Lock()

    def __init__(
        self,
        event_type: str,
        initiator_id: str,
        target_id: str | None,
        description: str,
        impact: float,
        timestamp: float,
        position: SimVector3 = None,
        rng: SimRng = None,
        category: str = "",
    ):
        if rng is not None:
            self.event_id = rng.next_id("ev")
        else:
            with SimEvent._lock:
                SimEvent._global_counter += 1
                self.event_id = f"ev_{SimEvent._global_counter:06x}"

        self.event_type = event_type or ""
        self.initiator_id = initiator_id or ""
        self.target_id = target_id or ""
        self.description = description or ""
        self.impact = max(-1.0, min(impact, 1.0))
        self.timestamp = timestamp
        self.world_position = position or SimVector3.ZERO
        self.category = category or ""

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "initiator_id": self.initiator_id,
            "target_id": self.target_id,
            "description": self.description,
            "impact": self.impact,
            "timestamp": self.timestamp,
            "category": self.category,
        }

    def __repr__(self) -> str:
        return (f"[SimEvent:{self.event_type}] {self.initiator_id}→{self.target_id} "
                f"Impact:{self.impact:+.2f} @t={self.timestamp:.1f}")
