# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Sensor range configuration and FOV checks."""

from __future__ import annotations
import math
from npc_sim.core.sim_vector3 import SimVector3
from npc_sim.events.stimulus import Stimulus, StimulusType


class SensorRange:
    """Per-NPC sensor configuration with range and FOV per modality."""

    def __init__(self, visual_range: float = 20.0, audio_range: float = 25.0,
                 social_range: float = 15.0, olfactory_range: float = 10.0,
                 fov_degrees: float = 180.0):
        self.visual_range = visual_range
        self.audio_range = audio_range
        self.social_range = social_range
        self.olfactory_range = olfactory_range
        self.fov_half_cos = math.cos(math.radians(fov_degrees / 2.0))

    def can_sense(self, stimulus: Stimulus, npc_position: SimVector3,
                  npc_forward: SimVector3) -> bool:
        sq_dist = SimVector3.sqr_distance(npc_position, stimulus.source_position)

        if stimulus.type == StimulusType.VISUAL:
            if sq_dist > self.visual_range ** 2:
                return False
            # FOV check
            if npc_forward.sqr_magnitude > 1e-6:
                to_stim = stimulus.source_position - npc_position
                if to_stim.sqr_magnitude > 1e-6:
                    dot = (npc_forward.normalized().x * to_stim.normalized().x +
                           npc_forward.normalized().z * to_stim.normalized().z)
                    if dot < self.fov_half_cos:
                        return False
            return True
        elif stimulus.type == StimulusType.AUDIO:
            return sq_dist <= self.audio_range ** 2
        elif stimulus.type == StimulusType.SOCIAL:
            return sq_dist <= self.social_range ** 2
        elif stimulus.type == StimulusType.OLFACTORY:
            return sq_dist <= self.olfactory_range ** 2
        return False


class SensorRangePresets:
    """Per-archetype sensor range presets."""

    _PRESETS = {
        "guardian": SensorRange(visual_range=35, audio_range=30, social_range=20, olfactory_range=15, fov_degrees=160),
        "merchant": SensorRange(visual_range=20, audio_range=20, social_range=30, olfactory_range=10, fov_degrees=180),
        "scholar": SensorRange(visual_range=18, audio_range=18, social_range=25, olfactory_range=12, fov_degrees=180),
        "farmer": SensorRange(visual_range=20, audio_range=35, social_range=15, olfactory_range=20, fov_degrees=180),
        "priest": SensorRange(visual_range=18, audio_range=20, social_range=40, olfactory_range=10, fov_degrees=180),
        "generic": SensorRange(visual_range=20, audio_range=25, social_range=15, olfactory_range=10, fov_degrees=180),
    }

    @staticmethod
    def for_archetype(archetype: str) -> SensorRange:
        return SensorRangePresets._PRESETS.get(
            (archetype or "generic").lower(),
            SensorRangePresets._PRESETS["generic"]
        )
