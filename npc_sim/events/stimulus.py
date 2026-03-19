# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Raw world signal emitted by entities."""

from __future__ import annotations
from enum import Enum
from npc_sim.core.sim_vector3 import SimVector3


class StimulusType(Enum):
    VISUAL = "Visual"
    AUDIO = "Audio"
    SOCIAL = "Social"
    OLFACTORY = "Olfactory"


class Stimulus:
    """
    A raw world signal emitted by any entity (NPC, object, event).
    The StimulusDispatcher routes stimuli to nearby NPCs;
    each NPC's PerceptionSystem then filters them.
    """

    def __init__(
        self,
        stimulus_type: StimulusType,
        source_id: str,
        source_position: SimVector3,
        intensity: float,
        timestamp: float,
        tag: str = "",
        payload: object = None,
    ):
        self.type = stimulus_type
        self.source_id = source_id or ""
        self.source_position = source_position
        self.intensity = max(0.0, min(intensity, 1.0))
        self.timestamp = timestamp
        self.tag = tag or ""
        self.payload = payload

    def __repr__(self) -> str:
        return (f"[Stimulus] {self.type.value} '{self.tag}' from {self.source_id} "
                f"@ {self.source_position} I={self.intensity:.2f} t={self.timestamp:.1f}")
