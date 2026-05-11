# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""A1: Inventory per-stack cap invariants."""

from npc_sim.npc.inventory import NPCInventory, ItemIds


def test_add_caps_existing_stack_at_default_100():
    inv = NPCInventory(capacity=10)
    for _ in range(150):
        inv.add(ItemIds.GRAIN, 1)
    assert inv.get_amount(ItemIds.GRAIN) == 100


def test_add_returns_false_when_stack_full():
    inv = NPCInventory(capacity=10)
    for _ in range(100):
        assert inv.add(ItemIds.GOLD, 1) is True
    assert inv.add(ItemIds.GOLD, 1) is False
    assert inv.get_amount(ItemIds.GOLD) == 100


def test_add_clamps_initial_amount_to_cap():
    inv = NPCInventory(capacity=10)
    inv.add(ItemIds.TOOLS, 500)
    assert inv.get_amount(ItemIds.TOOLS) == 100


def test_add_with_custom_cap_respects_caller():
    inv = NPCInventory(capacity=10)
    inv.add(ItemIds.WATER, 8, stack_cap=5)
    assert inv.get_amount(ItemIds.WATER) == 5


def test_capacity_still_blocks_new_stacks():
    inv = NPCInventory(capacity=2)
    inv.add(ItemIds.FOOD, 1)
    inv.add(ItemIds.WATER, 1)
    assert inv.add(ItemIds.GOLD, 1) is False
