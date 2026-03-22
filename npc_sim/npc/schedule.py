# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""NPC daily schedule with occupation-based presets."""

from __future__ import annotations
import math


class NPCSchedule:
    """
    Defines an NPC's preferred daily activity schedule.
    Used by time-aware actions to boost relevance during appropriate hours.
    """

    def __init__(
        self,
        work_start: float = 8.0,
        work_end: float = 18.0,
        sleep_start: float = 22.0,
        wake_hour: float = 7.0,
        social_hour: float = 19.0,
    ):
        self.work_start_hour = work_start
        self.work_end_hour = work_end
        self.sleep_start_hour = sleep_start
        self.wake_hour = wake_hour
        self.social_hour = social_hour

    @staticmethod
    def for_occupation(occupation: str) -> NPCSchedule:
        occ = (occupation or "").lower()
        presets = {
            "guard":    NPCSchedule(6, 14, 21, 5, 16),
            "merchant": NPCSchedule(9, 19, 23, 8, 20),
            "scholar":  NPCSchedule(8, 20, 24, 7, 18),
            "farmer":   NPCSchedule(5, 17, 20, 4, 18),
            "priest":   NPCSchedule(7, 13, 21, 5, 14),
            "civilian": NPCSchedule(9, 17, 22, 7, 19),
        }
        return presets.get(occ, NPCSchedule())

    def preference_at(self, activity: str, hour: float) -> float:
        act = activity.lower()
        if act == "work":
            return 1.0 if self._is_in_window(hour, self.work_start_hour, self.work_end_hour) else 0.1
        elif act == "sleep":
            if self._is_in_window(hour, self.sleep_start_hour, self.wake_hour + 24.0):
                return 1.0
            if self._is_in_window(hour, self.wake_hour, self.work_start_hour):
                return 0.3
            return 0.0
        elif act == "social":
            return max(0.0, 1.0 - abs(hour - self.social_hour) / 3.0)
        return 0.5

    @staticmethod
    def _is_in_window(hour: float, start: float, end: float) -> bool:
        if end > 24.0:
            return hour >= start or hour < end - 24.0
        return start <= hour < end

    def get_suggested_activity(self, hour: float) -> str:
        """Return the expected activity label for this hour (soft suggestion for LLM)."""
        if self._is_in_window(hour, self.sleep_start_hour, self.wake_hour + 24.0):
            return "sleep"
        if self._is_in_window(hour, self.work_start_hour, self.work_end_hour):
            return "work"
        if abs(hour - self.social_hour) <= 1.5:
            return "social"
        return "idle"

    def to_dict(self) -> dict:
        return {
            "work_start": self.work_start_hour,
            "work_end": self.work_end_hour,
            "sleep_start": self.sleep_start_hour,
            "wake_hour": self.wake_hour,
            "social_hour": self.social_hour,
        }

    def __repr__(self) -> str:
        return (f"[Schedule] Work:{self.work_start_hour:.0f}-{self.work_end_hour:.0f}h "
                f"Sleep:{self.sleep_start_hour:.0f}h Wake:{self.wake_hour:.0f}h")
