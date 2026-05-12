# Changelog

All notable changes to **NPC-Sim** are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

---

## [1.5.0] — 2026-05-12 (long-run stability + integration + polish)

Risk-first triage of the long-run stability audit (Phase A: A1–A7), then
integration gap closure (Phase B: B1–B4), then the 5 pending tracker bugs
(Phase C: C1–C5 / #15-#18, #20). Three 30 sim-day milestones, every fix
covered by an invariant test, every commit gated by a 6h `--strict`
diagnostic.

**Phase A & B & C milestones — 30 sim-day strict diagnostic, seed=42, 5
archetypes:**

| Metric                       | v1.4.0 (6h) | v1.5.0 (30d) |
|------------------------------|-------------|--------------|
| Ticks                        | 3,600       | 432,001      |
| Real time                    | 0.8 s       | 109 s        |
| Survivors                    | 5/5         | 5/5          |
| Invariant violations         | n/a         | 0            |
| Mean stress                  | 0.532       | ≈0.10        |
| Inventory growth bounded     | no          | yes (cap=100)|
| Belief/relation dict bounded | no          | yes (cap=200)|
| CSV rotation                 | no          | every 1M rows|
| pytest suite                 | none        | 68 cases     |


### Polish (tracker)

- **C5 / #16 — Doc sync: DualLLM marked as planned, not implemented**
  (`docs/architecture.md`, `docs/llm_data_spec.md`): both docs read as if
  the dual-model Reasoner/Formatter pipeline already existed; CLAUDE.md
  was the only place that warned readers it does not. Added a callout at
  the top of each doc's relevant section pointing to roadmap task G9 in
  `docs/nextsteps.md` and explicitly noting that
  `npc_sim/llm/llm_backend.py` ships only `OllamaBackend` and
  `MockBackend`. This closes the spec/code mismatch described in tracker
  #16. Doc-only change; no code touched.

- **C4 / #18 — Interrupt preempts in-flight LLM requests**
  (`npc_sim/llm/llm_request_queue.py`): the priority heap correctly
  ordered _pending_ work, but once a normal/background request was
  pulled into the worker thread, an arriving interrupt had to wait for
  it to finish — defeating H2's purpose of "react fast." Threads can't
  be killed cross-thread safely, but their callbacks can: `LLMRequest`
  now carries a `_cancelled` flag, the queue tracks `_in_flight`
  workers, and `submit()` of an `INTERRUPT`-priority request marks any
  currently-running lower-priority request as cancelled. `_execute()`
  short-circuits the callback to `(None, None)` so the NPC won't apply
  a stale response on the interrupt path; the HTTP call itself still
  completes and the worker is then free to pull the interrupt off the
  heap. New `preempted` stat counts these events. Covered by
  `tests/test_queue_preemption.py` (3 cases).

- **C3 / #17 — Removed unused `llm_tick_every` config**
  (`npc_sim/core/sim_config.py`, `npc_sim/llm/llm_decision_system.py`,
  `npc_sim/simulation/simulation_manager.py`, `README.md`,
  `test_llm_smoke.py`): the field was set but never read — LLM cadence is
  driven entirely by H2 interrupts. Its presence misled readers into
  expecting periodic LLM calls. Dropped from `SimulationConfig`, from
  the `LLMDecisionSystem.__init__` signature, from the constructor call
  in `SimulationManager._ensure_llm_subsystems`, and from documentation.
  Covered by `tests/test_config_no_llm_tick.py` (2 cases) which
  guards against re-introduction.

- **C2 / #20 — Trait coherence expanded to Coward / Greedy / Devout**
  (`npc_sim/llm/llm_decision_system.py`): `_enforce_trait_coherence` (H5)
  only covered Brave (resist flee under low-fear high-threat) and Pacifist
  (never attack). Added three more named-trait overrides for the LLM brain:
  Coward + percept threat ≥ 0.5 → `flee`; Greedy + gold-in-inventory + valid
  `trade` available → `trade`; Devout + stress ≥ 0.6 + valid `pray`
  available → `pray`. Each override carries an audit suffix in the reasoning
  field for diagnostics. Covered by `tests/test_trait_coherence.py` (7
  cases): trigger paths + the negative invariants (no override below
  threshold, no override when target action invalid, no override without
  prerequisite resource).

- **C1 / #15 — Work efficiency now reaches the yield**
  (`npc_sim/decisions/actions/builtin.py`): `WorkAction.execute()` computed
  `efficiency = max(0.05, energy_norm)` and used it only as the probability
  gate for whether the tick produced anything. The same `efficiency` was
  logged in the event description, suggesting it scaled the output — but
  every successful tick produced exactly `+1` regardless of energy. Now
  `yield_amount = max(1, int(efficiency * 2))`: well-rested NPCs produce
  `+2` per successful tick, depleted ones still get the `+1` floor.
  Inventory cap (A1) still applies. Covered by `tests/test_work_efficiency.py`
  (5 cases).

### Integration

- **B4 — Faction disposition reaches Utility AI**
  (`npc_sim/decisions/action_context.py`,
  `npc_sim/decisions/actions/builtin.py`,
  `npc_sim/simulation/simulation_manager.py`):
  `FactionRegistry.get_disposition` was used by the LLM-facing serializer
  but invisible to the every-tick Utility AI. Added
  `ActionContext.faction_disposition(target_id)` which resolves both NPCs'
  faction labels and looks up the registry — returning 0 when either side
  has no faction, the two share a faction, the target is unresolvable, or
  the registry isn't attached. SimulationManager injects the registry onto
  the per-tick ctx the same way it already injects `_action_library`.
  AttackAction adds up to `+0.30` against enemy factions / `−0.30` against
  allied; SocializeAction adds up to `+0.20 × disp` for allies and
  `+0.40 × disp` (i.e. up to `−0.40`) for enemies. Covered by
  `tests/test_faction_disposition.py` (5 cases).

- **B3 — Reputation now reaches Utility AI** (`npc_sim/decisions/actions/builtin.py`):
  `NPCSocial.reputation` was written by AttackAction but never read by the
  decision layer. Wired it into two actions:
  `SocializeAction.evaluate()` adds `0.20 × (target.reputation − 0.5)`
  (well-regarded NPCs attract conversation; pariahs repel it); `TradeAction.
  evaluate()` subtracts `0.30` when `target.reputation < 0.3` (refuse trades
  with the disreputable). Score still clamps to [0, 1]. Covered by
  `tests/test_reputation_reads.py` (3 cases).

- **B2 — WorkAction reads workplace-safety belief**
  (`npc_sim/decisions/actions/builtin.py`, `npc_sim/simulation/world_map.py`):
  `WorkAction.evaluate()` ignored the NPC's beliefs about its own workplace,
  so a Farmer would still go to the field after a bandit raid. Added
  `WorldMap.get_home_zone_name(occupation)` and a single
  `OCCUPATION_HOME_ZONE` table that `get_home_for_occupation` now reuses
  instead of duplicating the mapping. `WorkAction.evaluate()` consults
  `ctx.belief_score(home_zone)`: negative beliefs drop the score by up to
  −0.25 so the NPC stays away from places it remembers as dangerous.
  Positive beliefs do not inflate score (work is already preferred during
  scheduled hours; this is purely a safety guard). Covered by
  `tests/test_work_beliefs.py` (5 cases).

- **B1 — TradeAction reads target belief valence**
  (`npc_sim/decisions/actions/builtin.py`): trade scoring previously ignored
  what the NPC knew about the potential partner. `evaluate()` now consults
  `ctx.belief_score(target_id)`: negative beliefs drop the score by up to
  −0.30 (deterring trades with known cheaters), positive beliefs raise it
  by up to +0.15 (favoring trusted partners). Successful trades emit a
  positive (`impact=+0.25`) `Trade` event that both NPCs witness with each
  other as the belief subject, so trust compounds over repeated successful
  trades. Covered by `tests/test_trade_beliefs.py` (4 cases).

### Fixed

- **A1 — Inventory unbounded growth** (`npc_sim/npc/inventory.py`):
  `NPCInventory.add()` had no per-stack cap; `WorkAction` produced GRAIN/GOLD/
  TOOLS every tick, so a single NPC's gold stack would grow without bound over
  long runs (315M+ ticks/year). Added `stack_cap=100` parameter; existing-stack
  additions are clamped, initial amounts are clamped, and the method returns
  `False` when the stack is full so the producer falls through to another
  action. 6h diagnostic (seed=42, 5 archetypes) confirms gold saturating at
  exactly 100 instead of growing linearly. Covered by
  `tests/test_inventory_cap.py` (5 cases).

- **A7 — Invariant assertion framework** (`npc_sim/diagnostics/invariants.py`,
  `run_diagnostic.py`): no automated safety net existed for catching long-run
  drift (NaN vitals, runaway inventory, dict cap violation). New
  `check_invariants(sim_manager)` walks every NPC and returns a list of
  `InvariantViolation`s covering: vital finiteness/range
  (hp ∈ [0, max_hp], energy ∈ [0, max_energy], hunger/thirst/stress ∈ [0,1]),
  emotion finiteness/range, inventory ≤ A1 cap, beliefs ≤ A2 cap, relations
  ≤ A3 cap, memory count ≤ ring capacity. `run_diagnostic.py` gained
  `--strict` (check every `--strict-every=1000` ticks; exit code 2 on
  violation). The framework caught a real bug while being wired up — initial
  invariant code wrongly assumed `energy ∈ [0,1]` instead of `[0, max_energy]`,
  fixed before merge. Covered by `tests/test_invariants.py` (8 cases).

- **A6 — Unbounded CSV log growth** (`npc_sim/diagnostics/sim_logger.py`):
  `sim_full.csv` was opened once and appended forever — at 10 NPCs × 1 tick/s
  that's ~315M rows/year, gigabytes of disk and slow append. Added
  `rotate_every_rows=1_000_000` (default) to `SimLogger.__init__`: when the
  row counter crosses the threshold, the active file is closed and renamed
  to `sim_full.NNNN.csv` (sequential suffix), and a fresh `sim_full.csv` is
  opened with a new header. The notebook's "Re-run Cell 2" workflow keeps
  working since the active log path is unchanged. Covered by
  `tests/test_logger_rotation.py` (4 cases).

- **A5 — Memory emotional_weight collapsed to zero** (`npc_sim/npc/memory.py`):
  `MemoryEntry.decay()` used additive subtraction: every tick subtracted
  `rate` from `|weight|`, clamping to zero. After ~200 ticks at the default
  rate, every memory's weight was exactly `0.0` and `get_most_salient()`
  couldn't distinguish a once-traumatic event from a mundane one. Switched
  to multiplicative decay (`weight *= 1 - rate`) — magnitudes shrink
  exponentially toward zero but preserve relative ordering forever. Verified:
  100k decay ticks remain finite, in-range, and sign-preserving.
  Covered by `tests/test_memory_decay.py` (5 cases).

- **A4 — FactionRegistry stale dispositions** (`npc_sim/simulation/faction_registry.py`):
  `tick_decay()` cleanup threshold was `1e-6`. Floating-point rounding
  during multiplicative decay would freeze values slightly above that, so
  faded dispositions were retained indefinitely. Raised the threshold to
  `0.01` (now exposed as `_CLEANUP_THRESHOLD` class constant), matching
  the practical "no longer matters" floor used elsewhere. Old dispositions
  fully clear after ~2000 sim-seconds of decay. Covered by
  `tests/test_faction_cleanup.py` (4 cases).

- **A3 — NPCSocial.Relation dict unbounded growth** (`npc_sim/npc/social.py`):
  `NPCSocial._relations` grew without eviction. Every novel NPC encounter
  created a new `Relation` even when it stayed near zero forever; over years
  the dict would hold thousands of effectively-dead relationships. Added
  the same shape as A2: `max_relations=200` LRU cap + `prune_threshold=0.05`
  applied to `max(|trust|, |affinity|, |respect|)`. `tick_decay()` prunes
  faded relations; `get_or_create_relation()` evicts the lowest-magnitude
  (oldest tie-break) entry when at cap. Covered by
  `tests/test_relation_eviction.py` (4 cases).

- **A2 — BeliefSystem dict unbounded growth** (`npc_sim/npc/beliefs.py`):
  `BeliefSystem._nodes` grew indefinitely; gossip propagation in
  `SocializeAction` created new nodes on every interaction. Over years
  of simulation, RAM would balloon and iteration would slow. Added
  `max_nodes=200` LRU cap and `prune_threshold=0.05` confidence floor:
  `decay_all()` now removes nodes whose confidence falls below the
  threshold; `get_or_create()` evicts the lowest-confidence node (tie-break:
  oldest `last_updated`) when the cap is reached. Covered by
  `tests/test_belief_eviction.py` (4 cases).

---

## [1.4.0] – 2026-05-11

Psychology stability pass + Memory/Beliefs/Goals integration with the Utility AI
(roadmap tasks G1–G6 from `docs/nextsteps.md`). Diagnostic comparison (6 sim-hours,
`seed=42`, 5 archetypes):

| Metric                          | v1.3.x | v1.4.0 |
|---------------------------------|--------|--------|
| Mean stress                     | 0.745  | 0.532  |
| Stress > 0.9 (% of rows)        | 57.7 % | 31.3 % |
| Mean anger                      | 0.431  | 0.237  |
| Rows with anger≥0.7 AND hap≥0.7 | (latent) | **0** |
| Mood "Calm" share               | 53 %   | 75 %   |

### Fixed

- **Bug #27 — Monotonic stress accumulation** (`npc_sim/decisions/actions/builtin.py`,
  `npc_sim/npc/npc.py`):
  - `FleeAction.execute()` and `AttackAction.execute()` were adding flat `+0.05` /
    `+0.12` to stress every tick of the action lock (`builtin.py:204, 369`). With
    `delta_time = 0.1` and an 8–10 sim-second lock, stress climbed by ~1.0 per
    encounter. Scaled both deltas by `ctx.delta_time` so the lock contributes a
    realistic amount.
  - `NPC.witness_event()` used `abs(impact)` for the stress nudge — so positive
    events (Eat, Work, Trade…) also raised stress while raising happiness. Now
    only `impact < 0.0` events feed stress.
  - `NPC.tick()` had no baseline stress recovery; idle NPCs accumulated stress
    indefinitely from need-stress. Added a low-rate `baseline_recovery` term
    scaled inversely with neuroticism.
  - `SocializeAction.execute()` stress relief also wasn't `delta_time` scaled —
    a long socialize lock could crater stress in one chain. Now scaled.
  - `EatAction`, `DrinkAction`, `HealAction` now reduce stress proportional to
    `delta_time` so meeting basic needs feels recoverable.

