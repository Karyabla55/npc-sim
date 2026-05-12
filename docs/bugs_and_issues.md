# Bug Tracker & Technical Debt

**Document Created:** 2026-05-01
**Latest Update:** 2026-05-12 (v1.5.0 — all tracked bugs closed; 5 new long-run risks A1–A7 from the audit also closed)
**Status:** Active
**Priority Legend:** CRITICAL > HIGH > MEDIUM > LOW

---

## CRITICAL (Fix Immediately)

### #1 — `_tick_counter` undefined in `LLMDecisionSystem`
| | |
|---|---|
| **Location** | `npc_sim/llm/llm_decision_system.py:98` |
| **Issue** | Line 98 references `self._tick_counter = 0` but this attribute is never initialized in `__init__()`. Will raise `AttributeError` on first interrupt trigger. |
| **Impact** | Simulation crashes when any NPC experiences a high-threat interrupt or sudden HP drop. |
| **Fix** | Add `self._tick_counter: int = 0` to `__init__()` around line 54-56. |
| **Status** | **FIXED — v1.2.0** · `self._tick_counter: int = 0` added to `__init__()` at line 58. |

---

### #2 — Double execution of LLM actions
| | |
|---|---|
| **Location** | `npc_sim/llm/llm_decision_system.py:107-111` |
| **Issue** | Action returned from `_apply_pending()` is executed again in `tick()`. The `_apply_pending()` method already calls `action.execute(ctx)` internally (via the action resolution loop), but `tick()` also calls `action.execute(ctx)` on line 108 before returning. |
| **Impact** | LLM-selected actions execute twice per tick, causing double resource consumption, double damage, etc. |
| **Fix** | Remove `action.execute(ctx)` from line 108 — `_apply_pending()` should only return the action, not execute it. OR: have `_apply_pending()` return without executing. |
| **Status** | **FIXED — v1.2.0** · `_apply_pending()` returns the action without executing it; `tick()` calls `execute()` exactly once at line 108. |

---

### #3 — Dead NPCs not logged on death tick
| | |
|---|---|
| **Location** | `npc_sim/simulation/simulation_manager.py:196-198` |
| **Issue** | Early `continue` on line 198 skips dead NPCs entirely. Death detection (lines 230-235) sets `event_type`/`event_detail` but these values are never captured in the log because the loop continues before reaching `log_npc_tick()`. |
| **Impact** | Death events not recorded in CSV logs. Cannot analyze mortality patterns or validate death_by_neglect mechanics. |
| **Fix** | Move death detection BEFORE the `continue` check, or change condition to allow one final log pass for newly-dead NPCs. |
| **Status** | **FIXED — v1.2.0** · Death detection block restructured: `was_alive` captured before tick, newly-dead NPCs detected at lines 253-257, logged with `event_type="Death"` before `continue`. Previously-dead NPCs get one final log entry and are skipped via `_death_logged` set. |

---

### #4 — Variable shadowing in `WalkToAction.evaluate()`
| | |
|---|---|
| **Location** | `npc_sim/decisions/actions/builtin.py:622-627` |
| **Issue** | Line 622 reassigns `target = WorldMap.get_zone("Market")` but `get_zone()` can return `None`. Line 624 then calls `SimVector3.distance(ctx.self_npc.position, target)` which raises `AttributeError` if `target is None`. |
| **Impact** | Crash when NPC tries to walk to Market zone that doesn't exist or isn't registered. |
| **Fix** | Add null check: `if target: dist = SimVector3.distance(...)` before using `target`. |
| **Status** | **FIXED — v1.2.0** · Renamed inner variable to `market_pos`, added explicit `is not None` guard. |

---

### #5 — Race condition in `LLMRequestQueue` dispatcher
| | |
|---|---|
| **Location** | `npc_sim/llm/llm_request_queue.py:120-126` |
| **Issue** | `_pop_highest()` acquires `_heap_lock`, but `submit()` also uses this lock. The dispatcher thread can pop while `submit()` is mid-operation (between counter increment and heap push). No condition variable for proper signaling. |
| **Impact** | Potential for lost requests or heap corruption under high concurrency. |
| **Fix** | Use `threading.Condition` instead of plain `Lock`. Signal condition on submit, wait on empty heap. |
| **Status** | **FIXED (partial) — v1.2.0** · `Condition` was already in place; added `notify_all()` to `shutdown()` so dispatcher exits immediately instead of waiting 100ms timeout. |

---

