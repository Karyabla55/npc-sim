# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""SimulationManager — top-level orchestrator for the deterministic simulation."""

from __future__ import annotations
from npc_sim.core.sim_config import SimulationConfig
from npc_sim.core.sim_clock import SimulationClock
from npc_sim.core.sim_rng import SimRng
from npc_sim.events.sim_event import SimEvent
from npc_sim.npc.npc import NPC
from npc_sim.perception.perception_system import PerceptionSystem
from npc_sim.perception.sensor_range import SensorRangePresets
from npc_sim.decisions.decision_system import DecisionSystem
from npc_sim.decisions.action_library import ActionLibrary
from npc_sim.decisions.action_context import ActionContext
from npc_sim.decisions.utility_evaluator import UtilityEvaluator
from npc_sim.simulation.sim_world import SimWorldAdapter
from npc_sim.simulation.spatial_grid import DictionaryGrid
from npc_sim.simulation.stimulus_dispatcher import StimulusDispatcher
from npc_sim.simulation.faction_registry import FactionRegistry
from npc_sim.simulation.population_stats import PopulationStats
# LLM — imported lazily so simulation runs fine without LLM installed
try:
    from npc_sim.llm.llm_backend import OllamaBackend, MockBackend
    from npc_sim.llm.llm_request_queue import LLMRequestQueue
    from npc_sim.llm.llm_decision_system import LLMDecisionSystem
    from npc_sim.llm.npc_serializer import NPCSerializer
    from npc_sim.llm.world_registry import WorldRegistry
    _LLM_AVAILABLE = True
except ImportError:
    _LLM_AVAILABLE = False