- **Bug #28 — Anger and Happiness could both reach 1.0 simultaneously**
  (`npc_sim/npc/psychology.py`): `set_anger()` and `set_happiness()` were fully
  independent; the mood label's if-elif chain hid the conflict but the state was
  internally contradictory. Implemented cross-inhibition: a positive delta to
  one emotion proportionally dampens the other (factor `_CROSS_INHIBITION = 0.5`).
  Added a defensive `"Conflicted"` mood label for edge cases where both still
  cross 0.6 (cross-inhibition makes this rare).

### Added

- **`ActionContext.belief_score(subject)`** (`npc_sim/decisions/action_context.py`):
  Returns `valence × confidence` in `[-1, +1]` for a subject (NPC id, zone, topic).
  Used by `WalkToAction` and `AttackAction` to bias scoring with the BeliefSystem.
- **`ActionContext.goal_bonus(goal_type, amount=0.25)`**: Additive score bonus for
  actions whose related goal is active. Threaded through Eat, Drink, Sleep, Heal,
  Socialize, Trade, Work, Pray, Gather, Flee.
- **`WalkToAction` memory + belief bias** (G2): The target zone is now exposed as
  `(zone_name, position)` and `_zone_bias()` combines `get_memory_threat_bias()`
  and `belief_score()` for the target zone. Negative bias discounts the walk score
  (NPC avoids places it associates with harm); positive bias boosts it. Survival
  walks (hunger/thirst > 0.65) get a smaller modulation than exploratory walks.
