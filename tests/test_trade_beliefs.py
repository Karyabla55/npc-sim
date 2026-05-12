# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""B1: TradeAction reads target belief valence and reinforces on success."""

from types import SimpleNamespace
from npc_sim.decisions.actions.builtin import TradeAction
from npc_sim.npc.beliefs import BeliefSystem
from npc_sim.perception.perceived_object import PerceivedObject


def _make_ctx(belief_valence: float = 0.0, belief_confidence: float = 0.0,
              target_id: str = "tgt", has_gold: bool = True):
    npc_beliefs = BeliefSystem()
    if belief_confidence > 0.0:
        node = npc_beliefs.get_or_create(target_id)
        node.valence = belief_valence
        node.confidence = belief_confidence
    npc = SimpleNamespace(
        identity=SimpleNamespace(npc_id="me"),
        beliefs=npc_beliefs,
        inventory=SimpleNamespace(
            has=lambda item: has_gold,
        ),
        traits=SimpleNamespace(get_weight_modifier=lambda _t: 1.0),
        goals=SimpleNamespace(has_active_goal=lambda _t: False),
    )
    ally = PerceivedObject(
        object_id=target_id, object_type="NPC", tag="NPC",
        position=SimpleNamespace(x=0, y=0, z=0),
        first_seen=0.0, salience=1.0, threat_level=0.0,
    )
    ctx = SimpleNamespace(
        self_npc=npc,
        world=None,
        belief_score=lambda subj: (
            npc_beliefs.nodes[subj].valence * npc_beliefs.nodes[subj].confidence
            if subj in npc_beliefs.nodes else 0.0
        ),
        goal_bonus=lambda _gt: 0.0,
        get_top_percept=lambda tag: ally if tag in ("Ally", "NPC") else None,
    )
    return TradeAction(), ctx


def test_evaluate_baseline_no_belief():
    act, ctx = _make_ctx()
    s = act.evaluate(ctx)
    assert 0.39 <= s <= 0.41


def test_negative_belief_drops_score():
    act, ctx = _make_ctx(belief_valence=-1.0, belief_confidence=1.0)
    s = act.evaluate(ctx)
    assert s < 0.15


def test_positive_belief_lifts_score():
    act, ctx = _make_ctx(belief_valence=1.0, belief_confidence=1.0)
    s = act.evaluate(ctx)
    assert s > 0.5


def test_score_clamped_to_unit_interval():
    act, ctx = _make_ctx(belief_valence=-1.0, belief_confidence=1.0)
    assert act.evaluate(ctx) >= 0.0
    act2, ctx2 = _make_ctx(belief_valence=1.0, belief_confidence=1.0)
    assert act2.evaluate(ctx2) <= 1.0