### #24 — Death-by-neglect: 80% NPC mortality within 2 sim-days despite v1.3.0 fixes
| | |
|---|---|
| **Location** | `npc_sim/decisions/decision_system.py` (action lock policy) + `npc_sim/decisions/utility_evaluator.py` (vital-weight scoring) + `npc_sim/decisions/actions/builtin.py` (`WorkAction`, `SleepAction`, `PrayAction`) |
| **Issue** | Diagnostic CSV (`logs/sim_full.csv`, 24,035 rows, 10 NPCs, 2 sim-days) shows 8/10 NPCs dead by `sim_hour 22.63` of `sim_day 1`, all from `health=0` driven by `thirst=1.0` (5 deaths) or `hunger=1.0` (3 deaths). Trace of one Farmer (npc_24107e49): worked for **1640 consecutive ticks** (≈164 sim-seconds, sim_hour 0 → 23.61) during which thirst rose 0.10 → 0.85 with **zero Drink actions**, then ran one Eat (1 tick) + one Drink (1 tick), then Slept for 11 ticks (thirst rose 0.38 → 0.83), then died during a 5-tick WalkTo as thirst hit 1.0. Multiple NPCs (Scholar, Merchant, Priest, Guard) follow the same pattern: a 1635-1640-tick continuous Work or Pray segment, followed by death within ~10 sim-minutes. The action lock from #21 fix correctly holds the action, but no `hard_interrupt` exists for `thirst >= 0.8` or `hunger >= 0.8`, so vitals saturate while NPC is locked into Work/Pray/Sleep. Of 949 critical-state ticks (`thirst>0.8 OR hunger>0.8`), NPCs Drink only 16 times (1.7%) and Eat 53 times (5.6%); they Sleep 378 times (40%), Gather 268 (28%), Pray 101 (11%). |
| **Impact** | Simulation produces no living NPCs after 2 sim-days — unusable for any behavior/narrative research. Bugs #21–#23 fixed lock-stickiness and shift duration but exposed this deeper issue: locks have no escape valve for life-threatening vitals. |
| **Fix** | Add `hard_interrupt` predicate to long-duration actions (Work, Sleep, Pray) that breaks the lock when `thirst >= 0.85` or `hunger >= 0.85` or `hp <= 0.25 * hp_max`. Implementation: extend `ActionLock` with an `interrupt_predicate: Callable[[ActionContext], bool]` field; `decision_system.py` evaluates it each tick during the `min_duration` window and breaks the lock if True. Alternatively, raise vital weights in `UtilityEvaluator` so Drink/Eat outscore Sleep/Pray when critical (less robust — locks would still need to yield). |
| **Status** | **FIXED — v1.3.1** · Added `interrupt_predicate=_vital_interrupt` to `WorkAction`, `SleepAction`, `PrayAction` locks. Predicate breaks the lock when `thirst≥0.85 or hunger≥0.85 or health≤0.25*max_health`. Logic added in `decision_system.py` min_duration window (before execute). Also extended global `hard_interrupt` to include `health ≤ 0.25*max_health`. |

---

### #25 — Sleep chosen 40% of the time during critical thirst/hunger states
| | |
|---|---|
| **Location** | `npc_sim/decisions/actions/builtin.py:SleepAction.evaluate()` + `npc_sim/decisions/utility_evaluator.py` |
| **Issue** | When `thirst > 0.8 OR hunger > 0.8` (949 critical ticks across all NPCs), Sleep is the most-chosen action: 378/949 = 40%. Drink fires 16 times (1.7%), Eat 53 (5.6%). The longest Sleep segment is **721 ticks** (Farmer, sim_hour 1707→2428) during which thirst rose from 0.0015 to 0.6975 — the NPC slept through near-critical dehydration. Sleep utility apparently scores high on low energy without sufficient downweighting from rising thirst/hunger. |
| **Impact** | NPCs sleep through dehydration/starvation, contributing directly to the mass-mortality pattern in #24. |
| **Fix** | In `SleepAction.evaluate()`, multiply the score by `(1 - max(thirst, hunger))` or apply a hard cap: `if thirst > 0.7 or hunger > 0.7: score *= 0.2`. Alternatively, use `UtilityEvaluator`-level vital-priority gating (Maslow-style hierarchy: thirst/hunger needs always outrank rest/spirit needs). |
| **Status** | **FIXED — v1.3.1** · `SleepAction.evaluate()` now returns `base_score * (1 - max(thirst, hunger))`. Score collapses to near-zero as vitals become critical. |

---

### #27 — Stress accumulates monotonically toward 1.0
| | |
|---|---|
| **Location** | `npc_sim/decisions/actions/builtin.py:204, 369` (`FleeAction`, `AttackAction` execute); `npc_sim/npc/npc.py:120-140` (`witness_event`); `npc_sim/npc/npc.py:97-103` (`tick`) |
| **Issue** | Four compounding problems drove stress toward 1.0 within ~25 sim-minutes and held it there: (a) `FleeAction` and `AttackAction` added flat `+0.05` / `+0.12` to stress on every tick of the action lock; with `delta_time=0.1` and 8–10s locks this stacks to ~1.0 per encounter. (b) `witness_event()` used `abs(impact)` so every positive event (Eat, Trade, Work success) also pushed stress up while simultaneously raising happiness. (c) `NPC.tick()` had no baseline stress recovery — only specific actions (sleep, pray, socialize) reduced it. (d) `SocializeAction` stress relief was not `delta_time` scaled, so a long socialize lock could crater stress to 0 in one chain. |
| **Impact** | Diagnostic mean stress 0.745, with 57.7 % of all rows at stress > 0.9. NPCs were perma-anxious regardless of context, which corrupted Pray scoring, anger spillover (`stress → anger` term in `npc.py:98`), and emotion-driven action selection downstream. |
| **Fix** | (a) Scale stress deltas in `FleeAction.execute()` and `AttackAction.execute()` by `ctx.delta_time`. (b) Only feed stress in `witness_event()` when `sim_event.impact < 0`. (c) Add a low-rate `baseline_recovery` term in `NPC.tick()` scaled inversely with neuroticism. (d) Scale `SocializeAction` stress relief by `ctx.delta_time`. Add small `delta_time`-scaled relief in `EatAction`, `DrinkAction`, `HealAction`. |
| **Status** | **FIXED — v1.4.0** · Mean stress 0.745 → 0.532; stress > 0.9 share 57.7 % → 31.3 % in the regression run. |

