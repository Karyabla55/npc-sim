# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""C1 / #15: WorkAction yield scales with efficiency."""

from types import SimpleNamespace
from npc_sim.decisions.actions.builtin import WorkAction
from npc_sim.npc.inventory import NPCInventory, ItemIds


class _AlwaysChance:
    def chance(self, _p):
        return True


class _NeverChance:
    def chance(self, _p):
        return False


def _npc(energy_norm: float, occupation: str = "farmer"):
    inv = NPCInventory(capacity=10)
    return SimpleNamespace(
        identity=SimpleNamespace(npc_id="me", display_name="Me", occupation=occupation),
        position=SimpleNamespace(x=0, y=0, z=0),
        vitals=SimpleNamespace(
            energy_norm=energy_norm,
            consume_energy=lambda _a: None,
        ),
        inventory=inv,
    )


def test_full_energy_yields_two():
    npc = _npc(1.0)
    ctx = SimpleNamespace(self_npc=npc, delta_time=0.1, rng=_AlwaysChance(),
                          world=None, current_time=0.0)
    WorkAction().execute(ctx)
    assert npc.inventory.get_amount(ItemIds.GRAIN) == 2


def test_mid_energy_yields_one():
    npc = _npc(0.5)
    ctx = SimpleNamespace(self_npc=npc, delta_time=0.1, rng=_AlwaysChance(),
                          world=None, current_time=0.0)
    WorkAction().execute(ctx)
    assert npc.inventory.get_amount(ItemIds.GRAIN) == 1


def test_low_energy_still_yields_at_least_one():
    npc = _npc(0.1)
    ctx = SimpleNamespace(self_npc=npc, delta_time=0.1, rng=_AlwaysChance(),
                          world=None, current_time=0.0)
    WorkAction().execute(ctx)
    assert npc.inventory.get_amount(ItemIds.GRAIN) == 1


def test_failed_chance_yields_nothing():
    npc = _npc(1.0)
    ctx = SimpleNamespace(self_npc=npc, delta_time=0.1, rng=_NeverChance(),
                          world=None, current_time=0.0)
    WorkAction().execute(ctx)
    assert npc.inventory.get_amount(ItemIds.GRAIN) == 0


def test_merchant_yield_is_gold():
    npc = _npc(1.0, occupation="merchant")
    ctx = SimpleNamespace(self_npc=npc, delta_time=0.1, rng=_AlwaysChance(),
                          world=None, current_time=0.0)
    WorkAction().execute(ctx)
    assert npc.inventory.get_amount(ItemIds.GOLD) == 2
