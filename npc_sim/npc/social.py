# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""NPC social relationships, reputation, and relation time-decay."""

from __future__ import annotations


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(val, hi))


class Relation:
    """A directed relationship from one NPC to another."""

    def __init__(self, owner_id: str, target_id: str):
        self.owner_id = owner_id
        self.target_id = target_id
        self.trust: float = 0.0
        self.affinity: float = 0.0
        self.respect: float = 0.0
        self.last_interaction_time: float = 0.0

    @property
    def relation_type(self) -> str:
        avg = (self.trust + self.affinity + self.respect) / 3.0
        if avg > 0.5:
            return "Friend"
        elif avg < -0.3:
            return "Enemy"
        return "Neutral"

    def apply_interaction(self, trust_delta: float, affinity_delta: float,
                          respect_delta: float, current_time: float) -> None:
        self.trust = _clamp(self.trust + trust_delta, -1.0, 1.0)
        self.affinity = _clamp(self.affinity + affinity_delta, -1.0, 1.0)
        self.respect = _clamp(self.respect + respect_delta, -1.0, 1.0)
        self.last_interaction_time = current_time

    def decay_over_time(self, delta_time: float, decay_rate: float = 0.00005) -> None:
        decay = delta_time * decay_rate
        if self.trust > 0:
            self.trust = max(0.0, self.trust - decay)
        elif self.trust < 0:
            self.trust = min(0.0, self.trust + decay)

        if self.affinity > 0:
            self.affinity = max(0.0, self.affinity - decay)
        elif self.affinity < 0:
            self.affinity = min(0.0, self.affinity + decay)

        if self.respect > 0:
            self.respect = max(0.0, self.respect - decay)
        elif self.respect < 0:
            self.respect = min(0.0, self.respect + decay)

    def to_dict(self) -> dict:
        return {
            "target_id": self.target_id,
            "trust": round(self.trust, 3),
            "affinity": round(self.affinity, 3),
            "respect": round(self.respect, 3),
            "relation_type": self.relation_type,
        }

    def __repr__(self) -> str:
        return (f"[Relation] {self.owner_id}→{self.target_id} "
                f"T:{self.trust:.2f} A:{self.affinity:.2f} R:{self.respect:.2f} ({self.relation_type})")


class NPCSocial:
    """Manages social relationships, reputation, and group standing for an NPC."""

    def __init__(self, initial_reputation: float = 0.5, initial_group_standing: float = 0.5):
        self._relations: dict[str, Relation] = {}
        self.reputation = _clamp(initial_reputation, 0.0, 1.0)
        self.group_standing = _clamp(initial_group_standing, 0.0, 1.0)

    @property
    def relations(self) -> dict[str, Relation]:
        return self._relations

    def get_or_create_relation(self, owner_id: str, target_id: str) -> Relation:
        if target_id not in self._relations:
            self._relations[target_id] = Relation(owner_id, target_id)
        return self._relations[target_id]

    def get_relation(self, target_id: str) -> Relation | None:
        return self._relations.get(target_id)

    def get_relations_by_type(self, rel_type: str) -> list[Relation]:
        return [r for r in self._relations.values() if r.relation_type == rel_type]

    def modify_reputation(self, delta: float) -> None:
        self.reputation = _clamp(self.reputation + delta, 0.0, 1.0)

    def modify_group_standing(self, delta: float) -> None:
        self.group_standing = _clamp(self.group_standing + delta, 0.0, 1.0)

    def tick_decay(self, delta_time: float, decay_rate: float = 0.00005) -> None:
        for rel in self._relations.values():
            rel.decay_over_time(delta_time, decay_rate)

    def to_dict(self) -> dict:
        return {
            "reputation": round(self.reputation, 3),
            "group_standing": round(self.group_standing, 3),
            "relations": [r.to_dict() for r in self._relations.values()],
        }

    def __repr__(self) -> str:
        return (f"[Social] Relations:{len(self._relations)} | "
                f"Rep:{self.reputation:.0%} | Group:{self.group_standing:.0%}")
