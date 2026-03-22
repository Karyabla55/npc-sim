# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""SimLogger — comprehensive per-tick CSV logger for NPC-Sim diagnostics.

Writes one row per NPC per tick to logs/sim_full.csv.
When logger_enabled=False in SimulationConfig, all calls are no-ops.
"""

from __future__ import annotations
import csv
import os
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from npc_sim.npc.npc import NPC

# ── CSV column schema ──────────────────────────────────────────────────────────
COLUMNS = [
    "timestamp_real", "tick", "sim_day", "sim_hour",
    "npc_id", "npc_name", "archetype", "occupation", "zone", "pos_x", "pos_z",
    "hp", "hp_max", "hunger", "thirst", "energy", "stress",
    "emotion_happiness", "emotion_fear", "emotion_anger", "mood",
    "inv_food", "inv_water", "inv_medicine", "inv_gold",
    "top_goal", "action_selected", "action_valid",
    "action_target_id", "action_dialogue",
    "percept_count", "top_percept_tag", "top_percept_threat",
    "memory_count", "top_memory_desc",
    "llm_called", "llm_trigger", "llm_latency_ms", "llm_fallback",
    "event_type", "event_detail",
    "is_alive", "death_cause",
]

# Threshold levels logged when crossed (in either direction)
_VITAL_THRESHOLDS = (0.35, 0.65, 0.85)


class SimLogger:
    """
    Thread-safe CSV logger. One instance lives on SimulationManager.
    All log_row() calls are buffered and flushed periodically.
    When enabled=False, every public method is a no-op.
    """

    def __init__(self, log_dir: str = "logs", enabled: bool = True,
                 flush_every: int = 100):
        self.enabled = enabled
        self._flush_every = flush_every
        self._row_count = 0
        self._log_path = ""
        self._writer = None
        self._file = None

        if not enabled:
            return

        os.makedirs(log_dir, exist_ok=True)
        self._log_path = os.path.join(log_dir, "sim_full.csv")
        self._file = open(self._log_path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=COLUMNS,
                                      extrasaction="ignore")
        self._writer.writeheader()
        self._file.flush()

    # ── Public API ──────────────────────────────────────────────────────────────

    def log_npc_tick(
        self,
        tick: int,
        sim_day: int,
        sim_hour: float,
        npc,                        # NPC instance
        percepts: list,             # list[PerceivedObject]
        action_selected: str = "",
        action_valid: bool = True,
        action_target_id: str = "",
        action_dialogue: str = "",
        llm_called: bool = False,
        llm_trigger: str = "",
        llm_latency_ms: float = 0.0,
        llm_fallback: bool = False,
        event_type: str = "",
        event_detail: str = "",
        death_cause: str = "",
        zone: str = "",
    ) -> None:
        if not self.enabled:
            return

        v = npc.vitals
        p = npc.psychology
        inv = npc.inventory
        identity = npc.identity
        pos = npc.position

        # Top percept
        top_percept = max(percepts, key=lambda x: x.salience, default=None) if percepts else None

        # Top memory — use NPCMemory's own API
        top_mem = npc.memory.get_most_salient()
        mem_count = npc.memory._count

        # Top goal
        top_goal = npc.goals.get_top_goal()

        row = {
            "timestamp_real": f"{time.time():.3f}",
            "tick": tick,
            "sim_day": sim_day,
            "sim_hour": f"{sim_hour:.2f}",
            "npc_id": identity.npc_id,
            "npc_name": identity.display_name,
            "archetype": identity.personality_archetype,
            "occupation": identity.occupation,
            "zone": zone,
            "pos_x": f"{pos.x:.2f}",
            "pos_z": f"{pos.z:.2f}",
            # Vitals
            "hp": f"{v.health:.1f}",
            "hp_max": f"{v.max_health:.1f}",
            "hunger": f"{v.hunger:.4f}",
            "thirst": f"{v.thirst:.4f}",
            "energy": f"{v.energy:.2f}",
            "stress": f"{v.stress:.4f}",
            # Emotions
            "emotion_happiness": f"{p.happiness:.4f}",
            "emotion_fear": f"{p.fear:.4f}",
            "emotion_anger": f"{p.anger:.4f}",
            "mood": p.mood_label,
            # Inventory
            "inv_food": inv.get_amount(ItemIds.FOOD),
            "inv_water": inv.get_amount(ItemIds.WATER),
            "inv_medicine": inv.get_amount(ItemIds.MEDICINE),
            "inv_gold": inv.get_amount(ItemIds.GOLD),
            # Goals / action
            "top_goal": top_goal.goal_type if top_goal else "",
            "action_selected": action_selected,
            "action_valid": 1 if action_valid else 0,
            "action_target_id": action_target_id,
            "action_dialogue": action_dialogue,
            # Perception
            "percept_count": len(percepts),
            "top_percept_tag": top_percept.tag if top_percept else "",
            "top_percept_threat": f"{top_percept.threat_level:.2f}" if top_percept else "",
            # Memory
            "memory_count": mem_count,
            "top_memory_desc": (top_mem.event.description[:60] if top_mem and hasattr(top_mem, "event") else ""),
            # LLM
            "llm_called": 1 if llm_called else 0,
            "llm_trigger": llm_trigger,
            "llm_latency_ms": f"{llm_latency_ms:.1f}" if llm_latency_ms else "",
            "llm_fallback": 1 if llm_fallback else 0,
            # Events
            "event_type": event_type,
            "event_detail": event_detail,
            # Alive
            "is_alive": 1 if v.is_alive else 0,
            "death_cause": death_cause,
        }
        self._writer.writerow(row)
        self._row_count += 1
        if self._row_count % self._flush_every == 0:
            self._file.flush()

    def note_vital_threshold(self, npc_id: str, vital: str,
                              value: float, direction: str,
                              threshold: float) -> str:
        """Return a formatted event_detail string for a vital threshold crossing."""
        return f"{vital} crossed {threshold} ({direction}) value={value:.4f}"

    def close(self) -> None:
        if self._file:
            self._file.flush()
            self._file.close()

    @property
    def log_path(self) -> str:
        return self._log_path

    @property
    def row_count(self) -> int:
        return self._row_count


# ── Threshold tracker (per-NPC, lightweight) ──────────────────────────────────

class VitalThresholdTracker:
    """
    Tracks per-NPC vital values across ticks to detect threshold crossings.
    One instance per NPC, created by SimLogger.make_tracker().
    """
    def __init__(self):
        self._prev: dict[str, float] = {}

    def check(self, vital: str, value: float) -> list[tuple[str, float, str]]:
        """Return list of (vital, threshold, direction) for crossings since last call."""
        crossings = []
        prev = self._prev.get(vital, value)
        for thr in _VITAL_THRESHOLDS:
            crossed_up   = (prev < thr <= value)
            crossed_down = (prev > thr >= value)
            if crossed_up:
                crossings.append((vital, thr, "up"))
            elif crossed_down:
                crossings.append((vital, thr, "down"))
        self._prev[vital] = value
        return crossings


# ── Lazy import guard ─────────────────────────────────────────────────────────
try:
    from npc_sim.npc.inventory import ItemIds
except ImportError:
    class ItemIds:  # type: ignore
        FOOD = "food"; WATER = "water"; MEDICINE = "medicine"; GOLD = "gold"
