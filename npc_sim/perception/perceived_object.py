# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""A perceived object tracked by the perception system."""

from __future__ import annotations
from npc_sim.core.sim_vector3 import SimVector3


class PerceivedObject:
    """Represents a single entity perceived by an NPC's senses."""

    def __init__(self, object_id: str, object_type: str, position: SimVector3,
                 first_seen: float, threat_level: float = 0.0,
                 salience: float = 0.0, tag: str = ""):
        self.object_id = object_id
        self.object_type = object_type
        self.last_known_position = position
        self.first_seen = first_seen
        self.last_seen = first_seen
        self.threat_level = threat_level
        self.salience = salience
        self.tag = tag
        self._visible = True

    def refresh(self, position: SimVector3, current_time: float,
                threat: float, salience: float) -> None:
        self.last_known_position = position
        self.last_seen = current_time
        self.threat_level = threat
        self.salience = salience
        self._visible = True

    def mark_not_visible(self) -> None:
        self._visible = False

    def is_expired(self, current_time: float, timeout: float) -> bool:
        return (current_time - self.last_seen) > timeout

    def __repr__(self) -> str:
        return (f"[Percept] {self.object_id} ({self.object_type}) "
                f"threat={self.threat_level:.2f} sal={self.salience:.2f}")