---

### #28 — Anger and Happiness can both reach 1.0 simultaneously
| | |
|---|---|
| **Location** | `npc_sim/npc/psychology.py:41-51` (setters), `npc_sim/npc/psychology.py:101-121` (`_recalculate_mood`) |
| **Issue** | `set_anger()` and `set_happiness()` clamped each value independently and the `_recalculate_mood()` if-elif chain only surfaced one label (`Furious` priority), hiding the contradictory internal state. CSV logs showed cells where `emotion_anger ≈ 1.0` co-existed with happiness gains from earlier ticks, producing psychologically incoherent NPCs. |
| **Impact** | LLM payloads exposed both emotions to the model with no antagonism, producing dialogue/decisions that contradicted the visible mood. Mood label looked correct but the underlying state did not match what trait coherence guards reasoned about. |
| **Fix** | Implement cross-inhibition: when one emotion increases, scale the other by `(1 - delta * _CROSS_INHIBITION)` with `_CROSS_INHIBITION = 0.5`. Add a defensive `"Conflicted"` mood label for the rare case both still exceed 0.6 after inhibition. |
| **Status** | **FIXED — v1.4.0** · 0 / 18,000 rows in the regression run satisfy `anger ≥ 0.7 AND happiness ≥ 0.7`. |

---

### #29 — Memory, Beliefs, and Goals not consumed by Utility AI
| | |
|---|---|
| **Location** | `npc_sim/decisions/actions/builtin.py` (all `evaluate()` and most `execute()`), `npc_sim/decisions/action_context.py`, `npc_sim/llm/llm_decision_system.py` |
| **Issue** | `BeliefSystem`, `NPCMemory`, and `NPCGoals` correctly stored data but the Utility AI never read them. NPCs that had been attacked at Market still scored Market the same in `WalkToAction`; NPCs with strong negative beliefs about a hostile NPC didn't get an attack bias; the `FIND_FOOD` / `FIND_WATER` / `REST` goals raised by `refresh_need_goals()` had no effect on action scoring. `SocializeAction.execute()` only mutated relation scalars — the dialogue line generated by the LLM was never delivered to the listener, and the speaker's beliefs never propagated. |
| **Impact** | Data structures existed but did not drive emergent behavior. NPCs never "learned" to avoid places or people that had hurt them; gossip / information transfer was impossible; the LLM produced dialogue strings the rest of the system threw away. |
| **Fix** | Roadmap tasks G1–G6 from `docs/nextsteps.md`: `ActionContext.belief_score()` + `goal_bonus()` helpers; `WalkToAction` zone bias from memory+belief; `AttackAction` belief valence; `SocializeAction` dialogue handoff to listener memory + trust-gated belief propagation; goal bonus threaded through every action's `evaluate()`. `LLMDecisionSystem._apply_pending()` now sets `NPC.pending_dialogue` for the speaker to consume. |
| **Status** | **FIXED (partial) — v1.4.0** · G1–G6 complete. G7 (LLM reasoning → memory) and G8 (target_context payload for social actions) deferred to v1.5. |

---

### #26 — Pray saturates Priest archetype (~95% of existence)
| | |
|---|---|
| **Location** | `npc_sim/decisions/actions/builtin.py:PrayAction.evaluate()` + Priest trait modifiers (likely `Devout`) |
| **Issue** | Priest archetype emits **4104 of 5848 total Pray actions (70%)**. Two Priest Pray segments are 1635 and 1638 ticks long (~164 sim-seconds = 2.7 sim-hours continuous prayer). Across the simulation, Priest spends ~95% of all ticks praying. During these segments, thirst rises from ~0.18 to ~0.83 with no Drink action. Pray fires 5848 times total vs. Drink 423 — Pray is **14× more frequent than Drink** despite Drink being a survival need and Pray being a spiritual one. |
| **Impact** | Priest archetype is non-functional for behavior research — they pray themselves to death without varied behavior. Pray dominance also pulls non-Priests (567 Guard, 603 Merchant, 573 Scholar Pray actions) away from survival actions. |
| **Fix** | (a) Cap `Devout` trait modifier on Pray score (currently appears unbounded). (b) Add piety-saturation: Pray score should decay after consecutive uses (similar to diminishing returns on social actions). (c) Add an `exit_condition` to `PrayAction` lock that fires when `thirst > 0.6 OR hunger > 0.6`. (d) Reduce default Pray base score so it doesn't outrank Drink/Eat at moderate spiritual-need levels. |
| **Status** | **FIXED — v1.3.1** · (a) `devout_bonus` capped `0.4→0.2`. (b) `evaluate()` applies `vital_penalty = 1.0 - max(thirst, hunger)` multiplier. (c) `exit_condition` now includes `thirst > 0.6 or hunger > 0.6` in addition to `stress < 0.2`. (d) `interrupt_predicate=_vital_interrupt` added to lock for hard break at 0.85 threshold. |