- **`AttackAction` belief valence** (G3): Negative belief about the target
  (`belief_score ≤ -0.3`) adds `+0.25` to the attack score; positive belief
  (`≥ 0.3`) applies `-0.40`. Pacifist/Brave/anger logic preserved.
- **`SocializeAction` dialogue + gossip** (G4 + G5): LLM-authored dialogue is
  carried to the target via `NPC.pending_dialogue` and recorded as a `Dialogue`
  episodic memory on the listener. The speaker's highest-confidence belief is
  propagated to the listener with attenuated valence/confidence (gossip retelling
  fidelity), gated by relationship trust (`trust ≥ 0.3`).
- **`NPC.pending_dialogue`** (`npc_sim/npc/npc.py`): Buffer for LLM-authored lines,
  set in `LLMDecisionSystem._apply_pending()` and consumed by `SocializeAction`.

### Changed

- Mood label algorithm now exposes a `"Conflicted"` state for `anger > 0.6 AND
  happiness > 0.6` (`npc_sim/npc/psychology.py`).
- Version: `1.3.0` → `1.4.0` in `pyproject.toml` and `npc_sim/__init__.py`.

### Documentation

- **New: `docs/psychology_model.md`** — Formal documentation of vitals decay,
  stress balance, emotion model with cross-inhibition, mood label algorithm,
  and trait modifiers.
