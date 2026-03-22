# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""A predefined world map of distinctive zones mappings."""

from npc_sim.core.sim_vector3 import SimVector3

class WorldMap:
    # Coords mapped across a 100x100 grid.
    ZONES: dict[str, SimVector3] = {
        "Town Square": SimVector3(50.0, 0.0, 50.0),
        "Farm": SimVector3(20.0, 0.0, 80.0),
        "Barracks": SimVector3(80.0, 0.0, 80.0),
        "Academy": SimVector3(80.0, 0.0, 20.0),
        "Temple": SimVector3(20.0, 0.0, 20.0),
        "Market": SimVector3(50.0, 0.0, 40.0),
        "Tavern": SimVector3(60.0, 0.0, 60.0),
        "Riverside": SimVector3(10.0, 0.0, 50.0),
        "Forest Edge": SimVector3(50.0, 0.0, 90.0),
        "Cemetery": SimVector3(90.0, 0.0, 50.0),
    }

    @classmethod
    def get_zone(cls, name: str) -> SimVector3:
        return cls.ZONES.get(name, cls.ZONES["Town Square"])
    
    @classmethod
    def get_home_for_occupation(cls, occupation: str) -> SimVector3:
        occ = occupation.lower()
        if occ == "farmer":
            return cls.ZONES["Farm"]
        if occ == "guard":
            return cls.ZONES["Barracks"]
        if occ == "scholar":
            return cls.ZONES["Academy"]
        if occ == "priest":
            return cls.ZONES["Temple"]
        if occ == "merchant":
            return cls.ZONES["Market"]
        return cls.ZONES["Tavern"]  # Civilian / default
