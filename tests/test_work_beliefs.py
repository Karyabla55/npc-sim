# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""B2: WorkAction penalizes occupations whose home-zone has negative beliefs."""

from types import SimpleNamespace
from npc_sim.decisions.actions.builtin import WorkAction
from npc_sim.npc.beliefs import BeliefSystem
from npc_sim.simulation.world_map import WorldMap


def _ctx(occupation: str, zone_belief: float = 0.0, zone_conf: float = 0.0,
        sched_pref: float = 0.8, conscientiousness: float = 0.7, energy: float = 0.9):
    beliefs = BeliefSystem()
    zone_name = WorldMap.get_home_zone_name(occupation)
    if zone_conf > 0:
        n = beliefs.get_or_create(zone_name)
        n.valence = zone_belief
        n.confidence = zone_conf
    npc = SimpleNamespace(
        identity=SimpleNamespace(occupation=occupation),
        beliefs=beliefs,
        psychology=SimpleNamespace(conscientiousness=conscientiousness),
        vitals=SimpleNamespace(energy_norm=energy),
        schedule=SimpleNamespace(preference_at=lambda _k, _h: sched_pref),
    )
    return SimpleNamespace(
        self_npc=npc,
        sim_day_hour=12.0,
        belief_score=lambda subj: (
            beliefs.nodes[subj].valence * beliefs.nodes[subj].confidence
            if subj in beliefs.nodes else 0.0
        ),
        goal_bonus=lambda _gt: 0.0,
    )


def test_work_zone_helper_maps_occupations():
    assert WorldMap.get_home_zone_name("farmer") == "Farm"
    assert WorldMap.get_home_zone_name("guard") == "Barracks"
    assert WorldMap.get_home_zone_name("merchant") == "Market"
    assert WorldMap.get_home_zone_name("unknown_role") == "Tavern"


def test_baseline_score_no_zone_belief():
    act = WorkAction()
    s = act.evaluate(_ctx("farmer"))
    assert s > 0.3


def test_negative_zone_belief_drops_work_score():
    act = WorkAction()
    safe = act.evaluate(_ctx("farmer"))
    dangerous = act.evaluate(_ctx("farmer", zone_belief=-1.0, zone_conf=1.0))
    assert dangerous < safe
    assert (safe - dangerous) >= 0.20


def test_positive_zone_belief_does_not_inflate_work():
    act = WorkAction()
    baseline = act.evaluate(_ctx("farmer"))
    pleasant = act.evaluate(_ctx("farmer", zone_belief=1.0, zone_conf=1.0))
    assert pleasant == baseline


def test_score_clamped_to_zero():
    act = WorkAction()
    s = act.evaluate(_ctx("farmer", zone_belief=-1.0, zone_conf=1.0,
                          sched_pref=0.1, conscientiousness=0.1, energy=0.3))
    assert s >= 0.0