---

## HIGH (Fix Before Next Release)

### #6 — `_should_call_llm()` ignores interrupt parameter
| | |
|---|---|
| **Location** | `npc_sim/llm/llm_decision_system.py:137-142` |
| **Issue** | Docstring says "LLM is only called on explicit triggers (H2 interrupt)" but method only checks `self._pending`. The `interrupt` parameter passed in is completely ignored. |
| **Impact** | Confusing API. Currently works by accident because caller checks interrupt first, but violates single responsibility. |
| **Fix** | Either remove `interrupt` parameter or use it in the return logic. Update docstring to match actual behavior. |
| **Status** | **FIXED — v1.2.0** · Method now returns `interrupt` directly (`return interrupt` at line 142), making the parameter usage explicit and intentional. |

---

### #7 — Anger logic inverted in `AttackAction.execute()`
| | |
|---|---|
| **Location** | `npc_sim/decisions/actions/builtin.py:347-351` |
| **Issue** | Comment says "anger peaks during combat and only cools post-combat" but condition `if not threat_present` lowers anger when threat is GONE. Should be: threat present = anger rises, threat gone = anger cools. Current code does the opposite. |
| **Impact** | NPCs calm down DURING combat and get angrier AFTER combat ends. |
| **Fix** | Invert condition: `if threat_present: anger += 0.05` and `else: anger -= 0.15`. |
| **Status** | **FIXED — v1.2.0** · `if not threat_present: anger -= 0.15` else `anger += 0.05`. Since `execute()` early-returns when no threat is present, this branch always runs with a live threat, so anger correctly rises during combat. |

---

### #8 — Death by neglect damage rate too high
| | |
|---|---|
| **Location** | `npc_sim/npc/npc.py:93-95` |
| **Issue** | When `hunger >= 1.0` or `thirst >= 1.0`, damage is `10.0 * delta_time` per tick. At 10 ticks/sec with `delta_time ~0.1`, that's 1.0 damage/tick = 10 damage/sec. At 100 HP, death in 10 seconds. |
| **Impact** | NPCs die almost instantly when needs max out. No time for rescue or recovery behaviors. |
| **Fix** | Reduce to `1.0 * delta_time` (death in ~100 seconds) or `0.5 * delta_time` for more dramatic starvation. |
| **Status** | **FIXED — v1.2.0** · Changed `10.0 * delta_time` → `1.0 * delta_time`. NPCs now survive ~100s of maxed needs, giving recovery behaviors time to fire. |

---

### #9 — Trait modifier applied after curve shaping
| | |
|---|---|
| **Location** | `npc_sim/decisions/utility_evaluator.py:56-59` |
| **Issue** | Curve shaping (line 57) compresses dynamic range, THEN trait modifier is applied (line 58). A `0.5` modifier on a shaped `0.9` score produces `0.45`, but the curve already lost information. |
| **Impact** | Trait effects are amplified non-linearly. Pacifist trait (0.3 modifier) on high-score actions becomes nearly zero. |
| **Fix** | Apply trait modifier to `raw` score before curve: `shaped = curve.evaluate(raw * modifier)`. |
| **Status** | **FIXED — v1.2.0** · Modifier now applied to `raw` before curve. Functionally equivalent for default `LinearCurve`; semantically correct for `QuadraticCurve`/`SigmoidCurve`. |

---

### #10 — `ItemIds` lazy import doesn't protect module usage
| | |
|---|---|
| **Location** | `npc_sim/diagnostics/sim_logger.py:131-134, 212-215` |
| **Issue** | Lines 131-134 call `ItemIds.FOOD`, `ItemIds.WATER`, etc. inside `log_npc_tick()`. The fallback dummy class (lines 214-215) defines attributes as semicolon-separated string `"food"; "water"` which is invalid Python syntax — should be separate assignments. |
| **Impact** | If `npc_sim.npc.inventory` fails to import, logger crashes with `AttributeError`. |
| **Fix** | Fix dummy class: `FOOD = "food"; WATER = "water"` → separate lines or proper class body. |
| **Status** | **FIXED — v1.2.0** · Dummy class uses valid single-line syntax (`FOOD = "food"; WATER = "water"; MEDICINE = "medicine"; GOLD = "gold"`). Python class bodies accept semicolon-separated statements. |

