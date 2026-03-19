# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""NPC physical life stats: health, energy, hunger, thirst, stress."""

from __future__ import annotations


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(val, hi))


class NPCVitals:
    """Tracks an NPC's physical life stats. All setters clamp to valid ranges."""

    def __init__(self, max_health: float = 100.0, max_energy: float = 100.0):
        self.max_health = max_health
        self.health = max_health
        self.max_energy = max_energy
        self.energy = max_energy
        self.hunger: float = 0.0
        self.thirst: float = 0.0
        self.stress: float = 0.0

    @property
    def is_alive(self) -> bool:
        return self.health > 0.0

    @property
    def energy_norm(self) -> float:
        return self.energy / self.max_energy if self.max_energy > 0.0 else 0.0

    # ── Mutations ──

    def apply_damage(self, amount: float) -> None:
        self.health = _clamp(self.health - amount, 0.0, self.max_health)

    def heal(self, amount: float) -> None:
        self.health = _clamp(self.health + amount, 0.0, self.max_health)

    def set_health(self, value: float) -> None:
        self.health = _clamp(value, 0.0, self.max_health)

    def consume_energy(self, amount: float) -> None:
        self.energy = _clamp(self.energy - amount, 0.0, self.max_energy)

    def restore_energy(self, amount: float) -> None:
        self.energy = _clamp(self.energy + amount, 0.0, self.max_energy)

    def set_energy(self, value: float) -> None:
        self.energy = _clamp(value, 0.0, self.max_energy)

    def set_hunger(self, value: float) -> None:
        self.hunger = _clamp(value, 0.0, 1.0)

    def set_thirst(self, value: float) -> None:
        self.thirst = _clamp(value, 0.0, 1.0)

    def set_stress(self, value: float) -> None:
        self.stress = _clamp(value, 0.0, 1.0)

    def to_dict(self) -> dict:
        return {
            "health": round(self.health, 2),
            "max_health": self.max_health,
            "energy": round(self.energy, 2),
            "max_energy": self.max_energy,
            "hunger": round(self.hunger, 4),
            "thirst": round(self.thirst, 4),
            "stress": round(self.stress, 4),
            "is_alive": self.is_alive,
        }

    def __repr__(self) -> str:
        return (f"[Vitals] HP:{self.health:.0f}/{self.max_health:.0f} "
                f"EN:{self.energy:.0f}/{self.max_energy:.0f} "
                f"Hunger:{self.hunger:.0%} Thirst:{self.thirst:.0%} Stress:{self.stress:.0%}")
