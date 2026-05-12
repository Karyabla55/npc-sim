# Psychology & Vitals Model

**Status:** Authoritative reference for the vitals decay and emotion model.
**Applies to:** v1.5.0 and later. v1.4.0 calibrated stress / anger / happiness
balance against the 6-sim-hour diagnostic (`seed=42`, 5 archetypes); v1.5.0
extended the stability story with multiplicative `MemoryEntry.decay()` (A5),
bounded social/belief dicts (A2/A3), and the invariant safety net (A7) — see
`CHANGELOG.md` v1.5.0 entry. The stress / mood numbers in §7 are still the
v1.4.0 6-hour baseline; v1.5.0 30 sim-day strict runs hold them and observe
mean stress drifting further down (≈ 0.10) once memory salience persists.

This document is the single source of truth for how stress, anger, fear and
happiness behave in NPC-Sim. If you change a coefficient here, also update the
relevant test in `run_diagnostic.py` and bump the comparison row in the
[`docs/bugs_and_issues.md`](bugs_and_issues.md) regression-results section.

---

## 1. Vitals decay (per `NPC.tick(delta_time, current_time)`)

Implemented in `npc_sim/npc/npc.py`. Default rates come from `SimulationConfig`
(see `npc_sim/core/sim_config.py`); the values below are the runtime defaults.

| Vital  | Formula (per tick)                                       | Default rate | Source            |
|--------|----------------------------------------------------------|--------------|-------------------|
| hunger | `hunger += hunger_rate * delta_time`                     | 0.001        | `hunger_decay_rate` |
| thirst | `thirst += thirst_rate * delta_time`                     | 0.0015       | `thirst_decay_rate` |
| energy | `energy -= energy_rate * delta_time`                     | 0.073        | `energy_decay_rate` |
| stress | `stress += need_stress − baseline_recovery`              | see §2       | computed each tick  |
| health | mutated only by `apply_damage` / `heal`                  | n/a          | actions/events      |

Death-by-neglect: when `hunger ≥ 1.0` or `thirst ≥ 1.0`, `apply_damage(1.0 * dt)`
ticks every frame (≈100 sim-seconds to kill at maxed need). Gate: `cfg.death_by_neglect`.

---

## 2. Stress balance

Stress is the most fragile vital because it has **many sources, few sinks**, and
small per-tick deltas accumulate over thousands of ticks. v1.4.0 rebalanced it.

### Sources (raise stress)