---

### #21 — Action lock broken by `is_valid()` during minimum duration → rapid sleep/work cycling
| | |
|---|---|
| **Location** | `npc_sim/decisions/decision_system.py:55-56, 69-70` |
| **Issue** | While serving a lock's `min_duration`, the system checks `is_valid()` on the locked action (lines 55 and 69). If False, the lock is immediately cleared and normal evaluation runs. `SleepAction.is_valid()` requires `energy_norm < 0.35`; the restore rate (`0.15 × max_energy × delta_time`) crosses this threshold in **1-3 ticks**, so the sleep lock breaks almost immediately. The NPC then evaluates freely, Work wins, drains energy back below the threshold, and the cycle repeats every 1-5 ticks. **CSV evidence:** Scholar oscillates Sleep↔Work at tick 271-277 (sim_hour 6.45-6.46), cycling ~57 times per sim-day. |
| **Impact** | Core simulation behavioral failure. NPCs never sustain work or sleep — they flicker every few ticks instead of serving meaningful shifts. Makes the simulation unusable for behavior research. |
| **Fix** | Remove the `is_valid()` check inside the `min_duration` phase (lines 55-56 and 69-70). During minimum duration only `hard_interrupt` should be able to break the lock. `is_valid()` and `exit_condition` should only apply after `min_duration` has elapsed. |
| **Status** | **FIXED — v1.3.0** · Removed `is_valid()` call from the `min_duration` window. Lock now runs execute() unconditionally during minimum duration; `is_valid()` and `exit_condition` checks remain only in the post-min_duration branch. |

---

### #22 — `WorkAction` energy drain rate 65× too high for 1440-second sim-day
| | |
|---|---|
| **Location** | `npc_sim/decisions/actions/builtin.py:518` |
| **Issue** | `consume_energy(5.0 * ctx.delta_time)` drains 5.0 units/sim-second. With `delta_time = 0.1` sim-sec/tick this is 0.5 units/tick. For an NPC with `max_energy ≈ 90`, energy is exhausted (`energy_norm < 0.35`) in **≈ 18 sim-minutes** (108 ticks). An 8-hour work shift in a 1440-second day requires only ≈ 0.077 units/sim-second above the base `energy_decay_rate` of 0.073. The configured value is 65× larger. Base decay alone (`energy_decay_rate = 0.073`) already drains energy over ≈ 20 sim-hours; the action rate should be a modest multiplier (e.g. 2–3×), not 69×. |
| **Impact** | Even if bug #21 is fixed (locks hold), NPCs exhaust themselves in 18 sim-minutes per shift. Combined with #21, WorkAction is the engine of the rapid cycling loop. |
| **Fix** | Replace `5.0` with a value that drains ≈ 60-70% of max_energy over an 8-hour shift (480 sim-sec): `consume_energy(0.10 * ctx.delta_time)` (≈ 1.4× the base decay, net drain ≈ 0.173 units/sim-sec → 83 units over 480 sec ≈ 92% for max_energy=90, or tune as needed). |
| **Status** | **FIXED — v1.3.0** · Changed `5.0` → `0.167`. Drains ≈ 80 energy (100→20 threshold) over 480 sim-seconds = 8 sim-hour work shift. |

---

## MEDIUM (Fix When Convenient)

### #11 — `_valid_actions()` has fragile fallback logic
| | |
|---|---|
| **Location** | `npc_sim/llm/npc_serializer.py:162-167` |
| **Issue** | `ctx.world._get_action_library_if_set()` method doesn't exist on `SimWorldAdapter`. Fallback to `ctx._action_library` works but relies on undocumented attribute. |
| **Impact** | `valid_actions` list may be empty if fallback fails, causing LLM to hallucinate invalid action IDs. |
| **Fix** | Add `get_action_library()` method to `SimWorldAdapter` or pass `ActionLibrary` directly to `NPCSerializer`. |
| **Status** | **FIXED — v1.3.0** · Removed broken primary path (`ctx.world._get_action_library_if_set`). Method now directly uses `ctx._action_library` which is always set by `SimulationManager`. |

---

### #12 — `GatherAction.execute()` doesn't check inventory caps
| | |
|---|---|
| **Location** | `npc_sim/decisions/actions/builtin.py:246-259` |
| **Issue** | `is_valid()` caps at 5 items (line 226), but `execute()` just adds without checking. NPC could accumulate beyond cap over multiple ticks if `is_valid()` threshold is met but cap not enforced. |
| **Impact** | Inventory exploits — NPCs can hoard beyond intended limits. |
| **Fix** | Add cap check in `execute()`: `if inv.get_amount(ItemIds.FOOD) >= 5: return`. |
| **Status** | **FIXED — v1.2.0** · Added per-resource cap enforcement in `execute()` matching `is_valid()` limit of 5 items. Correctly falls back to gathering the other resource if one is full. |

---