- **New: `docs/integration_map.md`** — Data-source → consumer matrix showing
  which actions read which subsystems (Memory, Beliefs, Goals, Social, Traits),
  pre-v1.4.0 vs post-v1.4.0 wiring, and remaining gaps.
- `docs/bugs_and_issues.md`: Added #27 (stress accumulation), #28 (anger/happiness
  independence), #29 (Memory/Beliefs/Goals integration gap — partial fix).
- `docs/nextsteps.md`: G1–G6 marked completed; G7, G8 moved to v1.5.
- `CLAUDE.md`: "What Exists vs What's Integrated" section updated to reflect
  partial integration.

### Known Limitations

- Diagnostic NPCs still bias heavily toward `Work` and don't trigger
  `Eat`/`Drink`/`Socialize` within a 6-hour run; the stress-relief / happiness
  pathways those actions provide are present but rarely exercised in current
  diagnostic configuration. Tracked as part of action-selection tuning, separate
  from this release.

---

## [1.3.0] – 2026-05-02

### Fixed

- **Bug #21 — Action lock broken by `is_valid()` during `min_duration`** (`npc_sim/decisions/decision_system.py`):
  Removed `is_valid()` check from the `min_duration` window. Lock is now truly unbreakable
  during minimum duration — only `hard_interrupt` can break it. This eliminates the Scholar
  Sleep↔Work oscillation (~57 cycles/sim-day → proper 8-hour shifts).

- **Bug #22 — `WorkAction` energy drain 30× too high** (`npc_sim/decisions/actions/builtin.py`):
  Changed `consume_energy(5.0 * ctx.delta_time)` → `consume_energy(0.167 * ctx.delta_time)`.
  Drains ~80 energy (100→20 threshold) over 480 sim-seconds = one 8-hour sim-day work shift.

- **Bug #23 — `SleepAction` restore rate 75× too fast + `min_duration` 2.5× sim-days** (`npc_sim/decisions/actions/builtin.py`):
  (a) Restore rate `0.15 → 0.002`: full energy recovery now takes ~480 sim-seconds instead of 6.7 sim-seconds.
  (b) `min_duration` `3600.0 → 480.0` sim-seconds: sleep lock now covers one 8-sim-hour shift
  in a 1440-second sim-day (was 2.5 sim-days).

