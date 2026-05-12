# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""B3: Utility AI reads target reputation for Socialize + Trade."""

from types import SimpleNamespace
from npc_sim.decisions.actions.builtin import SocializeAction, TradeAction
from npc_sim.npc.beliefs import BeliefSystem
from npc_sim.perception.perceived_object import PerceivedObject


class _FakeSocial:
    def __init__(self, reputation: float):
        self.reputation = reputation


class _FakeWorld:
    def __init__(self, by_id):
        self._npcs = by_id

    def get_npc_by_id(self, nid):
        return self._npcs.get(nid)


def _ctx(action_target_reputation: float | None, *, is_trade: bool = False):
    target_id = "tgt"
    target = SimpleNamespace(social=_FakeSocial(action_target_reputation)) \
        if action_target_reputation is not None else None
    world = _FakeWorld({target_id: target})
    beliefs = BeliefSystem()
    npc = SimpleNamespace(
        identity=SimpleNamespace(npc_id="me"),
        beliefs=beliefs,
        psychology=SimpleNamespace(extraversion=0.6),
        schedule=SimpleNamespace(preference_at=lambda _k, _h: 0.5),
        traits=SimpleNamespace(get_weight_modifier=lambda _t: 1.0),
        inventory=SimpleNamespace(has=lambda i: True),
        goals=SimpleNamespace(has_active_goal=lambda _t: False),
    )
    ally = PerceivedObject(
        object_id=target_id, object_type="NPC", tag="NPC",
        position=SimpleNamespace(x=0, y=0, z=0),
        first_seen=0.0, salience=1.0, threat_level=0.0,
    )
    return SimpleNamespace(
        self_npc=npc,
        world=world,
        sim_day_hour=12.0,
        belief_score=lambda _s: 0.0,
        goal_bonus=lambda _gt: 0.0,
        get_top_percept=lambda tag: ally if tag in ("Ally", "NPC") else None,
        has_percept=lambda tag: tag in ("Ally", "NPC"),
    )


def test_socialize_score_rises_with_target_reputation():
    act = SocializeAction()
    low  = act.evaluate(_ctx(0.0))
    mid  = act.evaluate(_ctx(0.5))
    high = act.evaluate(_ctx(1.0))
    assert low < mid < high


def test_socialize_neutral_when_target_unknown():
    act = SocializeAction()
    none = act.evaluate(_ctx(None))
    mid  = act.evaluate(_ctx(0.5))
    assert abs(none - mid) < 1e-6


def test_trade_drops_for_disreputable_target():
    act = TradeAction()
    good = act.evaluate(_ctx(0.8, is_trade=True))
    bad  = act.evaluate(_ctx(0.1, is_trade=True))
    assert (good - bad) >= 0.25