class SimulationManager:
    """
    Top-level orchestrator. Drives the deterministic simulation loop:
    Clock → Stimulus Dispatch → Perception → NPC Tick → Decision → World Update.
    """

    def __init__(self, config: SimulationConfig = None):
        self.config = config or SimulationConfig()
        self.rng = SimRng(self.config.seed)
        self.clock = SimulationClock(
            self.config.day_length_seconds,
            self.config.initial_time_scale,
        )
        self.world = SimWorldAdapter(
            DictionaryGrid(self.config.spatial_grid_cell_size),
            event_log_capacity=500,
            stimulus_queue_size=self.config.stimulus_queue_size,
        )
        self.dispatcher = StimulusDispatcher()
        self.faction_registry = FactionRegistry()
        self.population_stats = PopulationStats()
        self.action_library = ActionLibrary()
        self.evaluator = UtilityEvaluator()

        # Per-NPC systems
        self._perception_systems: dict[str, PerceptionSystem] = {}
        self._decision_systems: dict[str, DecisionSystem] = {}
        self._llm_decision_systems: dict[str, "LLMDecisionSystem"] = {}
        self._last_actions: dict[str, str] = {}
        self._last_reasoning: dict[str, str] = {}
        self._last_dialogue: dict[str, str | None] = {}
        self._last_emotion: dict[str, str | None] = {}

        # LLM subsystems (created on demand)
        self._llm_queue: "LLMRequestQueue | None" = None
        self._llm_backend = None
        self._llm_serializer = None
        self.world_registry: "WorldRegistry | None" = None

        self.tick_count: int = 0

    # ── NPC management ──

    def add_npc(self, npc: NPC) -> None:
        npc.inject_config(self.config)
        self.world.add_npc(npc)

        sensor = SensorRangePresets.for_archetype(npc.identity.personality_archetype)
        ps = PerceptionSystem(sensor=sensor)
        ps.percept_timeout = self.config.percept_timeout
        self._perception_systems[npc.identity.npc_id] = ps

        self._decision_systems[npc.identity.npc_id] = DecisionSystem(
            self.action_library, self.evaluator)

        self.faction_registry.register_faction(npc.identity.faction)

    # ── LLM management ──

    def enable_llm_for(self, npc_id: str) -> bool:
        """Hot-swap one NPC's DecisionSystem to LLMDecisionSystem."""
        if not _LLM_AVAILABLE:
            return False
        self._ensure_llm_subsystems()
        if npc_id not in self._llm_decision_systems:
            self._llm_decision_systems[npc_id] = LLMDecisionSystem(
                library=self.action_library,
                backend=self._llm_backend,
                queue=self._llm_queue,
                serializer=self._llm_serializer,
                evaluator=self.evaluator,
                llm_tick_every=self.config.llm_tick_every,
                timeout_seconds=self.config.llm_timeout_seconds,
                interrupt_threat_threshold=self.config.llm_interrupt_threat_threshold,
                interrupt_hp_drop=self.config.llm_interrupt_hp_drop,
            )
        return True

    def disable_llm_for(self, npc_id: str) -> None:
        self._llm_decision_systems.pop(npc_id, None)

    def enable_llm_for_all(self) -> None:
        for npc_id in list(self._decision_systems.keys()):
            self.enable_llm_for(npc_id)

    def disable_llm_for_all(self) -> None:
        self._llm_decision_systems.clear()

    def set_focused_npc(self, npc_id: str | None) -> None:
        """Mark NPC as UI-focused → priority boost in LLM queue."""
        for nid, ds in self._llm_decision_systems.items():
            ds.focused = (nid == npc_id)

    def get_llm_stats(self) -> dict:
        if self._llm_queue:
            return self._llm_queue.get_stats()
        return {}

    def _ensure_llm_subsystems(self) -> None:
        if self._llm_queue is not None:
            return
        cfg = self.config
        if cfg.llm_backend == "mock":
            self._llm_backend = MockBackend()
        else:
            self._llm_backend = OllamaBackend(
                model=cfg.llm_model,
                base_url=cfg.ollama_base_url,
            )
        self._llm_queue = LLMRequestQueue(
            backend=self._llm_backend,
            max_concurrent=cfg.llm_max_concurrent,
            max_queue_size=cfg.llm_max_queue_size,
        )
        self.world_registry = WorldRegistry()
        self._llm_serializer = NPCSerializer(self.world_registry)

    def remove_npc(self, npc_id: str) -> None:
        self.world.remove_npc(npc_id)
        self._perception_systems.pop(npc_id, None)
        self._decision_systems.pop(npc_id, None)
        self._last_actions.pop(npc_id, None)

    # ── Tick ──

    def tick(self, real_delta: float) -> dict:
        sim_delta = self.clock.tick(real_delta)
        if sim_delta <= 0.0:
            return {}

        current_time = self.clock.current_time
        self.tick_count += 1

        # 1. Dispatch pending stimuli
        pending = self.world.drain_pending_stimuli()
        for stimulus in pending:
            self.dispatcher.dispatch(stimulus, self.world)

        # 2. Faction decay
        self.faction_registry.tick_decay(sim_delta)

        # 3. Per-NPC loop (deterministic order: sorted by NPC ID)
        all_npcs = sorted(self.world.all_npcs, key=lambda n: n.identity.npc_id)
        new_events: list[dict] = []

        for npc in all_npcs:
            if not npc.is_active or not npc.vitals.is_alive:
                continue

            npc_id = npc.identity.npc_id

            # Perception
            ps = self._perception_systems.get(npc_id)
            stimuli = self.dispatcher.drain_for(npc_id)
            changed_percepts = []
            if ps:
                changed_percepts = ps.tick(
                    stimuli, npc.position, npc.forward,
                    npc.vitals, npc.psychology, current_time)

            # NPC internal tick (vitals, emotions, memory decay...)
            npc.tick(sim_delta, current_time)

            # Need → Goal pipeline
            npc.refresh_need_goals(current_time)

            # Decision — use LLMDecisionSystem if enabled, else UtilityEvaluator
            llm_ds = self._llm_decision_systems.get(npc_id)
            ds = self._decision_systems.get(npc_id)
            active_ds = llm_ds if llm_ds is not None else ds

            if active_ds and ps:
                ctx = ActionContext(
                    npc=npc,
                    percepts=ps.active_percepts,
                    current_time=current_time,
                    delta_time=sim_delta,
                    world=self.world,
                    rng=self.rng,
                    day_length_seconds=self.config.day_length_seconds,
                )
                ctx._action_library = self.action_library
                chosen_action = active_ds.tick(ctx)
                if chosen_action:
                    self._last_actions[npc_id] = chosen_action.action_type
                else:
                    self._last_actions[npc_id] = "Idle"

                # Store LLM-specific fields
                if llm_ds is not None:
                    self._last_reasoning[npc_id] = llm_ds.last_reasoning
                    self._last_dialogue[npc_id] = llm_ds.last_dialogue
                    self._last_emotion[npc_id] = llm_ds.last_emotion

        # 4. Update population stats
        self.population_stats.update(self.world.all_npcs, self.world.get_recent_events(50))

        return self.get_state_snapshot()

    # ── State snapshot ──

    def get_state_snapshot(self) -> dict:
        return {
            "tick": self.tick_count,
            "time": round(self.clock.current_time, 2),
            "day": self.clock.current_day,
            "hour": round(self.clock.current_hour, 1),
            "population": self.population_stats.to_dict(),
            "npcs": [self._npc_snapshot(n) for n in self.world.all_npcs
                     if n.is_active],
            "recent_events": [e.to_dict() for e in self.world.get_recent_events(20)],
        }

    def _npc_snapshot(self, npc: NPC) -> dict:
        nid = npc.identity.npc_id
        d = npc.to_dict()
        d["current_action"] = self._last_actions.get(nid, "Idle")
        d["reasoning"] = self._last_reasoning.get(nid, "")
        d["dialogue"] = self._last_dialogue.get(nid)
        d["emotion"] = self._last_emotion.get(nid)
        d["llm_active"] = nid in self._llm_decision_systems
        return d

    def get_llm_stats_full(self) -> dict:
        """Per-NPC LLM diagnostics for the /api/llm/status endpoint."""
        per_npc = {}
        for nid, ds in self._llm_decision_systems.items():
            per_npc[nid] = {
                "calls": ds.llm_call_count,
                "fallbacks": ds.fallback_count,
                "retries": ds.retry_count,
            }
        queue = self._llm_queue.get_stats() if self._llm_queue else {}
        return {"queue": queue, "per_npc": per_npc}

    def __repr__(self) -> str:
        return (f"[SimulationManager] Tick:{self.tick_count} {self.clock} "
                f"NPCs:{len(self.world.all_npcs)}")