- **Bug #13 — Action lock created after `execute()`** (`npc_sim/decisions/decision_system.py`):
  Lock is now created before `execute()` runs. First tick of every multi-tick action is
  immediately covered by the lock, preventing single-tick interruption on action start.

- **Bug #11 — `_valid_actions()` fragile fallback** (`npc_sim/llm/npc_serializer.py`):
  Removed the non-functional `ctx.world._get_action_library_if_set()` primary path.
  Method now directly uses `ctx._action_library`, which is always set by `SimulationManager`.

### Documentation

- `docs/bugs_and_issues.md`: Marked bugs #1, #2, #3, #6, #7, #10 as FIXED in v1.2.0
  (they were fixed but not documented in the previous release).

---

## [1.2.0] – 2026-05-02

### Fixed

- **Bug #4 — `WalkToAction.evaluate()` variable shadowing** (`npc_sim/decisions/actions/builtin.py`):
  Renamed inner `target` to `market_pos`, added explicit `is not None` guard before
  `SimVector3.distance()`. Eliminates potential `AttributeError` when Market zone is not registered.

- **Bug #5 — `LLMRequestQueue.shutdown()` silent** (`npc_sim/llm/llm_request_queue.py`):
  Added `notify_all()` on the `Condition` inside `shutdown()` so the dispatcher thread wakes
  immediately rather than waiting up to 100ms for the condition timeout.

- **Bug #8 — Death by neglect rate too high** (`npc_sim/npc/npc.py`):
  Reduced `apply_damage(10.0 * delta_time)` → `apply_damage(1.0 * delta_time)`. NPCs now
  survive ~100 seconds of maxed-out hunger/thirst, giving recovery behaviors (Eat, Drink,
  Gather) time to fire.

- **Bug #9 — Trait modifier applied after curve shaping** (`npc_sim/decisions/utility_evaluator.py`):
  Trait modifier is now applied to the raw score before the response curve shapes it.
  Functionally equivalent for the default `LinearCurve`; semantically correct for non-linear
  curves (`QuadraticCurve`, `SigmoidCurve`).

- **Bug #12 — `GatherAction.execute()` uncapped** (`npc_sim/decisions/actions/builtin.py`):
  Added per-resource cap enforcement (≤ 5 items) inside `execute()`, matching the cap in
  `is_valid()`. Correctly falls back to gathering the other resource when one is full.

- **Bug #14 — EOS token stripping fragile** (`npc_sim/llm/llm_backend.py`):
  Replaced sequential `str.find()` loop with a single `re.sub()` regex pass covering all EOS
  artifacts (`<|eot_id|>`, `<|end_of_text|>`, `<|eot`, `espo*`) atomically.

- **Bug #19 — `FleeAction` lock duration = 0.0** (`npc_sim/decisions/actions/builtin.py`):
  Changed `min_duration_sim_seconds` from `0.0` to `8.0`. NPCs now commit to fleeing for at
  least 8 sim-seconds, preventing oscillation. Exit condition (threat disappears) still
  provides early termination.

- **`LLMDecisionSystem._focused` class variable** (`npc_sim/llm/llm_decision_system.py`):
  Moved `self._focused = False` initialization to `__init__()` and removed the class-level
  attribute. Each `LLMDecisionSystem` instance now has independent focus state.

### Added

- **`NPCPsychology` increment helpers** (`npc_sim/npc/psychology.py`):
  Added `increase_anger()`, `decrease_anger()`, `increase_fear()`, `decrease_fear()`,
  `increase_happiness()`, `decrease_happiness()`. Delegates to existing clamped setters;
  provides a consistent increment API matching `NPCVitals`.

- **`/api/llm/status` REST endpoint** (`server.py`):
  Returns `get_llm_stats_full()` dict with per-NPC LLM call/fallback/retry counts.

- **`/api/npc/<npc_id>` REST endpoint** (`server.py`):
  Returns the full snapshot for a single NPC by ID. 404 if NPC not found or no simulation running.

- **`llm_enable_all` / `llm_disable_all` SocketIO events** (`server.py`):
  Allows web clients to hot-swap all NPCs to/from LLM decision-making in a single message.

- **`run_diagnostic.py` — three additional pass/fail checks**:
  SleepAction present in distribution, at least one NPC has an active goal (`top_goal` not
  empty), multiple mood labels observed (psychology is not static). Total checks: 5 → 8.

### Changed

- Version: `1.0.3` → `1.2.0` in `pyproject.toml` and `npc_sim/__init__.py`.

---

## [1.1.0] – 2026-04-20

### Removed
- **`OllamaBackend` Monolithic Processing**: Migrated architectural focus away from single-model JSON generation due to reasoning vs. valid-schema conflicts.

