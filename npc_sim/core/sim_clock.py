# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Deterministic simulation clock."""

from __future__ import annotations


class SimulationClock:
    """
    Deterministic simulation clock.
    The ONLY source of time in the simulation — no datetime, no system clock.
    Advances via explicit tick() calls driven by the SimulationManager.
    """

    def __init__(self, day_length_seconds: float = 1440.0, time_scale: float = 1.0):
        self.day_length_seconds = max(1.0, day_length_seconds)
        self.time_scale = max(0.0, time_scale)
        self.total_elapsed: float = 0.0
        self.initial_offset: float = 0.0
        self._paused = False

    def set_initial_hour(self, hour: float) -> None:
        """Sets the starting offset without treating it as elapsed simulation time."""
        self.initial_offset = (hour / 24.0) * self.day_length_seconds

    @property
    def current_time(self) -> float:
        """Total effective time for scheduling components."""
        return self.initial_offset + self.total_elapsed

    @property
    def current_hour(self) -> float:
        """Current in-game hour in [0, 24)."""
        return (self.current_time % self.day_length_seconds) / self.day_length_seconds * 24.0

    @property
    def current_day(self) -> int:
        """How many full in-game days have elapsed conceptually from the start."""
        return int(self.current_time / self.day_length_seconds)

    # ── Control ──

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def set_time_scale(self, scale: float) -> None:
        self.time_scale = max(0.0, scale)

    # ── Tick ──

    def tick(self, real_delta_time: float) -> float:
        """
        Advances the simulation clock by real_delta_time × time_scale.
        Returns the actual sim-delta applied.
        """
        if self._paused or real_delta_time <= 0.0:
            return 0.0
        sim_delta = real_delta_time * self.time_scale
        self.total_elapsed += sim_delta
        return sim_delta

    def __repr__(self) -> str:
        paused = " PAUSED" if self._paused else ""
        return (f"[SimClock] t={self.current_time:.2f}s Day={self.current_day} "
                f"Hour={self.current_hour:.1f} Scale={self.time_scale}x{paused}")
