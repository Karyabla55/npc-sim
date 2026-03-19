# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""SimWorldAdapter: manages the NPC collection, spatial grid, stimuli, and event log."""

from __future__ import annotations
from collections import deque
from npc_sim.core.sim_vector3 import SimVector3
from npc_sim.events.sim_event import SimEvent
from npc_sim.events.stimulus import Stimulus, StimulusType
from npc_sim.simulation.spatial_grid import ISpatialGrid, DictionaryGrid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from npc_sim.npc.npc import NPC


class SimWorldAdapter:
    """
    Manages collection of NPCs, spatial grid, stimulus queue, and event log.
    Central point for world-level queries and mutations.
    """

    def __init__(self, grid: ISpatialGrid = None, event_log_capacity: int = 500,
                 stimulus_queue_size: int = 1024):
        self._grid = grid or DictionaryGrid()
        self._npcs: dict[str, "NPC"] = {}
        self._stimulus_queue: deque[Stimulus] = deque(maxlen=stimulus_queue_size)
        self._event_log: deque[SimEvent] = deque(maxlen=event_log_capacity)
        self._pending_stimuli: list[Stimulus] = []

    @property
    def all_npcs(self) -> list:
        return list(self._npcs.values())

    @property
    def event_log(self) -> deque[SimEvent]:
        return self._event_log

    # ── NPC management ──

    def add_npc(self, npc) -> None:
        self._npcs[npc.identity.npc_id] = npc
        self._grid.insert(npc)

    def remove_npc(self, npc_id: str) -> None:
        npc = self._npcs.pop(npc_id, None)
        if npc:
            self._grid.remove(npc)

    def get_npc_by_id(self, npc_id: str):
        return self._npcs.get(npc_id)

    def move_npc(self, npc_id: str, new_position: SimVector3) -> None:
        npc = self._npcs.get(npc_id)
        if npc:
            npc.position = new_position
            self._grid.update(npc)

    # ── Spatial queries ──

    def get_npcs_in_radius(self, center: SimVector3, radius: float) -> list:
        return self._grid.query_radius(center, radius)

    # ── Stimulus management ──

    def publish_stimulus(self, stimulus: Stimulus) -> None:
        self._stimulus_queue.append(stimulus)
        self._pending_stimuli.append(stimulus)

    def publish_stimulus_from_action(self, source_id: str, position: SimVector3,
                                     stim_type: str, tag: str, intensity: float,
                                     current_time: float) -> None:
        type_map = {
            "Visual": StimulusType.VISUAL,
            "Audio": StimulusType.AUDIO,
            "Social": StimulusType.SOCIAL,
            "Olfactory": StimulusType.OLFACTORY,
        }
        st = type_map.get(stim_type, StimulusType.VISUAL)
        self.publish_stimulus(Stimulus(st, source_id, position, intensity, current_time, tag))

    def drain_pending_stimuli(self) -> list[Stimulus]:
        result = self._pending_stimuli.copy()
        self._pending_stimuli.clear()
        return result

    # ── Event log ──

    def publish_event(self, event: SimEvent) -> None:
        self._event_log.append(event)

    def get_recent_events(self, count: int = 20) -> list[SimEvent]:
        n = min(count, len(self._event_log))
        return list(self._event_log)[-n:]

    def __repr__(self) -> str:
        return (f"[SimWorld] NPCs:{len(self._npcs)} Events:{len(self._event_log)} "
                f"Stimuli:{len(self._stimulus_queue)}")