### Added
- **Asymmetric Dual-LLM Pipeline (`architecture.md` v2.0)**: Introduced a two-stage sequential workflow (Component A: 3B Reasoner for logic, Component B: 1B Formatter for schema).
- **`Stateful_NPC/newgen-rpg.ipynb`**: Complete 34-cell Dual-Phase SFTTrainer notebook. Phase A trains 3B Reasoner on Chain-of-Thought, Phase B trains 1B Formatter on schema conversion. Evaluates individually.
- **`Stateful_NPC/generator/npc_sim_generator_v2.py` (v4 Dataset Generator)**: 
  - `generate_cot_reasoning()`: Generates 3-5 sentence Turkish first-person internal monologues.
  - New Deviation Cases (D5-D8): Logic coverage for dual-crises, conflicted courage, schedule overrides, and trauma-driven fleeing.
  - `generate_formatter_dataset()`: Derives the JSON conversion dataset automatically.
  - `_paraphrase()`: Replaces synonyms randomly directly in the generated dataset for the formatter for robustness.

### Changed
- Moved `llm_data_spec.md` to `docs/llm_data_spec.md`.
- Updated dataset schemas to explicitly support dual-dataset logic (Reasoner 10k + 2k, Formatter ~12k).

---

## [1.0.3] – 2026-03-26

### Fixed

- **`llm/llm_backend.py` — `OllamaBackend.call()`**: Added `stop` tokens (`<|eot_id|>`, `<|end_of_text|>`, `<|eot`) to the Ollama request body to prevent corrupt EOS artifacts (`espoň` / `espon`) from appearing in model output.
- **`llm/llm_backend.py` — `OllamaBackend._parse()`**: Added pre-parse sanitisation that strips any EOS token artifacts (`<|eot_id|>`, `espo`, etc.) from model output before calling `json.loads()`.
- **`llm/llm_backend.py` — `ILLMBackend.SYSTEM_PROMPT`**: Replaced Turkish prompt with English version that includes a strict **decision priority ladder** (interrupt + trait → attack/flee, hunger/thirst/HP rules) and explicit **trait behaviour rules** (Brave→no-flee, Fearful→flee, Devout→pray, Greedy→trade). Reduces Brave-NPC hallucination from dataset imbalance.
- **`llm/llm_decision_system.py` — `_enforce_trait_coherence()`**: New post-inference guard (H5) — overrides `flee` → `attack` when NPC has `Brave` trait, `fear < 0.4`, and `threat_level ≥ 0.7`; overrides `attack` → `flee` when NPC has `Pacifist` trait. Applied in `_apply_pending()` before action lookup.
- **`llm/llm_decision_system.py` — `_check_interrupt()`**: Added fear spike on high-threat interrupt — `fear += threat_level × 0.3 × (0.5 + neuroticism × 0.5)` — so the NPC's emotional state reacts visibly when the LLM brain activates.
- **`decisions/decision_system.py` — `tick()`**: Added identical fear spike for the pure utility-AI path so both paths produce consistent emotional reactions to threats.
- **`decisions/actions/builtin.py` — `AttackAction.is_valid()`**: Extended eligibility: `Brave` trait alone now qualifies an NPC for self-defence (no longer requires `Aggressive` or `anger > 0.65`); any NPC with `health < max_health × 0.85` can retaliate.
- **`decisions/actions/builtin.py` — `AttackAction.evaluate()`**: Brave NPCs gain `brave_boost = threat_level × 0.4` added to the raw score, ensuring `attack` beats `flee` after Brave modifier is applied.
- **`decisions/actions/builtin.py` — `AttackAction.execute()`**: Reversed anger direction — anger now rises (`+0.05`) while a threat is present and only decays (`-0.15`) post-combat. Stress change raised from `+0.1` to `+0.12`.
- **`decisions/actions/builtin.py` — `FleeAction.evaluate()`**: Added trait-aware suppressors — Brave NPCs with `fear < 0.5` multiply base score by `0.4`; Coward NPCs multiply by `1.5`. Incorporates `get_memory_threat_bias()` from `ActionContext` for experience-sensitive flee decisions (Bug 2.7).
- **`decisions/actions/builtin.py` — `FleeAction.execute()`**: Added emotion side-effects — `fear += 0.15`, `stress += 0.05` each time the NPC flees; NPCs now become visibly scared when fleeing.
- **`decisions/actions/builtin.py` — `SocializeAction.execute()`**: Added happiness gain `+0.05 × (0.5 + extraversion)` and stress reduction `-0.08` per socialise action.
- **`decisions/actions/builtin.py` — `WorkAction.is_valid()`**: Raised energy floor from `0.05` to `0.20`; additionally returns `False` when `hunger > 0.80` or `thirst > 0.80` so survival needs block work.
- **`decisions/actions/builtin.py` — `WorkAction.evaluate()`**: Added `energy_factor = (energy - 0.20) / 0.80` multiplier — work score fades toward 0 as energy approaches the 0.20 floor, letting `SleepAction` win naturally.
- **`decisions/actions/builtin.py` — `PrayAction.evaluate()`**: Steepened stress-driven curve to `max(0, (stress - 0.3) / 0.7) × 0.6`; Devout bonus raised from `0.3` to `0.4`. Non-Devout NPCs now choose prayer when highly stressed.
- **`decisions/actions/builtin.py` — `WalkToAction.evaluate()`**: When NPC is hungry and the Market is more than `2.0` away, score is `hunger × 0.92` (was `× 0.85`), ensuring `WalkToAction` beats `GatherAction` until the NPC reaches the resource zone.
- **`decisions/action_context.py` — `get_memory_threat_bias()`**: New helper returns `[-1, +1]` average emotional weight of all episodic memories related to a given entity ID. Negative bias → NPC was hurt before → flee score rises. Used by `FleeAction.evaluate()`.
- **`Stateful_NPC/generator/npc_sim_generator_v2.py` — `generate_dataset()`**: Oversamples `Brave` arch + `threat ≥ 0.7` examples by 3×, correcting the `35% × 20% = 7%` occurrence rate that caused the model to underfit the brave-guard-attacks-threat decision rule.

