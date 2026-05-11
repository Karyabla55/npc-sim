# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""NPC psychological profile: Big Five personality + transient emotions."""

from __future__ import annotations


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(val, hi))


class NPCPsychology:
    """
    Big Five personality traits, transient emotional state, and derived mood label.
    Emotional decay is ticked each sim frame so emotions return toward baseline.
    """

    def __init__(
        self,
        extraversion: float = 0.5,
        agreeableness: float = 0.5,
        conscientiousness: float = 0.5,
        neuroticism: float = 0.5,
        openness: float = 0.5,
    ):
        self.extraversion = _clamp(extraversion, 0.0, 1.0)
        self.agreeableness = _clamp(agreeableness, 0.0, 1.0)
        self.conscientiousness = _clamp(conscientiousness, 0.0, 1.0)
        self.neuroticism = _clamp(neuroticism, 0.0, 1.0)
        self.openness = _clamp(openness, 0.0, 1.0)

        # Transient emotions
        self.happiness: float = 0.0
        self.fear: float = 0.0
        self.anger: float = 0.0
        self.mood_label: str = "Calm"
        self._recalculate_mood()

    # ── Emotion setters ──

    # Anger ↔ Happiness cross-inhibition strength. A rise in one emotion dampens
    # the other proportionally to the increase. Tuned in docs/psychology_model.md.
    _CROSS_INHIBITION = 0.5

    def set_happiness(self, value: float) -> None:
        new_val = _clamp(value, -1.0, 1.0)
        delta = new_val - self.happiness
        self.happiness = new_val
        # Positive happiness gains dampen anger (you can't stay furious while elated)
        if delta > 0.0 and self.anger > 0.0:
            self.anger = _clamp(self.anger * (1.0 - delta * self._CROSS_INHIBITION), 0.0, 1.0)
        self._recalculate_mood()

    def set_fear(self, value: float) -> None:
        self.fear = _clamp(value, 0.0, 1.0)
        self._recalculate_mood()

    def set_anger(self, value: float) -> None:
        new_val = _clamp(value, 0.0, 1.0)
        delta = new_val - self.anger
        self.anger = new_val
        # Anger gains dampen positive happiness (rage suppresses joy)
        if delta > 0.0 and self.happiness > 0.0:
            self.happiness = _clamp(self.happiness * (1.0 - delta * self._CROSS_INHIBITION), -1.0, 1.0)
        self._recalculate_mood()

    # ── Emotion increment helpers ──

    def increase_anger(self, delta: float) -> None:
        self.set_anger(self.anger + delta)

    def decrease_anger(self, delta: float) -> None:
        self.set_anger(self.anger - delta)

    def increase_fear(self, delta: float) -> None:
        self.set_fear(self.fear + delta)

    def decrease_fear(self, delta: float) -> None:
        self.set_fear(self.fear - delta)

    def increase_happiness(self, delta: float) -> None:
        self.set_happiness(self.happiness + delta)

    def decrease_happiness(self, delta: float) -> None:
        self.set_happiness(self.happiness - delta)

    # ── Emotion decay ──

    def decay_emotions(
        self,
        delta_time: float,
        fear_rate: float = 0.0005,
        happiness_rate: float = 0.0003,
        anger_rate: float = 0.0004,
    ) -> None:
        # Fear: high-Neuroticism means slow recovery
        fear_decay = delta_time * fear_rate * (1.0 - self.neuroticism * 0.5)
        self.fear = max(0.0, self.fear - fear_decay)

        # Happiness drifts back toward 0 (neutral)
        happy_decay = delta_time * happiness_rate
        if self.happiness > 0.0:
            self.happiness = max(0.0, self.happiness - happy_decay)
        else:
            self.happiness = min(0.0, self.happiness + happy_decay)

        # Anger: high-Agreeableness means faster cooling
        anger_decay = delta_time * anger_rate * (1.0 + self.agreeableness * 0.5)
        self.anger = max(0.0, self.anger - anger_decay)

        self._recalculate_mood()

    # ── Mood derivation ──

    def _recalculate_mood(self) -> None:
        if self.fear > 0.8:
            self.mood_label = "Terrified"
        elif self.anger > 0.6 and self.happiness > 0.6:
            # Edge case: cross-inhibition should make this rare; defensive label.
            self.mood_label = "Conflicted"
        elif self.anger > 0.7:
            self.mood_label = "Furious"
        elif self.fear > 0.5:
            self.mood_label = "Afraid"
        elif self.anger > 0.4:
            self.mood_label = "Irritated"
        elif self.happiness > 0.7:
            self.mood_label = "Euphoric"
        elif self.happiness > 0.3:
            self.mood_label = "Happy"
        elif self.happiness < -0.6:
            self.mood_label = "Depressed"
        elif self.happiness < -0.2:
            self.mood_label = "Sad"
        elif self.neuroticism > 0.7:
            self.mood_label = "Anxious"
        else:
            self.mood_label = "Calm"

    def to_dict(self) -> dict:
        return {
            "extraversion": round(self.extraversion, 3),
            "agreeableness": round(self.agreeableness, 3),
            "conscientiousness": round(self.conscientiousness, 3),
            "neuroticism": round(self.neuroticism, 3),
            "openness": round(self.openness, 3),
            "happiness": round(self.happiness, 3),
            "fear": round(self.fear, 3),
            "anger": round(self.anger, 3),
            "mood_label": self.mood_label,
        }

    def __repr__(self) -> str:
        return (f"[Psychology] Mood:{self.mood_label} | E:{self.extraversion:.2f} "
                f"A:{self.agreeableness:.2f} C:{self.conscientiousness:.2f} "
                f"N:{self.neuroticism:.2f} O:{self.openness:.2f}")