| Source | Formula | Notes |
|--------|---------|-------|
| Need pressure (in `NPC.tick`) | `(hunger + thirst) * 0.01 * delta_time` | Climbs as basic needs go unmet |
| Negative events (in `witness_event`) | `−impact * 0.1 * neuroticism` *if impact<0* | Only negative impact events feed stress (v1.4.0 fix #27) |
| Fleeing (`FleeAction.execute`) | `+0.05 * delta_time` per locked tick | Scaled in v1.4.0 (was flat `+0.05`) |
| Attacking (`AttackAction.execute`) | `+0.12 * delta_time` per locked tick | Scaled in v1.4.0 (was flat `+0.12`) |

### Sinks (lower stress)

| Sink | Formula | Notes |
|------|---------|-------|
| Baseline organic recovery (in `NPC.tick`) | `−0.004 * delta_time * (1 − neuroticism * 0.5)` | Always-on, scaled by 1-N (high-N NPCs recover slower) |
| Sleeping (`SleepAction.execute`) | `−0.02 * delta_time` | |
| Praying (`PrayAction.execute`) | `−0.1 * delta_time` | |
| Socialising (`SocializeAction.execute`) | `−0.08 * delta_time` | Scaled in v1.4.0 |
| Eating (`EatAction.execute`) | `−0.03 * delta_time` | Added in v1.4.0 |
| Drinking (`DrinkAction.execute`) | `−0.02 * delta_time` | Added in v1.4.0 |
| Healing (`HealAction.execute`) | `−0.04 * delta_time` | Added in v1.4.0 |

### Stress → Anger spillover

`NPC.tick`:
```
anger += stress * 0.02 * delta_time * neuroticism
```
High-stress, high-neuroticism NPCs convert ambient stress into irritability.
There is no anger → stress spillover; the relationship is one-way.

---

## 3. Emotion model

Three transient emotions live in `NPCPsychology`:

| Emotion   | Range          | Notes |
|-----------|----------------|-------|
| happiness | `[-1.0, +1.0]` | Negative half represents sadness/depression |
| anger     | `[ 0.0, +1.0]` | One-sided axis (no "calm" negative anger) |
| fear      | `[ 0.0, +1.0]` | Independent of anger/happiness |

### 3.1 Anger ↔ Happiness cross-inhibition (v1.4.0+)

A change to one emotion proportionally dampens the other when *both would be
positive simultaneously*. This is enforced inside the setters:

```python
_CROSS_INHIBITION = 0.5  # tuned via diagnostic regression

def set_anger(value):
    new = clamp(value, 0, 1)
    delta = new - anger
    anger = new
    if delta > 0 and happiness > 0:
        happiness = clamp(happiness * (1 - delta * _CROSS_INHIBITION), -1, 1)

# symmetric for set_happiness
```

A jump from `anger = 0.0 → 0.8` shrinks a happiness of `+0.9` to
`+0.9 * (1 − 0.8*0.5) = +0.54`. Empirically: with this rule, 0 out of 18 000
diagnostic rows satisfy `anger ≥ 0.7 AND happiness ≥ 0.7`.

Fear is on a separate axis and is not subject to cross-inhibition.

### 3.2 Emotion decay (in `NPC.tick`)

```
fear   *= (1 − delta_time * fear_rate   * (1 − neuroticism * 0.5))   # high-N → slow recovery
anger  *= (1 − delta_time * anger_rate  * (1 + agreeableness * 0.5)) # high-A → fast cooling
happy  drifts toward 0 at delta_time * happiness_rate
```

Default rates: `fear_rate = 0.0005`, `happiness_rate = 0.0003`,
`anger_rate = 0.0004`. Defined in `SimulationConfig`.

---

## 4. Mood label

The categorical mood label is derived from emotion values in
`NPCPsychology._recalculate_mood()`. Priority chain (first match wins):

| Condition                                     | Label       |
|-----------------------------------------------|-------------|
| `fear > 0.8`                                  | Terrified   |
| `anger > 0.6 AND happiness > 0.6`             | Conflicted  *(v1.4.0+ defensive case)* |
| `anger > 0.7`                                 | Furious     |
| `fear > 0.5`                                  | Afraid      |
| `anger > 0.4`                                 | Irritated   |
| `happiness > 0.7`                             | Euphoric    |
| `happiness > 0.3`                             | Happy       |
| `happiness < -0.6`                            | Depressed   |
| `happiness < -0.2`                            | Sad         |
| `neuroticism > 0.7` (with calm vitals)        | Anxious     |
| else                                          | Calm        |

`Conflicted` should be rare because cross-inhibition prevents both anger and
happiness from being high at the same time. If you observe many `Conflicted`
rows in a run, either cross-inhibition is being bypassed (direct attribute
assignment instead of setter calls) or the inhibition factor needs raising.

---

## 5. Trait modifiers

`NPCPsychology` holds the Big Five scalars (`extraversion`, `agreeableness`,
`conscientiousness`, `neuroticism`, `openness`). The current model uses them
explicitly in:

- **Neuroticism** scales fear spike from witnessed negative events, scales
  stress pump from negative events, scales `stress → anger` spillover,
  *attenuates* baseline stress recovery.
- **Agreeableness** speeds anger decay.
- **Extraversion** scales the happiness gain from `SocializeAction.execute()`.

Named traits (`Brave`, `Coward`, `Pacifist`, `Aggressive`, `Devout`, `Greedy`, …)
live on `NPCTraits` and are consumed by individual actions, not by
`NPCPsychology`. See `docs/integration_map.md` for the full trait → action map.

**LLM trait coherence guard (H5).** v1.5.0+ extended the post-inference
override in `LLMDecisionSystem._enforce_trait_coherence()` to five named
traits: Brave (low fear + high threat → `attack`), Pacifist (never attack),
Coward (threat ≥ 0.5 → `flee`), Greedy (gold-in-inventory + valid `trade` →
`trade`), Devout (stress ≥ 0.6 + valid `pray` → `pray`). Each override
appends an audit suffix to the LLM's reasoning string for diagnostics.

**Memory decay (v1.5.0+).** `MemoryEntry.decay()` is multiplicative
(`weight *= 1 - rate`), not additive — exponential approach to zero with
sign preserved, so even decades-old salient events remain meaningfully
larger than mundane ones. `get_most_salient()` keeps returning a sensible
peak even after 100k decay ticks.

---

## 6. Determinism

`NPCPsychology` and `NPCVitals` are deterministic — they contain no randomness
of their own. All stochastic effects originate in actions, perception, or
events and flow through `SimRng`. Same seed + same config → identical emotion
trajectory.

---

## 7. Regression baseline

Reproducible diagnostic (`python run_diagnostic.py --hours 6.0 --seed 42`):

| Metric                          | v1.3.x | v1.4.0 |
|---------------------------------|--------|--------|
| Mean stress                     | 0.745  | 0.532  |
| Stress > 0.9 (% of rows)        | 57.7 % | 31.3 % |
| Mean anger                      | 0.431  | 0.237  |
| Rows with anger≥0.7 AND hap≥0.7 | (latent contradiction) | **0** |
| Mood "Calm" share               | 53 %   | 75 %   |

Any change to the coefficients in this document should be validated against
this baseline. Regression-result tables for older versions live in
[`docs/bugs_and_issues.md`](bugs_and_issues.md).
