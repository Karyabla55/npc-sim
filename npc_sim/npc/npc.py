# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Primary NPC data container aggregating all subsystems."""

from __future__ import annotations
import math
from npc_sim.core.sim_vector3 import SimVector3
from npc_sim.core.sim_config import SimulationConfig
from npc_sim.events.sim_event import SimEvent
from npc_sim.npc.identity import NPCIdentity
from npc_sim.npc.vitals import NPCVitals
from npc_sim.npc.psychology import NPCPsychology
from npc_sim.npc.social import NPCSocial
from npc_sim.npc.memory import NPCMemory
from npc_sim.npc.beliefs import BeliefSystem
from npc_sim.npc.goals import NPCGoals, Goal, GoalType
from npc_sim.npc.traits import NPCTraits
from npc_sim.npc.inventory import NPCInventory
from npc_sim.npc.schedule import NPCSchedule


class NPC:
    """
    The primary NPC data container.
    Aggregates Vitals, Identity, Psychology, Social, Belief, Memory, Goals, Traits, Inventory.
    All logic lives in Systems — this class is pure data + minimal wiring.
    """

    def __init__(
        self,
        identity: NPCIdentity,
        vitals: NPCVitals = None,
        psychology: NPCPsychology = None,
        social: NPCSocial = None,
        memory_capacity: int = 50,
        traits: NPCTraits = None,
        inventory_slots: int = 10,
    ):
        if identity is None:
            raise ValueError("identity is required")

        self.identity = identity
        self.vitals = vitals or NPCVitals()
        self.psychology = psychology or NPCPsychology()
        self.social = social or NPCSocial()
        self.beliefs = BeliefSystem()
        self.memory = NPCMemory(memory_capacity)
        self.goals = NPCGoals()
        self.traits = traits or NPCTraits()
        self.inventory = NPCInventory(inventory_slots)
        self.schedule = NPCSchedule.for_occupation(identity.occupation)

        # World state
        self.position = SimVector3.ZERO
        self.forward = SimVector3(0, 0, 1)
        self.is_active = True

        # Config reference (injected by SimulationManager)
        self._config: SimulationConfig | None = None

    def inject_config(self, config: SimulationConfig) -> None:
        self._config = config

    def set_schedule(self, schedule: NPCSchedule) -> None:
        if schedule is not None:
            self.schedule = schedule

    # ── Tick ──

    def tick(self, delta_time: float, current_time: float) -> None:
        if not self.is_active or not self.vitals.is_alive:
            return

        cfg = self._config
        hunger_rate = cfg.hunger_decay_rate if cfg else 0.001
        thirst_rate = cfg.thirst_decay_rate if cfg else 0.002
        energy_rate = cfg.energy_decay_rate if cfg else 0.5
        mem_decay = cfg.global_memory_decay_rate if cfg else 0.001
        belief_decay = cfg.global_belief_decay_rate if cfg else 0.005
        rel_decay = cfg.relation_decay_rate if cfg else 0.00005
        fear_rate = cfg.fear_decay_rate if cfg else 0.0005
        happy_rate = cfg.happiness_decay_rate if cfg else 0.0003
        anger_rate = cfg.anger_decay_rate if cfg else 0.0004

        # Physiology
        self.vitals.set_hunger(self.vitals.hunger + hunger_rate * delta_time)
        self.vitals.set_thirst(self.vitals.thirst + thirst_rate * delta_time)
        self.vitals.consume_energy(energy_rate * delta_time)

        # Death by neglect
        if cfg and cfg.death_by_neglect:
            if self.vitals.hunger >= 1.0 or self.vitals.thirst >= 1.0:
                self.vitals.apply_damage(10.0 * delta_time)

        # Cross-component: Stress → Anger (Neuroticism-scaled)
        stress_anger = self.vitals.stress * 0.02 * delta_time * self.psychology.neuroticism
        self.psychology.set_anger(self.psychology.anger + stress_anger)

        # Hunger/Thirst → Stress
        need_stress = (self.vitals.hunger + self.vitals.thirst) * 0.01 * delta_time
        self.vitals.set_stress(self.vitals.stress + need_stress)

        # Emotional decay
        self.psychology.decay_emotions(delta_time, fear_rate, happy_rate, anger_rate)

        # Relation decay
        self.social.tick_decay(delta_time, rel_decay)

        # Memory and belief decay
        self.memory.decay_all(mem_decay * delta_time)
        self.beliefs.decay_all(belief_decay * delta_time)

        # Prune expired goals
        self.goals.prune_expired(current_time)

    # ── Event witnessing ──

    def witness_event(self, sim_event: SimEvent, belief_subjects: list[str], current_time: float) -> None:
        if sim_event is None:
            return

        # Record in episodic memory
        emotional_weight = sim_event.impact * (1.0 - self.psychology.neuroticism * 0.5)
        self.memory.remember(sim_event, emotional_weight, current_time)

        # Update beliefs about each subject
        self.beliefs.process_event(sim_event, belief_subjects, current_time)

        # Emotional reaction
        stress_delta = abs(sim_event.impact) * 0.1 * self.psychology.neuroticism
        self.vitals.set_stress(self.vitals.stress + stress_delta)

        if sim_event.impact < -0.3:
            fear_spike = abs(sim_event.impact) * 0.15 * self.psychology.neuroticism
            self.psychology.set_fear(self.psychology.fear + fear_spike)
        elif sim_event.impact > 0.2:
            happy_boost = sim_event.impact * 0.1 * (1.0 - self.psychology.neuroticism * 0.5)
            self.psychology.set_happiness(self.psychology.happiness + happy_boost)

    # ── Social interaction ──

    def interact(self, other: NPC, trust_delta: float, affinity_delta: float,
                 respect_delta: float, current_time: float) -> None:
        if other is None:
            return
        relation = self.social.get_or_create_relation(self.identity.npc_id, other.identity.npc_id)
        relation.apply_interaction(trust_delta, affinity_delta, respect_delta, current_time)

    # ── Need → Goal pipeline ──

    def refresh_need_goals(self, current_time: float, urgency_window: float = 300.0) -> None:
        expiry = current_time + urgency_window

        if self.vitals.hunger > 0.65 and not self.goals.has_active_goal(GoalType.FIND_FOOD):
            self.goals.add_goal(Goal(GoalType.FIND_FOOD, "I need to eat", self.vitals.hunger, expiry))

        if self.vitals.thirst > 0.70 and not self.goals.has_active_goal(GoalType.FIND_WATER):
            self.goals.add_goal(Goal(GoalType.FIND_WATER, "I need water", self.vitals.thirst, expiry))

        if self.vitals.energy < 0.30 * self.vitals.max_energy and not self.goals.has_active_goal(GoalType.REST):
            self.goals.add_goal(Goal(GoalType.REST, "I need rest", 1.0 - self.vitals.energy_norm, expiry))

    # ── Lifecycle ──

    def deactivate(self) -> None:
        self.is_active = False

    def to_dict(self) -> dict:
        return {
            "identity": self.identity.to_dict(),
            "vitals": self.vitals.to_dict(),
            "psychology": self.psychology.to_dict(),
            "social": self.social.to_dict(),
            "inventory": self.inventory.to_dict(),
            "traits": self.traits.to_dict(),
            "position": {"x": round(self.position.x, 2), "y": round(self.position.y, 2), "z": round(self.position.z, 2)},
            "is_active": self.is_active,
            "schedule": self.schedule.to_dict(),
        }

    def __repr__(self) -> str:
        state = "Active" if self.is_active else "Inactive"
        return f"[NPC] {self.identity.display_name} ({state}) | {self.vitals} | {self.psychology}"
