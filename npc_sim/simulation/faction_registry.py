# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Inter-faction disposition matrix with time-decay toward neutrality."""

from __future__ import annotations


class FactionRegistry:
    """Manages faction registrations and inter-faction dispositions."""

    def __init__(self):
        self._factions: set[str] = set()
        self._dispositions: dict[tuple[str, str], float] = {}
        self._decay_rate: float = 0.0001

    def register_faction(self, faction: str) -> None:
        self._factions.add(faction)

    def set_mutual_disposition(self, a: str, b: str, value: float) -> None:
        value = max(-1.0, min(value, 1.0))
        self._dispositions[(a, b)] = value
        self._dispositions[(b, a)] = value

    def get_disposition(self, a: str, b: str) -> float:
        return self._dispositions.get((a, b), 0.0)

    def tick_decay(self, delta_time: float) -> None:
        decay = self._decay_rate * delta_time
        keys_to_remove = []
        for key, val in self._dispositions.items():
            if val > 0:
                self._dispositions[key] = max(0.0, val - decay)
            elif val < 0:
                self._dispositions[key] = min(0.0, val + decay)
            if abs(self._dispositions[key]) < 1e-6:
                keys_to_remove.append(key)
        for k in keys_to_remove:
            del self._dispositions[k]

    def __repr__(self) -> str:
        return f"[FactionRegistry] {len(self._factions)} factions, {len(self._dispositions)} dispositions"