### Changed

- **`llm/llm_decision_system.py`**: Updated module docstring to document H5 (trait coherence guard) alongside H1–H4.

---

## [1.0.2] – 2026-03-22

### Added
- **Simulation Control Panel** — `server.py` now launches a configuration screen before starting. `initial_sim_hour`, `npc_move_speed`, and `npc_count` are now fully configurable.
- **Action Duration Locks** — `ActionLock` enforced minimum durations for decisions, preventing logic oscillation. NPCs now commit to actions until exit conditions or hard interrupts occur.
- **Time-of-Day Awareness** — Sleep and Work actions are strictly tied to a day/night schedule curve configured per occupation in `NPCSchedule`.
- **Targeted Movement System** — `WalkToAction` now correctly guides NPCs to specific named coordinates defined in `WorldMap` (e.g. Market, Riverside) instead of wandering aimlessly.
- **UI Redesign** — Transformed the dashboard canvas into a fully functional map drawing distinct zones and NPC paths. Inject interactive event coloration and expose deep diagnostic fields natively.

---

## [1.0.1] – 2026-03-22

### Added

- **`npc_sim/diagnostics/sim_logger.py`** — `SimLogger`: per-tick CSV logger writing all NPC state to `logs/sim_full.csv` (one row per NPC per tick, 44 columns); enabled/disabled via `SimulationConfig.logger_enabled`; `VitalThresholdTracker` for detecting hunger/thirst/energy crossings at 0.35/0.65/0.85
- **`npc_sim/diagnostics/__init__.py`** — diagnostics package
- **`run_diagnostic.py`** — headless 6-hour simulation runner; spawns 5 archetypes with fixed starting inventory, runs 21,600 sim-seconds, then prints pass/fail summary (survivors, deaths, action distribution, Eat/Drink coverage, LLM stats)
- **`SimulationConfig.logger_enabled`** — boolean field (`default=True`); when `False`, `SimLogger` is a no-op with zero overhead
- **`NPCGoals.remove_by_type(goal_type)`** — removes all goals of a given type; used by stale-goal pruning

### Fixed

- **`builtin.py` — EatAction** (`npc_sim/decisions/actions/builtin.py`): replaced flat quadratic score (`hunger²`) with urgency-scaled score `min(1.0, hunger² × (1 + (hunger-0.35)×3))` so Eat beats Work (0.6–0.9) at hunger ≥ 0.65
- **`builtin.py` — DrinkAction**: same urgency-scaled curve as EatAction; Drink now beats Work at thirst ≥ 0.65
- **`builtin.py` — GatherAction.is_valid()**: added inventory cap (`< 5 items`) preventing infinite accumulation; inventory was growing from 2 → 40,000+ items in 6 h
- **`builtin.py` — GatherAction.evaluate()**: scores near-zero (`urgency × 0.08`) when both food and water are stocked so Eat/Drink win; scores high (`urgency × 0.85`) when inventory is completely empty so Gather beats WalkTo wandering
- **`builtin.py` — WalkToAction.evaluate()**: now goal-urgency aware; scores high only when a Food/Water percept exists to move toward, capped at 0.5 for random-wander case so Gather (0.85) wins over purposeless wandering
- **`builtin.py` — SleepAction.is_valid()**: threshold tightened from `energy_norm < 0.4` to `< 0.35`; returns `False` when `hunger > 0.75` or `thirst > 0.75` (survival beats sleep)
- **`npc/npc.py` — refresh_need_goals()**: stale goals pruned before new ones added; `FindFood` removed when `hunger < 0.30`, `FindWater` removed when `thirst < 0.30`, `Rest` removed when `energy_norm > 0.50`; eliminates 10+ tick goal lag observed in CSV
- **Decay rate dt investigation**: confirmed `sim_delta` (= `real_delta × time_scale`) is correctly propagated from `SimulationClock.tick()` through `SimulationManager.tick()` to `NPC.tick()` — no dt bug present

---

## [1.0.0] – 2026-03-19

**Complete platform migration: Unity/C# → standalone Python + Web + LLM**

### Added — Python Simulation Core

