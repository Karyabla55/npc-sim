# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""C2 / #20: trait coherence override for Coward, Greedy, Devout."""

from types import SimpleNamespace
from npc_sim.llm.llm_backend import LLMResponse
from npc_sim.llm.llm_decision_system import LLMDecisionSystem


class _FakeTraits:
    def __init__(self, *names):
        self._names = set(names)

    def has(self, name):
        return name in self._names


class _FakeAction:
    def __init__(self, action_id: str, valid: bool = True):
        self.action_id = action_id
        self._valid = valid

    def is_valid(self, _ctx):
        return self._valid


class _FakeLibrary:
    def __init__(self, *actions):
        self._actions = list(actions)

    def get_all(self):
        return self._actions


def _system_with_library(*actions):
    sys = LLMDecisionSystem.__new__(LLMDecisionSystem)
    sys._library = _FakeLibrary(*actions)
    return sys


def _resp(action_id: str = "work"):
    return LLMResponse(
        npc_id="me", reasoning="r", action_id=action_id, target_id=None,
        dialogue=None, emotion=None, raw="{}", latency_ms=0.0,
    )


def _ctx(*, traits, stress=0.0, has_gold=False, threat_level=0.0):
    npc = SimpleNamespace(
        traits=traits,
        psychology=SimpleNamespace(fear=0.5),
        vitals=SimpleNamespace(stress=stress),
        inventory=SimpleNamespace(has=lambda i: has_gold),
        identity=SimpleNamespace(npc_id="me"),
    )
    threat = None
    if threat_level > 0.0:
        threat = SimpleNamespace(object_id="enemy", threat_level=threat_level)
    return SimpleNamespace(
        self_npc=npc,
        get_top_percept=lambda tag: threat if tag == "Threat" else None,
    )


def test_coward_redirects_to_flee_under_threat():
    sys = _system_with_library()
    out = sys._enforce_trait_coherence(
        _resp("work"), _ctx(traits=_FakeTraits("Coward"), threat_level=0.7))
    assert out.action_id == "flee"
    assert out.target_id == "enemy"


def test_coward_does_not_override_below_threshold():
    sys = _system_with_library()
    out = sys._enforce_trait_coherence(
        _resp("work"), _ctx(traits=_FakeTraits("Coward"), threat_level=0.3))
    assert out.action_id == "work"


def test_greedy_redirects_to_trade_when_valid():
    sys = _system_with_library(_FakeAction("trade", valid=True))
    out = sys._enforce_trait_coherence(
        _resp("work"), _ctx(traits=_FakeTraits("Greedy"), has_gold=True))
    assert out.action_id == "trade"


def test_greedy_no_op_when_trade_invalid():
    sys = _system_with_library(_FakeAction("trade", valid=False))
    out = sys._enforce_trait_coherence(
        _resp("work"), _ctx(traits=_FakeTraits("Greedy"), has_gold=True))
    assert out.action_id == "work"


def test_greedy_no_op_without_gold():
    sys = _system_with_library(_FakeAction("trade", valid=True))
    out = sys._enforce_trait_coherence(
        _resp("work"), _ctx(traits=_FakeTraits("Greedy"), has_gold=False))
    assert out.action_id == "work"


def test_devout_redirects_to_pray_under_stress():
    sys = _system_with_library(_FakeAction("pray", valid=True))
    out = sys._enforce_trait_coherence(
        _resp("work"), _ctx(traits=_FakeTraits("Devout"), stress=0.7))
    assert out.action_id == "pray"


def test_devout_no_op_below_stress_threshold():
    sys = _system_with_library(_FakeAction("pray", valid=True))
    out = sys._enforce_trait_coherence(
        _resp("work"), _ctx(traits=_FakeTraits("Devout"), stress=0.3))
    assert out.action_id == "work"
