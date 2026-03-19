# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Routes stimuli to nearby NPCs via spatial queries."""

from __future__ import annotations
from collections import defaultdict
from npc_sim.events.stimulus import Stimulus
from npc_sim.core.sim_vector3 import SimVector3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from npc_sim.simulation.sim_world import SimWorldAdapter


class StimulusDispatcher:
    """Zero-alloc per-NPC stimulus dispatch. Routes world stimuli to nearby NPCs."""

    def __init__(self):
        self._buffers: dict[str, list[Stimulus]] = defaultdict(list)

    def dispatch(self, stimulus: Stimulus, world, max_radius: float = 60.0) -> None:
        nearby = world.get_npcs_in_radius(stimulus.source_position, max_radius)
        for npc in nearby:
            if npc.identity.npc_id != stimulus.source_id:
                self._buffers[npc.identity.npc_id].append(stimulus)

    def drain_for(self, npc_id: str) -> list[Stimulus]:
        buf = self._buffers.pop(npc_id, [])
        return buf
