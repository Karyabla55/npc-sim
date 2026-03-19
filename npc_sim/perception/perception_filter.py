# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Psychology-aware perception filter that evaluates stimulus salience."""

from __future__ import annotations
from npc_sim.events.stimulus import Stimulus
from npc_sim.npc.vitals import NPCVitals
from npc_sim.npc.psychology import NPCPsychology


class PerceptionFilter:
    """Evaluates salience of stimuli based on NPC psychology and vitals."""

    def __init__(self, attention_threshold: float = 0.2):
        self.attention_threshold = attention_threshold

    def evaluate(self, stimulus: Stimulus, vitals: NPCVitals,
                 psychology: NPCPsychology) -> float:
        base = stimulus.intensity

        # Stressed NPCs focus on threats
        tag_lower = stimulus.tag.lower()
        if tag_lower == "threat":
            base *= 1.0 + vitals.stress * 0.5 + psychology.neuroticism * 0.3
        elif tag_lower == "food":
            base *= 1.0 + vitals.hunger * 0.5
        elif tag_lower == "ally":
            base *= 1.0 + psychology.extraversion * 0.3

        if base < self.attention_threshold:
            return 0.0
        return min(base, 1.0)