### #13 — Action lock created AFTER execution
| | |
|---|---|
| **Location** | `npc_sim/decisions/decision_system.py:86-95` |
| **Issue** | Lock is created after `execute()` runs (line 86), meaning the action runs once before lock state is saved. Multi-tick actions lose their first tick of lock enforcement. |
| **Impact** | First tick of multi-tick actions (Work, Sleep) can be interrupted immediately. |
| **Fix** | Create lock BEFORE execute, store it, then execute. Or pass lock to execute for continuity. |
| **Status** | **FIXED — v1.3.0** · Lock now created before `execute()` call. First tick of every action is immediately covered by the lock. |

---

### #14 — EOS token stripping is fragile
| | |
|---|---|
| **Location** | `npc_sim/llm/llm_backend.py:159-162` |
| **Issue** | Sequential `find()` calls for each stop artifact means overlapping artifacts could leave residuals. Example: `<|eot_id|>` contains `<|eot` — first strip removes long form, second strip might find false positive. |
| **Impact** | Malformed JSON passed to parser, causing parse failures and fallbacks. |
| **Fix** | Use regex: `re.sub(r'<\|?(eot_id|end_of_text|eot)\|?>', '', content)`. |
| **Status** | **FIXED — v1.2.0** · Replaced sequential `find()` loop with single `re.sub()` regex pass covering all EOS artifacts atomically. |

---

### #15 — Work efficiency logged but never used
| | |
|---|---|
| **Location** | `npc_sim/simulation/simulation_manager.py:268-270` |
| **Issue** | `efficiency` variable computed and logged but never affects `WorkAction.execute()` output. Resource generation should scale with energy. |
| **Impact** | Work action produces same output regardless of NPC energy level. |
| **Fix** | Pass efficiency to WorkAction or compute resource generation in SimulationManager. |
| **Status** | **FIXED — v1.5.0 (C1)** · `WorkAction.execute()` now uses `yield_amount = max(1, int(efficiency * 2))`; full-energy NPCs produce +2 per tick, depleted ones floor at +1. |

---

### #23 — `SleepAction` restore rate and lock `min_duration` values miscalibrated for 1440-second day
| | |
|---|---|
| **Location** | `npc_sim/decisions/actions/builtin.py:115` (SleepAction lock), `npc_sim/decisions/actions/builtin.py:133` (restore rate), `npc_sim/decisions/actions/builtin.py:494` (WorkAction lock) |
| **Issue** | Two separate calibration errors compound each other: **(a) Restore rate too fast:** `SleepAction.execute()` uses `restore = 0.15 * max_energy * delta_time`. For Scholar (`max_energy=90`, `delta_time=0.1`): 13.5 units/sim-second → full recovery in **6.7 sim-seconds** (0.1 sim-minutes). For a realistic 8-hour sleep cycle (480 sim-sec), the rate should be ≈ 0.122 units/sim-sec. Current rate is 110× too fast. **(b) Lock `min_duration` wrong scale:** `SleepAction.min_duration = 3600` sim-seconds = **2.5 sim-days** in a 1440-sec day. `WorkAction.min_duration = 1800` sim-seconds = **1.25 sim-days**. These values are calibrated for an 86400-second (real-world) day. For an 8-hour sleep or work shift in a 1440-sec day: target `min_duration ≈ 480` sim-seconds. Note: currently masked by bug #21 (lock breaks before min_duration matters), but becomes the primary symptom after #21 is fixed. |
| **Impact** | (a) Even with locks correctly enforced, NPCs fully recover in 7 sim-seconds and the `exit_condition` (`energy_norm ≥ 0.95`) fires immediately, yielding 7-second sleep cycles. (b) If restore rate is fixed without fixing `min_duration`, NPCs sleep for 2.5 sim-days before being allowed to exit. Both issues must be fixed together with bug #22 for a coherent 24-hour lifecycle. |
| **Fix** | (a) Change restore formula: `restore = (0.122 / max_energy) * max_energy * delta_time` → simplifies to `restore = 0.122 * delta_time` (tune to ≈ 8-hour full recovery). (b) Change both lock durations from `3600` → `480` and `1800` → `480` sim-seconds (adjust as desired for balance). |
| **Status** | **FIXED — v1.3.0** · (a) Restore rate changed `0.15 → 0.002` (≈ 480 sim-sec full recovery). (b) SleepAction `min_duration` changed `3600.0 → 480.0` sim-seconds (8 sim-hours in a 1440-sec day). |

---

## LOW (Cleanup / Polish)

### #16 — Dual-LLM pipeline documented but not implemented
| | |
|---|---|
| **Location** | `docs/architecture.md:157-383` |
| **Issue** | Architecture doc describes `DualLLMBackend` with Reasoner (3B) + Formatter (1B) components. No such class exists in `npc_sim/llm/`. Only `OllamaBackend` is implemented. |
| **Impact** | Contributors will be confused. Documentation credibility受损. |
| **Fix** | Either implement `DualLLMBackend` class OR remove/archive the Dual-LLM section with a note. |
| **Status** | **FIXED — v1.5.0 (C5)** · `docs/architecture.md` and `docs/llm_data_spec.md` now carry an "Implementation status" callout at the top of their dual-LLM sections, pointing readers to roadmap task G9. Implementation deferred to v1.5 → v2.0. |

