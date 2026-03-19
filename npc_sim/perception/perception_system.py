# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Per-NPC perception orchestrator."""

from __future__ import annotations
from npc_sim.core.sim_vector3 import SimVector3
from npc_sim.events.stimulus import Stimulus, StimulusType
from npc_sim.npc.vitals import NPCVitals
from npc_sim.npc.psychology import NPCPsychology
from npc_sim.perception.perceived_object import PerceivedObject
from npc_sim.perception.sensor_range import SensorRange
from npc_sim.perception.perception_filter import PerceptionFilter


class PerceptionSystem:
    """
    Per-NPC perception orchestrator. Each tick it filters stimuli through
    sensor range and salience evaluation, upserts percepts, and prunes expired ones.
    """

    def __init__(self, sensor: SensorRange = None, pfilter: PerceptionFilter = None):
        self.sensor = sensor or SensorRange()
        self.filter = pfilter or PerceptionFilter()
        self._percepts: list[PerceivedObject] = []
        self.percept_timeout: float = 30.0

    @property
    def active_percepts(self) -> list[PerceivedObject]:
        return self._percepts

    def tick(self, stimuli: list[Stimulus], npc_position: SimVector3,
             npc_forward: SimVector3, vitals: NPCVitals,
             psychology: NPCPsychology, current_time: float) -> list[PerceivedObject]:
        # Mark all existing percepts as not currently visible
        for p in self._percepts:
            p.mark_not_visible()

        changed: list[PerceivedObject] = []

        for stimulus in stimuli:
            # Spatial pre-filter
            if not self.sensor.can_sense(stimulus, npc_position, npc_forward):
                continue

            # Salience evaluation
            salience = self.filter.evaluate(stimulus, vitals, psychology)
            if salience <= 0.0:
                continue

            # Derive threat level
            threat = 0.0
            if stimulus.tag.lower() == "threat":
                threat = stimulus.intensity * (0.5 + psychology.neuroticism * 0.5)

            # Upsert percept
            existing = self._find_percept(stimulus.source_id)
            if existing is not None:
                existing.refresh(stimulus.source_position, current_time, threat, salience)
            else:
                obj_type = self._infer_object_type(stimulus)
                existing = PerceivedObject(
                    stimulus.source_id, obj_type, stimulus.source_position,
                    current_time, threat, salience, stimulus.tag)
                self._percepts.append(existing)

            changed.append(existing)

        # Prune expired
        self._percepts = [p for p in self._percepts
                          if not p.is_expired(current_time, self.percept_timeout)]

        return changed

    def get_threats(self) -> list[PerceivedObject]:
        result = [p for p in self._percepts
                  if p.tag.lower() == "threat" and p.threat_level > 0]
        result.sort(key=lambda p: p.threat_level, reverse=True)
        return result

    def get_allies(self) -> list[PerceivedObject]:
        return [p for p in self._percepts if p.tag.lower() == "ally"]

    def get_nearest_food(self, npc_position: SimVector3) -> PerceivedObject | None:
        nearest = None
        nearest_sqr = float("inf")
        for p in self._percepts:
            if p.tag.lower() != "food":
                continue
            d = SimVector3.sqr_distance(npc_position, p.last_known_position)
            if d < nearest_sqr:
                nearest_sqr = d
                nearest = p
        return nearest

    def _find_percept(self, source_id: str) -> PerceivedObject | None:
        for p in self._percepts:
            if p.object_id == source_id:
                return p
        return None

    @staticmethod
    def _infer_object_type(s: Stimulus) -> str:
        if s.type == StimulusType.VISUAL:
            return "Hazard" if s.tag == "Threat" else "Entity"
        elif s.type == StimulusType.SOCIAL:
            return "NPC"
        elif s.type == StimulusType.AUDIO:
            return "Noise"
        elif s.type == StimulusType.OLFACTORY:
            return "Scent"
        return "Unknown"

    def __repr__(self) -> str:
        return f"[PerceptionSystem] {len(self._percepts)} active percept(s)"
