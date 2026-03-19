# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""NPC personality traits: multiplier tags for utility scoring."""

from __future__ import annotations


class NPCTraits:
    """
    Immutable set of personality trait tags.
    Traits act as multipliers inside UtilityEvaluator, biasing action scores.
    """

    # Well-known trait constants
    BRAVE = "Brave"
    COWARD = "Coward"
    GREEDY = "Greedy"
    GENEROUS = "Generous"
    LOYAL = "Loyal"
    TREACHEROUS = "Treacherous"
    CURIOUS = "Curious"
    CAUTIOUS = "Cautious"
    AGGRESSIVE = "Aggressive"
    PACIFIST = "Pacifist"

    def __init__(self, *initial_tags: str):
        self._tags: set[str] = set()
        for tag in initial_tags:
            if tag and tag.strip():
                self._tags.add(tag)

    @property
    def tags(self) -> set[str]:
        return self._tags

    def has(self, trait: str) -> bool:
        return trait.lower() in {t.lower() for t in self._tags}

    def has_any(self, *traits: str) -> bool:
        lower_tags = {t.lower() for t in self._tags}
        return any(t.lower() in lower_tags for t in traits)

    def has_all(self, *traits: str) -> bool:
        lower_tags = {t.lower() for t in self._tags}
        return all(t.lower() in lower_tags for t in traits)

    def get_weight_modifier(self, action_type: str) -> float:
        modifier = 1.0
        at = action_type.lower()

        if at == "flee":
            if self.has(self.BRAVE):
                modifier -= 0.35
            if self.has(self.COWARD):
                modifier += 0.50
        elif at == "attack":
            if self.has(self.AGGRESSIVE):
                modifier += 0.40
            if self.has(self.PACIFIST):
                modifier -= 0.50
            if self.has(self.BRAVE):
                modifier += 0.20
        elif at == "trade":
            if self.has(self.GREEDY):
                modifier += 0.30
            if self.has(self.GENEROUS):
                modifier += 0.15
        elif at == "explore":
            if self.has(self.CURIOUS):
                modifier += 0.35
            if self.has(self.CAUTIOUS):
                modifier -= 0.20

        return max(0.1, min(modifier, 2.0))

    def to_dict(self) -> dict:
        return {"tags": list(self._tags)}

    def __repr__(self) -> str:
        if not self._tags:
            return "[Traits] None"
        return f"[Traits] {', '.join(self._tags)}"