- **`npc_sim/core/`** — `SimVector3`, `SimRng`, `SimulationClock`, `SimulationConfig`
- **`npc_sim/events/`** — `SimEvent`, `Stimulus`, `StimulusType`
- **`npc_sim/npc/`** — `NPC`, `NPCFactory`, `NPCIdentity`, `NPCVitals`, `NPCPsychology`, `NPCSocial`, `NPCMemory`, `BeliefSystem`, `NPCGoals`, `NPCTraits`, `NPCInventory`, `NPCSchedule`
- **`npc_sim/perception/`** — `PerceptionSystem`, `SensorRange`, `PerceptionFilter`, `PerceivedObject`
- **`npc_sim/decisions/`** — `IAction` ABC, `DecisionSystem`, `UtilityEvaluator`, `ActionLibrary`, `ActionContext`
- **11 built-in actions** — `eat`, `sleep`, `flee`, `gather`, `heal`, `attack`, `socialize`, `trade`, `work`, `pray`, `walk_to`
- **`npc_sim/simulation/`** — `SimulationManager`, `SimWorldAdapter`, `StimulusDispatcher`, `FactionRegistry`, `PopulationStats`, `DictionaryGrid`

### Added — Web Dashboard

- **`server.py`** — Flask + Flask-SocketIO backend; simulation runs in background thread; WebSocket real-time push
- **`static/index.html`** — Premium dark-mode single-page dashboard
- **`static/style.css`** — Glassmorphism design, Inter font, micro-animations
- **`static/app.js`** — Canvas 2D NPC map, real-time panels, event log, controls

### Added — LLM Integration (`npc_sim/llm/`)

- **`world_registry.py`** — H1: coordinate → semantic zone label (AABB lookup)
- **`npc_serializer.py`** — Minified JSON payload builder (token-optimised, zone-labelled)
- **`llm_backend.py`** — `ILLMBackend` ABC, `OllamaBackend` (local Ollama API), `MockBackend`
- **`llm_request_queue.py`** — H3: priority heap queue; `max_concurrent=1` for serial Ollama inference
- **`llm_decision_system.py`** — H2 interrupt + H4 guided retry + `UtilityEvaluator` fallback
- **`SimulationConfig`** extended with 10 LLM fields (`llm_enabled`, `llm_model`, `llm_tick_every`, …)
- **`SimulationManager`** extended with `enable_llm_for()`, `enable_llm_for_all()`, `get_llm_stats_full()`

### Added — Training Dataset v2 (`Stateful_NPC/`)

- **`generator/npc_sim_generator_v2.py`** — Upgraded dataset generator  
  Full NPC-Sim state: Big Five, 11 actions, semantic zones, percepts, episodic memories, beliefs, interrupt flags
- **`data/train_v2.jsonl`** — 20,000 training examples (Llama-3 instruct format, ~14 MB)
- **`data/test_v2.jsonl`** — 2,000 test examples (~4 MB)

### Added — Project Config

- **`pyproject.toml`** — `setuptools` build config; dependencies: `flask`, `flask-socketio`, `simple-websocket`
- **`LICENSE`** — Apache License 2.0, Copyright 2025-2026 Sadık Abdusselam Albayrak

### Removed — Unity Artifacts

- `package.json` (Unity package manifest)
- `Runtime.meta`, `CHANGELOG.md.meta` (Unity meta files)
- `Editor/SimulationBootstrap.cs` (Unity Editor bootstrap script)

### Breaking Changes

- **Platform**: This version no longer targets Unity. All C# code removed. Python 3.10+ required.
- **Package name**: `com.forgeproject.sim` → `npc_sim`

---

## [0.4.1] – 2026-03-05 *(C# Unity — final patch before platform migration)*

- CS0592 fix: `[Header]` moved off nested class in `WorldRegistry.cs`
- CS0200 fix: Added `NPC.SetSchedule()` public method for cross-assembly access
- CS0618 fix: `FindObjectOfType<T>()` → `FindFirstObjectByType<T>()` (Unity 2022.2+)

## [0.4.0] – 2026-03-05 *(C# Unity)*

- ScriptableObject authoring layer (Bridge): `SimulationConfigSO`, `NPCDefinitionSO`, `NPCSpawnListSO`, `FactionDefinitionSO`, `WorldRegistrySO`, `NPCScheduleSO`, `SensorRangeProfileSO`, `ItemDefinitionSO`, `TraitDefinitionSO`, `TraitLibrarySO`
- `NPCSpawner` MonoBehaviour
- `SimulationManager.ReplacePerceptionSystem()` API

## [0.3.0] – 2025-03-05 *(C# Unity)*

- Civilization systems: Inventory, Schedule, FactionRegistry, PopulationStats
- 8 new actions: WalkTo, Socialize, Work, Attack, Gather, Trade, Heal, Pray
- NPCFactory: Farmer + Priest archetypes added
- O(1) ring buffer in NPCMemory, StimulusDispatcher zero-alloc drain

## [0.2.0-alpha] – 2025-02-21 *(C# Unity)*

- Initial alpha: SimulationManager, Clock, WorldAdapter, NPC core, 3 actions (Eat, Sleep, Flee)
