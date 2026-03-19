# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Unity-free 3D vector for use throughout the simulation core."""

from __future__ import annotations
import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SimVector3:
    """Immutable 3D vector. All simulation positions and directions use this type."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    # ── Class-level constants (set after class definition) ──

    @property
    def sqr_magnitude(self) -> float:
        return self.x * self.x + self.y * self.y + self.z * self.z

    @property
    def magnitude(self) -> float:
        return math.sqrt(self.sqr_magnitude)

    def normalized(self) -> SimVector3:
        m = self.magnitude
        if m < 1e-6:
            return SimVector3.ZERO
        return SimVector3(self.x / m, self.y / m, self.z / m)

    def within_radius(self, other: SimVector3, radius: float) -> bool:
        return SimVector3.sqr_distance(self, other) <= radius * radius

    # ── Static math ──

    @staticmethod
    def sqr_distance(a: SimVector3, b: SimVector3) -> float:
        dx = a.x - b.x
        dy = a.y - b.y
        dz = a.z - b.z
        return dx * dx + dy * dy + dz * dz

    @staticmethod
    def distance(a: SimVector3, b: SimVector3) -> float:
        return math.sqrt(SimVector3.sqr_distance(a, b))

    # ── Operators ──

    def __add__(self, other: SimVector3) -> SimVector3:
        return SimVector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: SimVector3) -> SimVector3:
        return SimVector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> SimVector3:
        return SimVector3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> SimVector3:
        return self.__mul__(scalar)

    def __repr__(self) -> str:
        return f"({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"


# Class-level constants
SimVector3.ZERO = SimVector3(0.0, 0.0, 0.0)
SimVector3.ONE = SimVector3(1.0, 1.0, 1.0)
