# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Per-NPC decision orchestrator: selects and executes the highest-utility action."""

from __future__ import annotations
from npc_sim.decisions.action import IAction
from npc_sim.decisions.action_library import ActionLibrary
from npc_sim.decisions.action_context import ActionContext
from npc_sim.decisions.utility_evaluator import UtilityEvaluator


class DecisionSystem:
    """Evaluates all registered actions and executes the winner each tick."""

    def __init__(self, library: ActionLibrary, evaluator: UtilityEvaluator = None):
        self._library = library
        self._evaluator = evaluator or UtilityEvaluator()
        self.last_selected_action: IAction | None = None
        self.last_score: float = 0.0

    def tick(self, ctx: ActionContext) -> IAction | None:
        best_action = None
        best_score = 0.0

        for action in self._library.get_all():
            score = self._evaluator.evaluate(action, ctx)
            if score > best_score:
                best_score = score
                best_action = action

        if best_action is not None:
            best_action.execute(ctx)
            self.last_selected_action = best_action
            self.last_score = best_score

        return best_action

    def get_scores(self, ctx: ActionContext) -> list[tuple[IAction, float]]:
        result = []
        for action in self._library.get_all():
            score = self._evaluator.evaluate(action, ctx) if action.is_valid(ctx) else 0.0
            result.append((action, score))
        result.sort(key=lambda x: x[1], reverse=True)
        return result

    def __repr__(self) -> str:
        last = self.last_selected_action.action_type if self.last_selected_action else "None"
        return f"[DecisionSystem] Last: {last} ({self.last_score:.2f})"
