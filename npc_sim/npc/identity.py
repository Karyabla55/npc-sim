# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""NPC identity: name, age, occupation, faction, personality archetype."""

from __future__ import annotations


class NPCIdentity:
    """Persistent identity data for an NPC."""

    def __init__(
        self,
        npc_id: str,
        display_name: str,
        age: int,
        gender: str = "Unknown",
        occupation: str = "Civilian",
        faction: str = "None",
        personality_archetype: str = "Generic",
    ):
        self.npc_id = npc_id
        self.display_name = display_name
        self.age = max(0, age)
        self.gender = gender
        self.occupation = occupation
        self.faction = faction
        self.personality_archetype = personality_archetype

    def to_dict(self) -> dict:
        return {
            "npc_id": self.npc_id,
            "display_name": self.display_name,
            "age": self.age,
            "gender": self.gender,
            "occupation": self.occupation,
            "faction": self.faction,
            "personality_archetype": self.personality_archetype,
        }

    def __repr__(self) -> str:
        return (f"[Identity] {self.display_name} (ID:{self.npc_id}) | Age:{self.age} | "
                f"{self.gender} | {self.occupation} @ {self.faction}")
