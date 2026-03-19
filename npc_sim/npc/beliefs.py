# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""NPC belief system: reinforcement-based belief nodes."""

from __future__ import annotations
from npc_sim.events.sim_event import SimEvent


class BeliefNode:
    """A single belief about a subject, with confidence and valence."""

    def __init__(self, subject: str):
        self.subject = subject
        self.confidence: float = 0.0
        self.valence: float = 0.0
        self.last_updated: float = 0.0

    def reinforce(self, sim_event: SimEvent, current_time: float, learning_rate: float = 0.1) -> None:
        self.confidence = min(1.0, self.confidence + learning_rate)
        self.valence = max(-1.0, min(1.0, self.valence + sim_event.impact * learning_rate))
        self.last_updated = current_time

    def decay(self, decay_rate: float = 0.01) -> None:
        self.confidence = max(0.0, self.confidence - decay_rate)

    def __repr__(self) -> str:
        return f"[Belief] {self.subject} conf={self.confidence:.2f} val={self.valence:+.2f}"


class BeliefSystem:
    """Manages all beliefs for an NPC."""

    def __init__(self):
        self._nodes: dict[str, BeliefNode] = {}

    @property
    def nodes(self) -> dict[str, BeliefNode]:
        return self._nodes

    def get_or_create(self, subject: str) -> BeliefNode:
        if subject not in self._nodes:
            self._nodes[subject] = BeliefNode(subject)
        return self._nodes[subject]

    def process_event(self, sim_event: SimEvent, subject_keys: list[str],
                      current_time: float, learning_rate: float = 0.1) -> None:
        if sim_event is None:
            return
        for key in subject_keys:
            self.get_or_create(key).reinforce(sim_event, current_time, learning_rate)

    def decay_all(self, decay_rate: float = 0.01) -> None:
        for node in self._nodes.values():
            node.decay(decay_rate)

    def __repr__(self) -> str:
        return f"[BeliefSystem] {len(self._nodes)} belief node(s)"
