# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Deterministic pseudo-random number generator for the simulation."""

from __future__ import annotations
import random
from typing import List, TypeVar

T = TypeVar("T")


class SimRng:
    """
    Deterministic PRNG. All randomness in the simulation flows through this class.
    Given the same seed, identical sequences are produced every time —
    enabling full replay support.
    """

    def __init__(self, seed: int = 42):
        self._seed = seed
        self._random = random.Random(seed)
        self._call_count = 0

    @property
    def seed(self) -> int:
        return self._seed

    @property
    def call_count(self) -> int:
        return self._call_count

    # ── Primitives ──

    def next_float(self, min_val: float = 0.0, max_val: float = 1.0) -> float:
        """Returns a float in [min_val, max_val)."""
        self._call_count += 1
        if min_val == 0.0 and max_val == 1.0:
            return self._random.random()
        return min_val + self._random.random() * (max_val - min_val)

    def next_int(self, min_val: int, max_exclusive: int) -> int:
        """Returns an int in [min_val, max_exclusive)."""
        self._call_count += 1
        return self._random.randint(min_val, max_exclusive - 1)

    def chance(self, probability: float) -> bool:
        """Returns True with the given probability [0, 1]."""
        self._call_count += 1
        return self._random.random() < probability

    # ── ID Generation ──

    def next_id(self, prefix: str = "id") -> str:
        """
        Generates a deterministic, unique-ish ID string.
        Format: '{prefix}_{hex}' — avoids uuid4 which is non-deterministic.
        """
        hash_val = (self._seed * 2654435761) ^ (self._call_count * 40503)
        hash_val = hash_val & 0xFFFFFFFF  # keep 32-bit
        self._call_count += 1
        return f"{prefix}_{hash_val:08x}"

    # ── Helpers ──

    def shuffle(self, lst: List[T]) -> None:
        """Shuffles a list in-place using Fisher-Yates."""
        for i in range(len(lst) - 1, 0, -1):
            j = self.next_int(0, i + 1)
            lst[i], lst[j] = lst[j], lst[i]

    def __repr__(self) -> str:
        return f"[SimRng] seed={self._seed} calls={self._call_count}"
