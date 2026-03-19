# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""WorldRegistry: maps (x,z) coordinates to semantic zone labels for LLM payloads.

H1 Fix — LLMs cannot reason about raw coordinates. We label them.
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Zone:
    """An AABB-bounded named region of the world."""
    name: str
    landmark: str
    x0: float
    z0: float
    x1: float
    z1: float

    def contains(self, x: float, z: float) -> bool:
        return self.x0 <= x <= self.x1 and self.z0 <= z <= self.z1


class WorldRegistry:
    """
    Registry mapping world coordinates to semantic zone labels.
    Usage:
        registry = WorldRegistry()
        registry.add_zone(Zone("MarketSquare", "CityGates", 30, 30, 70, 70))
        label = registry.resolve(54.2, 48.7)
        # → {"zone": "MarketSquare", "landmark": "CityGates"}
    """

    def __init__(self, world_size: float = 100.0):
        self._zones: list[Zone] = []
        self._world_size = world_size
        self._setup_defaults(world_size)

    def _setup_defaults(self, size: float) -> None:
        """Auto-generate quadrant-based zones if none are configured."""
        h = size / 2.0
        self._zones = [
            Zone("MarketSquare",   "CentralFountain",  h * 0.3, h * 0.3, h * 1.7, h * 1.7),
            Zone("NorthDistrict",  "CityWall",         0,       0,       size,     h * 0.3),
            Zone("SouthDistrict",  "SouthGate",        0,       h * 1.7, size,     size),
            Zone("WestDistrict",   "StableYard",       0,       0,       h * 0.3,  size),
            Zone("EastDistrict",   "TempleGardens",    h * 1.7, 0,       size,     size),
            Zone("Wilderness",     "OldForestEdge",    0,       0,       size,     size),  # fallback
        ]

    def add_zone(self, zone: Zone) -> None:
        """Prepend zone (higher priority than defaults)."""
        self._zones.insert(0, zone)

    def resolve(self, x: float, z: float) -> dict:
        """Return semantic label dict for NPC payload."""
        for zone in self._zones:
            if zone.contains(x, z):
                return {"zone": zone.name, "landmark": zone.landmark}
        return {"zone": "Outskirts", "landmark": "Unknown"}

    def __repr__(self) -> str:
        return f"[WorldRegistry] {len(self._zones)} zones"


# Singleton used by NPCSerializer — replaced by SimulationManager if configured
_default_registry: WorldRegistry | None = None


def get_default_registry() -> WorldRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = WorldRegistry()
    return _default_registry
