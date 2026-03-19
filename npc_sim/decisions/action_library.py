# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Registry of all available actions."""

from __future__ import annotations
from npc_sim.decisions.action import IAction


class ActionLibrary:
    """Registry of all available actions in the simulation."""

    def __init__(self):
        self._actions: list[IAction] = []

    def register(self, action: IAction) -> None:
        if action is not None:
            self._actions.append(action)

    def get_all(self) -> list[IAction]:
        return self._actions

    def __repr__(self) -> str:
        return f"[ActionLibrary] {len(self._actions)} action(s)"
