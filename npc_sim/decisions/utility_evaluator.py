# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Utility evaluator with response curves and trait modifiers."""

from __future__ import annotations
import math
from abc import ABC, abstractmethod
from npc_sim.decisions.action import IAction
from npc_sim.decisions.action_context import ActionContext


class ICurve(ABC):
    @abstractmethod
    def evaluate(self, x: float) -> float: ...


class LinearCurve(ICurve):
    def evaluate(self, x: float) -> float:
        return max(0.0, min(x, 1.0))


class QuadraticCurve(ICurve):
    def evaluate(self, x: float) -> float:
        return max(0.0, min(x * x, 1.0))


class InverseQuadraticCurve(ICurve):
    def evaluate(self, x: float) -> float:
        v = 1.0 - x
        return max(0.0, min(1.0 - v * v, 1.0))


class SigmoidCurve(ICurve):
    def __init__(self, steepness: float = 10.0, midpoint: float = 0.5):
        self._steepness = steepness
        self._midpoint = midpoint

    def evaluate(self, x: float) -> float:
        val = 1.0 / (1.0 + math.exp(-self._steepness * (x - self._midpoint)))
        return max(0.0, min(val, 1.0))


class UtilityEvaluator:
    """
    Normalised utility evaluator. Applies response curves and trait modifiers.
    """

    def __init__(self):
        self.default_curve: ICurve = LinearCurve()

    def evaluate(self, action: IAction, ctx: ActionContext,
                 curve: ICurve = None) -> float:
        if not action.is_valid(ctx):
            return 0.0

        raw = max(0.0, min(action.evaluate(ctx), 1.0))
        shaped = (curve or self.default_curve).evaluate(raw)
        modifier = ctx.self_npc.traits.get_weight_modifier(action.action_type)
        return max(0.0, min(shaped * modifier, 1.0))
