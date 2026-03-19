# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Flat configuration data for a simulation run."""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class SimulationConfig:
    """
    Flat configuration for a simulation run. Plain Python — no engine dependency.
    Same seed + same config → identical run.
    """

    # ── Identity ──
    seed: int = 42

    # ── Timing ──
    tick_rate: float = 10.0
    day_length_seconds: float = 1440.0
    initial_time_scale: float = 1.0

    # ── World ──
    max_npc_count: int = 500
    spatial_grid_cell_size: float = 50.0

    # ── Physiological decay rates (per sim-second) ──
    hunger_decay_rate: float = 0.001
    thirst_decay_rate: float = 0.002
    energy_decay_rate: float = 0.5

    # ── Psychological decay rates (per sim-second) ──
    fear_decay_rate: float = 0.0005
    happiness_decay_rate: float = 0.0003
    anger_decay_rate: float = 0.0004

    # ── Memory / Belief ──
    global_memory_decay_rate: float = 0.001
    global_belief_decay_rate: float = 0.005

    # ── Social ──
    relation_decay_rate: float = 0.00005

    # ── Perception ──
    percept_timeout: float = 30.0

    # ── Stimulus queue ──
    stimulus_queue_size: int = 1024

    # ── Civilisation / Lifecycle ──
    old_age_threshold: int = 75
    death_by_neglect: bool = True
    max_inventory_slots: int = 10
    wander_radius: float = 30.0

    # ── LLM Integration ──
    llm_enabled: bool = False
    llm_backend: str = "ollama"                     # "ollama" | "mock"
    llm_model: str = "npc-sim-decision:latest"      # custom fine-tuned model name
    llm_tick_every: int = 5                         # call LLM every N ticks
    llm_timeout_seconds: float = 3.0
    llm_max_concurrent: int = 1                     # 1 = serial (Ollama VRAM safe)
    llm_max_queue_size: int = 64
    llm_interrupt_threat_threshold: float = 0.8     # H2: immediate call on high threat
    llm_interrupt_hp_drop: float = 15.0             # H2: immediate call on damage
    ollama_base_url: str = "http://localhost:11434"

    def __repr__(self) -> str:
        return (f"[SimConfig] Seed:{self.seed} TickRate:{self.tick_rate} "
                f"Day:{self.day_length_seconds}s MaxNPC:{self.max_npc_count}")
