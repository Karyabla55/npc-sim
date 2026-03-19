# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Dictionary-bucketed uniform spatial grid for fast NPC radius queries."""

from __future__ import annotations
import math
from abc import ABC, abstractmethod
from npc_sim.core.sim_vector3 import SimVector3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from npc_sim.npc.npc import NPC


class ISpatialGrid(ABC):
    @abstractmethod
    def insert(self, npc) -> None: ...
    @abstractmethod
    def remove(self, npc) -> None: ...
    @abstractmethod
    def update(self, npc) -> None: ...
    @abstractmethod
    def clear(self) -> None: ...
    @abstractmethod
    def query_radius(self, center: SimVector3, radius: float) -> list: ...


class DictionaryGrid(ISpatialGrid):
    """O(1) insert/remove, O(k) radius query where k = NPCs in candidate cells."""

    def __init__(self, cell_size: float = 50.0):
        self._cell_size = max(1.0, cell_size)
        self._cells: dict[int, list] = {}
        self._index: dict[str, tuple[int, int]] = {}

    def insert(self, npc) -> None:
        cx, cy = self._cell(npc.position)
        self._get_or_create(cx, cy).append(npc)
        self._index[npc.identity.npc_id] = (cx, cy)

    def remove(self, npc) -> None:
        cell = self._index.get(npc.identity.npc_id)
        if cell is None:
            return
        key = self._key(cell[0], cell[1])
        bucket = self._cells.get(key)
        if bucket:
            try:
                bucket.remove(npc)
            except ValueError:
                pass
        self._index.pop(npc.identity.npc_id, None)

    def update(self, npc) -> None:
        old = self._index.get(npc.identity.npc_id)
        if old:
            ncx, ncy = self._cell(npc.position)
            if ncx == old[0] and ncy == old[1]:
                return
            key = self._key(old[0], old[1])
            bucket = self._cells.get(key)
            if bucket:
                try:
                    bucket.remove(npc)
                except ValueError:
                    pass
        self.insert(npc)

    def clear(self) -> None:
        self._cells.clear()
        self._index.clear()

    def query_radius(self, center: SimVector3, radius: float) -> list:
        cell_r = int(math.ceil(radius / self._cell_size))
        cx, cy = self._cell(center)
        result = []
        sqr_r = radius * radius

        for dx in range(-cell_r, cell_r + 1):
            for dy in range(-cell_r, cell_r + 1):
                key = self._key(cx + dx, cy + dy)
                bucket = self._cells.get(key)
                if not bucket:
                    continue
                for npc in bucket:
                    if SimVector3.sqr_distance(center, npc.position) <= sqr_r:
                        result.append(npc)
        return result

    def _cell(self, pos: SimVector3) -> tuple[int, int]:
        return (int(math.floor(pos.x / self._cell_size)),
                int(math.floor(pos.z / self._cell_size)))

    def _get_or_create(self, cx: int, cy: int) -> list:
        key = self._key(cx, cy)
        if key not in self._cells:
            self._cells[key] = []
        return self._cells[key]

    @staticmethod
    def _key(x: int, y: int) -> int:
        return (x << 32) | (y & 0xFFFFFFFF)
