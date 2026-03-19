# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Abstract base class for NPC actions in the utility AI system."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from npc_sim.decisions.action_context import ActionContext


class IAction(ABC):
    """
    Contract for all NPC actions. Every action is stateless —
    all context arrives via ActionContext.
    """

    @property
    @abstractmethod
    def action_id(self) -> str:
        ...

    @property
    @abstractmethod
    def action_type(self) -> str:
        ...

    @abstractmethod
    def is_valid(self, ctx: ActionContext) -> bool:
        ...

    @abstractmethod
    def evaluate(self, ctx: ActionContext) -> float:
        """Returns a normalised utility score [0, 1]. Must NOT have side-effects."""
        ...

    @abstractmethod
    def execute(self, ctx: ActionContext) -> None:
        """Commits the action: mutates NPC state and/or publishes a SimEvent."""
        ...
