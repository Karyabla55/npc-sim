# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Per-NPC decision orchestrator: selects and executes the highest-utility action."""

from __future__ import annotations
from npc_sim.decisions.action import IAction
from npc_sim.decisions.action_library import ActionLibrary
from npc_sim.decisions.action_context import ActionContext
from npc_sim.decisions.action_context import ActionContext
from npc_sim.decisions.utility_evaluator import UtilityEvaluator
from npc_sim.decisions.action_lock import ActionLock


class DecisionSystem:
    """Evaluates all registered actions and executes the winner each tick."""

    def __init__(self, library: ActionLibrary, evaluator: UtilityEvaluator = None):
        self._library = library
        self._evaluator = evaluator or UtilityEvaluator()
        self.last_selected_action: IAction | None = None
        self.last_score: float = 0.0

        # Action Lock state
        self._active_lock: ActionLock | None = None
        self._lock_start_sim_time: float = 0.0
        self._lock_elapsed: float = 0.0

    def tick(self, ctx: ActionContext) -> IAction | None:
        vitals = ctx.self_npc.vitals

        # ── Check hard interrupts ──
        # Threat is computed from latest percepts; hunger/thirst directly from vitals
        highest_threat = ctx.get_top_percept("Threat")
        threat_level = highest_threat.threat_level if highest_threat else 0.0
        hard_interrupt = vitals.hunger > 0.85 or vitals.thirst > 0.85 or threat_level >= 0.8

        # Fear spike when NPC first perceives a significant threat
        if highest_threat and threat_level >= 0.8:
            n = ctx.self_npc.psychology.neuroticism
            spike = threat_level * 0.3 * (0.5 + n * 0.5)
            ctx.self_npc.psychology.set_fear(
                min(1.0, ctx.self_npc.psychology.fear + spike)
            )

        if self._active_lock:
            self._lock_elapsed += ctx.delta_time

            if hard_interrupt and self._active_lock.interrupt_allowed:
                self._active_lock = None  # Lock broken by interrupt
            else:
                if self._lock_elapsed < self._active_lock.min_duration_sim_seconds:
                    # Still serving minimum duration
                    locked_action = self._library.get(self._active_lock.action_id)
                    if locked_action:
                        if not locked_action.is_valid(ctx):
                            self._active_lock = None
                        else:
                            # Continue executing the locked action
                            locked_action.execute(ctx)
                            return locked_action
                else:
                    # Min duration elapsed, check arbitrary exit condition
                    if self._active_lock.exit_condition(ctx):
                        self._active_lock = None # Exit condition met, drop lock
                    else:
                        # Lock persists
                        locked_action = self._library.get(self._active_lock.action_id)
                        if locked_action:
                            if not locked_action.is_valid(ctx):
                                self._active_lock = None
                            else:
                                locked_action.execute(ctx)
                                return locked_action

        # Now evaluate normally
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
            
            # Create a new lock for this action if it has lock configuration
            if hasattr(best_action, 'create_lock') and callable(getattr(best_action, 'create_lock')):
                self._active_lock = best_action.create_lock()
                self._lock_elapsed = 0.0
            else:
                self._active_lock = None

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
