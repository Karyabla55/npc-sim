# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Per-tick aggregate population statistics."""

from __future__ import annotations
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from npc_sim.npc.npc import NPC
    from npc_sim.events.sim_event import SimEvent


class PopulationStats:
    """Real-time aggregate metrics for the entire population."""

    def __init__(self):
        self.total_population: int = 0
        self.avg_hunger: float = 0.0
        self.avg_thirst: float = 0.0
        self.avg_happiness: float = 0.0
        self.avg_stress: float = 0.0
        self.total_deaths: int = 0
        self.recent_combat_count: int = 0
        self.is_at_war: bool = False

    def update(self, npcs: list, event_log) -> None:
        alive = [n for n in npcs if n.is_active and n.vitals.is_alive]
        self.total_population = len(alive)

        if not alive:
            return

        self.avg_hunger = sum(n.vitals.hunger for n in alive) / len(alive)
        self.avg_thirst = sum(n.vitals.thirst for n in alive) / len(alive)
        self.avg_happiness = sum(n.psychology.happiness for n in alive) / len(alive)
        self.avg_stress = sum(n.vitals.stress for n in alive) / len(alive)

        # Count recent combat events
        self.recent_combat_count = sum(
            1 for e in event_log if e.category == "combat"
        )
        self.is_at_war = self.recent_combat_count > 5

    def is_famine(self) -> bool:
        return self.avg_hunger > 0.7

    def is_prosperous(self) -> bool:
        return self.avg_happiness > 0.5 and self.avg_hunger < 0.3

    def to_dict(self) -> dict:
        return {
            "total_population": self.total_population,
            "avg_hunger": round(self.avg_hunger, 3),
            "avg_thirst": round(self.avg_thirst, 3),
            "avg_happiness": round(self.avg_happiness, 3),
            "avg_stress": round(self.avg_stress, 3),
            "is_at_war": self.is_at_war,
            "is_famine": self.is_famine(),
            "is_prosperous": self.is_prosperous(),
        }

    def __repr__(self) -> str:
        return (f"[PopStats] Pop:{self.total_population} "
                f"Hunger:{self.avg_hunger:.0%} Stress:{self.avg_stress:.0%}")