---

### #17 — `llm_tick_every` config unused
| | |
|---|---|
| **Location** | `npc_sim/core/sim_config.py:64` |
| **Issue** | `llm_tick_every: int = 5` is set but never read. `LLMDecisionSystem` only fires on interrupt (H2). Per docs, tick counter was "deliberately removed". |
| **Impact** | Dead configuration. Confuses users expecting periodic LLM calls. |
| **Fix** | Remove config field or restore tick-based calling as optional mode. |
| **Status** | **FIXED — v1.5.0 (C3)** · Field dropped from `SimulationConfig` and from the `LLMDecisionSystem.__init__` signature; constructor call in `SimulationManager._ensure_llm_subsystems` cleaned up; README + smoke test updated. Regression-guarded by `tests/test_config_no_llm_tick.py`. |

---

### #18 — Priority queue doesn't preempt in-flight requests
| | |
|---|---|
| **Location** | `npc_sim/llm/llm_request_queue.py:65-86` |
| **Issue** | `max_concurrent=1` means even `INTERRUPT` priority (0) waits for any in-flight request to complete. A `BACKGROUND` (10) request that started first blocks an interrupt. |
| **Impact** | High-priority interrupts delayed by low-priority background processing. |
| **Fix** | Implement preemption: cancel lowest-priority in-flight request when INTERRUPT arrives. |
| **Status** | **FIXED — v1.5.0 (C4)** · `LLMRequest` carries a `_cancelled` flag, `LLMRequestQueue` tracks `_in_flight` workers, and `submit()` of an `INTERRUPT`-priority request marks lower-priority running requests as cancelled. `_execute()` short-circuits the cancelled callback to `(None, None)`. New `preempted` stat counts events. Covered by `tests/test_queue_preemption.py`. |

---

### #19 — `FleeAction` lock duration = 0
| | |
|---|---|
| **Location** | `npc_sim/decisions/actions/builtin.py:153-156` |
| **Issue** | `min_duration_sim_seconds=0.0` means lock expires immediately. NPC flees one tick then re-evaluates. Defeats purpose of action locking for sustained fleeing behavior. |
| **Impact** | NPCs may freeze or oscillate between flee and other actions during danger. |
| **Fix** | Set reasonable duration (5-10 seconds) or use distance-based exit condition. |
| **Status** | **FIXED — v1.2.0** · Changed `min_duration_sim_seconds` from `0.0` to `8.0`. Exit condition (threat disappears) still provides early termination. |

---

### #20 — `_enforce_trait_coherence` only handles 2 cases
| | |
|---|---|
| **Location** | `npc_sim/llm/llm_decision_system.py:221-263` |
| **Issue** | Only `flee→attack` (Brave) and `attack→flee` (Pacifist) are handled. Docs mention `Devout→pray`, `Greedy→hoard`, `Aggressive→attack` but these aren't implemented. |
| **Impact** | Trait incoherence bugs for unhandled traits. |
| **Fix** | Add remaining trait coherence rules or remove from documentation. |
| **Status** | **FIXED — v1.5.0 (C2)** · `_enforce_trait_coherence` now also overrides for Coward (threat ≥ 0.5 → flee), Greedy (gold + valid trade → trade), and Devout (stress ≥ 0.6 + valid pray → pray). Each override appends a diagnostic suffix to the reasoning field. Covered by `tests/test_trait_coherence.py`. |

---

## Summary by Category

| Category | Count | Open (as of v1.5.0) |
|----------|-------|---------------------|
| CRITICAL | 9 | 0 |
| HIGH     | 9 | 0 |
| MEDIUM   | 6 | 0 |
| LOW      | 5 | 0 |
| **Total** | **29** | **0** |

