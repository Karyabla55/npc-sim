# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""NPC episodic memory with O(1) circular ring buffer."""

from __future__ import annotations
import math
from npc_sim.events.sim_event import SimEvent


class MemoryEntry:
    """A single episodic memory entry."""

    def __init__(self, sim_event: SimEvent, emotional_weight: float, recorded_at: float):
        self.event = sim_event
        self.emotional_weight = max(-1.0, min(emotional_weight, 1.0))
        self.recorded_at = recorded_at

    def decay(self, rate: float) -> None:
        sign = 1.0 if self.emotional_weight >= 0 else -1.0
        mag = max(0.0, min(abs(self.emotional_weight) - rate, 1.0))
        self.emotional_weight = sign * mag

    def __repr__(self) -> str:
        return f"[Mem] {self.event.event_type} EW:{self.emotional_weight:+.2f} @t={self.recorded_at:.1f}"


class NPCMemory:
    """
    NPC's episodic memory — O(1) circular ring buffer.
    Iteration is most-recent-first.
    """

    def __init__(self, capacity: int = 50):
        self.capacity = max(1, capacity)
        self._ring: list[MemoryEntry | None] = [None] * self.capacity
        self._head = 0
        self._count = 0

    @property
    def count(self) -> int:
        return self._count

    def remember(self, sim_event: SimEvent, emotional_weight: float, current_time: float) -> None:
        if sim_event is None:
            return
        self._ring[self._head] = MemoryEntry(sim_event, emotional_weight, current_time)
        self._head = (self._head + 1) % self.capacity
        if self._count < self.capacity:
            self._count += 1

    def for_each_recent(self, visitor) -> None:
        for i in range(self._count):
            idx = (self._head - 1 - i + self.capacity) % self.capacity
            entry = self._ring[idx]
            if entry is not None:
                visitor(entry)

    def get_by_event_type(self, event_type: str) -> list[MemoryEntry]:
        result = []
        self.for_each_recent(lambda e: result.append(e) if e.event.event_type == event_type else None)
        return result

    def get_related_to(self, npc_id: str) -> list[MemoryEntry]:
        result = []
        def _check(e: MemoryEntry):
            if e.event.initiator_id == npc_id or e.event.target_id == npc_id:
                result.append(e)
        self.for_each_recent(_check)
        return result

    def get_recent(self, current_time: float, window_seconds: float) -> list[MemoryEntry]:
        result = []
        self.for_each_recent(
            lambda e: result.append(e) if current_time - e.recorded_at <= window_seconds else None
        )
        return result

    def get_most_salient(self) -> MemoryEntry | None:
        best = None
        peak = 0.0
        def _check(e: MemoryEntry):
            nonlocal best, peak
            a = abs(e.emotional_weight)
            if a > peak:
                peak = a
                best = e
        self.for_each_recent(_check)
        return best

    def decay_all(self, decay_rate: float = 0.005) -> None:
        for i in range(self._count):
            entry = self._ring[i]
            if entry is not None:
                entry.decay(decay_rate)

    def to_list(self) -> list[MemoryEntry]:
        result = []
        self.for_each_recent(result.append)
        return result

    def __repr__(self) -> str:
        return f"[Memory] {self._count}/{self.capacity} entries"
