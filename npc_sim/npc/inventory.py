# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""NPC inventory: slot-based item container."""

from __future__ import annotations


class ItemIds:
    """String constants for all built-in item types."""
    FOOD = "food"
    WATER = "water"
    MEDICINE = "medicine"
    WOOD = "wood"
    STONE = "stone"
    GOLD = "gold"
    GRAIN = "grain"
    CLOTH = "cloth"
    TOOLS = "tools"
    WEAPON = "weapon"


class ItemStack:
    """A quantity of a single item type."""

    def __init__(self, item_id: str, amount: int):
        self.item_id = item_id
        self.amount = max(0, amount)

    def add(self, n: int) -> None:
        self.amount += max(0, n)

    def remove(self, n: int) -> None:
        self.amount = max(0, self.amount - n)

    def __repr__(self) -> str:
        return f"{self.item_id}×{self.amount}"


class NPCInventory:
    """NPC's personal inventory — a simple slot-based container for resource items."""

    def __init__(self, capacity: int = 10):
        self._capacity = max(1, capacity)
        self._stacks: list[ItemStack] = []

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def stacks(self) -> list[ItemStack]:
        return self._stacks

    def get_amount(self, item_id: str) -> int:
        for stack in self._stacks:
            if stack.item_id == item_id:
                return stack.amount
        return 0

    def has(self, item_id: str, amount: int = 1) -> bool:
        return self.get_amount(item_id) >= amount

    def add(self, item_id: str, amount: int = 1) -> bool:
        for stack in self._stacks:
            if stack.item_id == item_id:
                stack.add(amount)
                return True
        if len(self._stacks) >= self._capacity:
            return False
        self._stacks.append(ItemStack(item_id, amount))
        return True

    def remove(self, item_id: str, amount: int = 1) -> bool:
        for i, stack in enumerate(self._stacks):
            if stack.item_id != item_id:
                continue
            if stack.amount < amount:
                return False
            stack.remove(amount)
            if stack.amount <= 0:
                self._stacks.pop(i)
            return True
        return False

    def clear(self) -> None:
        self._stacks.clear()

    def to_dict(self) -> dict:
        return {
            "capacity": self._capacity,
            "stacks": [{"item_id": s.item_id, "amount": s.amount} for s in self._stacks],
        }

    def __repr__(self) -> str:
        return f"[Inventory] {len(self._stacks)}/{self._capacity} stacks"
