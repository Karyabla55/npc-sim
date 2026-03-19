# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Fluent factory for creating pre-configured NPC archetypes."""

from __future__ import annotations
from npc_sim.core.sim_rng import SimRng
from npc_sim.npc.npc import NPC
from npc_sim.npc.identity import NPCIdentity
from npc_sim.npc.vitals import NPCVitals
from npc_sim.npc.psychology import NPCPsychology
from npc_sim.npc.social import NPCSocial
from npc_sim.npc.traits import NPCTraits


class NPCFactory:
    """Fluent factory for creating pre-configured NPCs. Fully deterministic via SimRng."""

    @staticmethod
    def create(
        display_name: str, age: int, rng: SimRng,
        gender: str = "Unknown", occupation: str = "Civilian",
        faction: str = "None", personality_archetype: str = "Generic",
        max_health: float = 100.0, max_energy: float = 100.0,
        memory_capacity: int = 50,
    ) -> NPC:
        identity = NPCIdentity(
            rng.next_id("npc"), display_name, age,
            gender, occupation, faction, personality_archetype)
        return NPC(identity, NPCVitals(max_health, max_energy),
                   NPCPsychology(), NPCSocial(), memory_capacity)

    @staticmethod
    def create_guard(rng: SimRng, name: str = None, faction: str = "City Watch") -> NPC:
        name = name or "Guard"
        identity = NPCIdentity(
            rng.next_id("npc"), name, age=rng.next_int(22, 45),
            gender="Male", occupation="Guard", faction=faction,
            personality_archetype="Guardian")
        vitals = NPCVitals(max_health=120.0, max_energy=110.0)
        psych = NPCPsychology(
            extraversion=rng.next_float(0.3, 0.5),
            agreeableness=rng.next_float(0.3, 0.6),
            conscientiousness=rng.next_float(0.7, 1.0),
            neuroticism=rng.next_float(0.1, 0.4),
            openness=rng.next_float(0.1, 0.4))
        traits = NPCTraits(NPCTraits.BRAVE, NPCTraits.CAUTIOUS)
        return NPC(identity, vitals, psych, NPCSocial(), memory_capacity=60, traits=traits)

    @staticmethod
    def create_merchant(rng: SimRng, name: str = None, faction: str = "Merchant Guild") -> NPC:
        name = name or "Merchant"
        identity = NPCIdentity(
            rng.next_id("npc"), name, age=rng.next_int(25, 60),
            gender="Unknown", occupation="Merchant", faction=faction,
            personality_archetype="Merchant")
        psych = NPCPsychology(
            extraversion=rng.next_float(0.6, 0.9),
            agreeableness=rng.next_float(0.5, 0.8),
            conscientiousness=rng.next_float(0.4, 0.7),
            neuroticism=rng.next_float(0.2, 0.5),
            openness=rng.next_float(0.5, 0.8))
        traits = NPCTraits(NPCTraits.GREEDY, NPCTraits.CURIOUS)
        return NPC(identity, NPCVitals(), psych, NPCSocial(), memory_capacity=70, traits=traits)

    @staticmethod
    def create_civilian(rng: SimRng, name: str = None, faction: str = "None") -> NPC:
        name = name or "Civilian"
        identity = NPCIdentity(
            rng.next_id("npc"), name, age=rng.next_int(18, 70),
            gender="Unknown", occupation="Civilian", faction=faction,
            personality_archetype="Generic")
        psych = NPCPsychology(
            extraversion=rng.next_float(0.3, 0.7),
            agreeableness=rng.next_float(0.4, 0.8),
            conscientiousness=rng.next_float(0.3, 0.7),
            neuroticism=rng.next_float(0.3, 0.7),
            openness=rng.next_float(0.3, 0.6))
        traits = NPCTraits(NPCTraits.CAUTIOUS)
        return NPC(identity, NPCVitals(), psych, NPCSocial(), traits=traits)

    @staticmethod
    def create_scholar(rng: SimRng, name: str = None, faction: str = "Academy") -> NPC:
        name = name or "Scholar"
        identity = NPCIdentity(
            rng.next_id("npc"), name, age=rng.next_int(28, 65),
            gender="Unknown", occupation="Scholar", faction=faction,
            personality_archetype="Scholar")
        psych = NPCPsychology(
            extraversion=rng.next_float(0.2, 0.5),
            agreeableness=rng.next_float(0.5, 0.8),
            conscientiousness=rng.next_float(0.7, 1.0),
            neuroticism=rng.next_float(0.2, 0.5),
            openness=rng.next_float(0.8, 1.0))
        vitals = NPCVitals(max_health=80.0, max_energy=90.0)
        traits = NPCTraits(NPCTraits.CURIOUS, NPCTraits.PACIFIST)
        return NPC(identity, vitals, psych, NPCSocial(), memory_capacity=100, traits=traits)

    @staticmethod
    def create_farmer(rng: SimRng, name: str = None, faction: str = "Farmers Guild") -> NPC:
        name = name or "Farmer"
        identity = NPCIdentity(
            rng.next_id("npc"), name, age=rng.next_int(18, 60),
            gender="Unknown", occupation="Farmer", faction=faction,
            personality_archetype="Farmer")
        psych = NPCPsychology(
            extraversion=rng.next_float(0.3, 0.6),
            agreeableness=rng.next_float(0.5, 0.8),
            conscientiousness=rng.next_float(0.5, 0.8),
            neuroticism=rng.next_float(0.2, 0.5),
            openness=rng.next_float(0.4, 0.7))
        traits = NPCTraits(NPCTraits.CAUTIOUS)
        return NPC(identity, NPCVitals(90.0, 120.0), psych, NPCSocial(), memory_capacity=50, traits=traits)

    @staticmethod
    def create_priest(rng: SimRng, name: str = None, faction: str = "Temple") -> NPC:
        name = name or "Priest"
        identity = NPCIdentity(
            rng.next_id("npc"), name, age=rng.next_int(30, 70),
            gender="Unknown", occupation="Priest", faction=faction,
            personality_archetype="Priest")
        psych = NPCPsychology(
            extraversion=rng.next_float(0.4, 0.7),
            agreeableness=rng.next_float(0.7, 1.0),
            conscientiousness=rng.next_float(0.6, 0.9),
            neuroticism=rng.next_float(0.1, 0.4),
            openness=rng.next_float(0.6, 1.0))
        traits = NPCTraits("Devout", NPCTraits.PACIFIST)
        return NPC(identity, NPCVitals(85.0, 90.0), psych, NPCSocial(), memory_capacity=70, traits=traits)