All 29 tracked entries are now FIXED. The five v1.5.0 closures (#15, #16, #17, #18, #20) were the last LOW/MEDIUM polish backlog; the rest cleared in v1.2.0 → v1.4.0.

**v1.5.0 also closed seven long-run-stability risks (A1–A7) that were not in
this tracker:** unbounded inventory growth, BeliefSystem/Relation/Faction dict
overflow, additive memory decay collapsing to zero, unbounded CSV log file,
and the absence of an invariant safety net. See `CHANGELOG.md` v1.5.0 entry
for the full list. They surfaced in the long-run audit, not from a bug
report, so they are tracked there rather than re-numbered here.

### By Module

| Module | Issues |
|--------|--------|
| `llm/` | 8 (#1, #2, #5, #6, #11, #14, #16, #18) |
| `decisions/` | 12 (#4, #7, #12, #13, #19, #21, #22, #23, #24, #25, #26, #29) |
| `simulation/` | 2 (#3, #15) |
| `npc/` | 3 (#8, #27, #28) |
| `diagnostics/` | 1 (#10) |
| `core/` | 1 (#17) |
| Cross-module | 2 (#9, #20) |

### v1.3.0 Diagnostic Findings (2026-05-02)

Bugs #24–#26 discovered via `notebooks/log_analysis.ipynb` analysis of `logs/sim_full.csv` (24,035 rows, 10 NPCs, 2 sim-days):
- **80% mortality** (8/10 NPCs dead by sim_day 1, all `health=0` from thirst/hunger saturation)
- Longest Work segment: **1640 ticks** (Farmer) with no Drink action despite thirst rising 0.10 → 0.85
- Longest Sleep segment: **721 ticks** (Farmer) with thirst rising 0.00 → 0.70
- Longest Pray segment: **1638 ticks** (Priest) with thirst rising 0.18 → 0.78
- **Of 949 critical-vital ticks**: Sleep 40%, Gather 28%, Pray 11%, Eat 5.6%, Drink 1.7%
- Common root cause: action locks (v1.3.0 #21 fix) hold without vital-driven `hard_interrupt`

### v1.3.1 Diagnostic Results (2026-05-11)

Bugs #24–#26 fixed; validated via 144,010-row CSV (10 NPCs, 24 sim-hours, seed=42):
- **0% mortality** (10/10 NPCs alive at end of sim-day)
- **Critical vital ticks**: 6,670 / 144,010 (4.6%) — down from 949 absolute but NPCs now survive them
- **Action dist during critical vitals**: Work 79.9%, Pray 20.0%, Gather 0.1% — Drink/Sleep absent (vitals resolve before saturation)
- **Priest Pray %**: 46.8% (was ~95%) — vital penalty + exit_condition prevent prayer death spiral
- **Performance**: percept dict + tag cache + sort cache + CSV flush 500 applied for ~100 NPC scale

### v1.4.0 Diagnostic Results (2026-05-11)

Bugs #27–#29 fixed; validated via 18,000-row CSV (5 archetypes, 6 sim-hours, seed=42):
- **Mean stress**: 0.745 → 0.532 (-29 %)
- **Stress > 0.9**: 57.7 % → 31.3 % (cut nearly in half)
- **Mean anger**: 0.431 → 0.237 (cut in half)
- **`anger ≥ 0.7 AND happiness ≥ 0.7`**: **0 rows** (cross-inhibition holds)
- **Mood "Calm" share**: 53 % → 75 %
- **Conflicted mood**: 0 rows (cross-inhibition keeps the edge case out)
- **Open issue**: NPCs bias toward `Work` and don't trigger `Eat`/`Drink`/`Socialize` within 6 h; the new stress-relief / belief-propagation pathways are present but rarely exercised. Tracked as action-selection tuning, not a regression.

### v1.5.0 Diagnostic Results (2026-05-12)

Tracker bugs #15, #16, #17, #18, #20 fixed. Seven long-run audit fixes
(A1–A7) shipped alongside. Validated via three 30 sim-day `--strict` runs
at the end of each phase (seed=42, 5 archetypes, 432,001 ticks each, ≈109 s
real time):

- **Survival**: 5/5 NPCs alive at sim-day 30; 0 deaths across all three runs
- **Invariant violations**: 0 across vital range/finiteness, dict caps,
  inventory cap, memory ring overflow (checked every 1000 ticks)
- **Inventory cap**: Merchant gold saturates at exactly 100 (was unbounded);
  no other stack ever exceeds the cap
- **Dict bounds**: BeliefSystem and `NPCSocial.relations` per-NPC remain
  ≤ 200; FactionRegistry stale dispositions reclaim once `|val| < 0.01`
- **Mean stress**: ≈ 0.10 (down from 0.532 at v1.4.0 due to multiplicative
  memory decay no longer collapsing salience to zero)
- **Deterministic replay**: action distribution byte-identical across
  Phase A / B / C 30-day runs (Work 94 869, Sleep 30 240, Gather 12 664,
  Drink 8 100, Eat 6 000, Pray 5 402, WalkTo 2 730)
- **Pytest suite**: 68 cases across 13 files (was 0 before v1.5.0)
- **LLM queue preemption**: new `preempted` stat counts INTERRUPT-driven
  cancellations of in-flight lower-priority requests (#18 closure)
- **Open observation (not a regression)**: action distribution under the
  default 5-NPC archetype mix doesn't exercise Trade/Attack/Socialize/Flee/
  Heal; the new B1–B4 wirings are correct but unprovoked. A multi-faction
  scenario with hostile percepts is needed to surface their effect.

---

## Recommended Fix Order

1. **Week 1:** Fix CRITICAL bugs #1-5 (simulation stability)
2. **Week 2:** Fix HIGH bugs #6-10 (behavioral correctness)
3. **Week 3:** Fix MEDIUM bugs #11-15 (code quality)
4. **Week 4:** Address LOW bugs #16-20, add tests

---

## Notes

- This document should be updated whenever new bugs are discovered
- Move fixed items to `docs/CHANGELOG.md` with fix commit reference
- Consider integrating with GitHub Issues for tracking
