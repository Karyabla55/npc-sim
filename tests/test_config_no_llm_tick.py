# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""C3 / #17: llm_tick_every must be gone from SimulationConfig and the
LLMDecisionSystem constructor (unused, kept LLM cadence ambiguous)."""

import inspect
from npc_sim.core.sim_config import SimulationConfig
from npc_sim.llm.llm_decision_system import LLMDecisionSystem


def test_simulation_config_has_no_llm_tick_every():
    cfg = SimulationConfig()
    assert not hasattr(cfg, "llm_tick_every")


def test_llm_decision_system_init_has_no_llm_tick_every():
    params = inspect.signature(LLMDecisionSystem.__init__).parameters
    assert "llm_tick_every" not in params
