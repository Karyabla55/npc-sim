# Bug Tracker & Technical Debt

**Document Created:** 2026-05-01  
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
| **Status** | PENDING |

---

### #2 — Double execution of LLM actions
| | |
|---|---|
| **Location** | `npc_sim/llm/llm_decision_system.py:107-111` |
| **Issue** | Action returned from `_apply_pending()` is executed again in `tick()`. The `_apply_pending()` method already calls `action.execute(ctx)` internally (via the action resolution loop), but `tick()` also calls `action.execute(ctx)` on line 108 before returning. |
| **Impact** | LLM-selected actions execute twice per tick, causing double resource consumption, double damage, etc. |
| **Fix** | Remove `action.execute(ctx)` from line 108 — `_apply_pending()` should only return the action, not execute it. OR: have `_apply_pending()` return without executing. |
| **Status** | PENDING |

---

### #3 — Dead NPCs not logged on death tick
| | |
|---|---|
| **Location** | `npc_sim/simulation/simulation_manager.py:196-198` |
| **Issue** | Early `continue` on line 198 skips dead NPCs entirely. Death detection (lines 230-235) sets `event_type`/`event_detail` but these values are never captured in the log because the loop continues before reaching `log_npc_tick()`. |
| **Impact** | Death events not recorded in CSV logs. Cannot analyze mortality patterns or validate death_by_neglect mechanics. |
| **Fix** | Move death detection BEFORE the `continue` check, or change condition to allow one final log pass for newly-dead NPCs. |
| **Status** | PENDING |

---

### #4 — Variable shadowing in `WalkToAction.evaluate()`
| | |
|---|---|
| **Location** | `npc_sim/decisions/actions/builtin.py:622-627` |
| **Issue** | Line 622 reassigns `target = WorldMap.get_zone("Market")` but `get_zone()` can return `None`. Line 624 then calls `SimVector3.distance(ctx.self_npc.position, target)` which raises `AttributeError` if `target is None`. |
| **Impact** | Crash when NPC tries to walk to Market zone that doesn't exist or isn't registered. |
| **Fix** | Add null check: `if target: dist = SimVector3.distance(...)` before using `target`. |
| **Status** | PENDING |

---

### #5 — Race condition in `LLMRequestQueue` dispatcher
| | |
|---|---|
| **Location** | `npc_sim/llm/llm_request_queue.py:120-126` |
| **Issue** | `_pop_highest()` acquires `_heap_lock`, but `submit()` also uses this lock. The dispatcher thread can pop while `submit()` is mid-operation (between counter increment and heap push). No condition variable for proper signaling. |
| **Impact** | Potential for lost requests or heap corruption under high concurrency. |
| **Fix** | Use `threading.Condition` instead of plain `Lock`. Signal condition on submit, wait on empty heap. |
| **Status** | PENDING |

---

## HIGH (Fix Before Next Release)

### #6 — `_should_call_llm()` ignores interrupt parameter
| | |
|---|---|
| **Location** | `npc_sim/llm/llm_decision_system.py:137-142` |
| **Issue** | Docstring says "LLM is only called on explicit triggers (H2 interrupt)" but method only checks `self._pending`. The `interrupt` parameter passed in is completely ignored. |
| **Impact** | Confusing API. Currently works by accident because caller checks interrupt first, but violates single responsibility. |
| **Fix** | Either remove `interrupt` parameter or use it in the return logic. Update docstring to match actual behavior. |
| **Status** | PENDING |

---

### #7 — Anger logic inverted in `AttackAction.execute()`
| | |
|---|---|
| **Location** | `npc_sim/decisions/actions/builtin.py:347-351` |
| **Issue** | Comment says "anger peaks during combat and only cools post-combat" but condition `if not threat_present` lowers anger when threat is GONE. Should be: threat present = anger rises, threat gone = anger cools. Current code does the opposite. |
| **Impact** | NPCs calm down DURING combat and get angrier AFTER combat ends. |
| **Fix** | Invert condition: `if threat_present: anger += 0.05` and `else: anger -= 0.15`. |
| **Status** | PENDING |

---

### #8 — Death by neglect damage rate too high
| | |
|---|---|
| **Location** | `npc_sim/npc/npc.py:93-95` |
| **Issue** | When `hunger >= 1.0` or `thirst >= 1.0`, damage is `10.0 * delta_time` per tick. At 10 ticks/sec with `delta_time ~0.1`, that's 1.0 damage/tick = 10 damage/sec. At 100 HP, death in 10 seconds. |
| **Impact** | NPCs die almost instantly when needs max out. No time for rescue or recovery behaviors. |
| **Fix** | Reduce to `1.0 * delta_time` (death in ~100 seconds) or `0.5 * delta_time` for more dramatic starvation. |
| **Status** | PENDING |

---

### #9 — Trait modifier applied after curve shaping
| | |
|---|---|
| **Location** | `npc_sim/decisions/utility_evaluator.py:56-59` |
| **Issue** | Curve shaping (line 57) compresses dynamic range, THEN trait modifier is applied (line 58). A `0.5` modifier on a shaped `0.9` score produces `0.45`, but the curve already lost information. |
| **Impact** | Trait effects are amplified non-linearly. Pacifist trait (0.3 modifier) on high-score actions becomes nearly zero. |
| **Fix** | Apply trait modifier to `raw` score before curve: `shaped = curve.evaluate(raw * modifier)`. |
| **Status** | PENDING |

---

### #10 — `ItemIds` lazy import doesn't protect module usage
| | |
|---|---|
| **Location** | `npc_sim/diagnostics/sim_logger.py:131-134, 212-215` |
| **Issue** | Lines 131-134 call `ItemIds.FOOD`, `ItemIds.WATER`, etc. inside `log_npc_tick()`. The fallback dummy class (lines 214-215) defines attributes as semicolon-separated string `"food"; "water"` which is invalid Python syntax — should be separate assignments. |
| **Impact** | If `npc_sim.npc.inventory` fails to import, logger crashes with `AttributeError`. |
| **Fix** | Fix dummy class: `FOOD = "food"; WATER = "water"` → separate lines or proper class body. |
| **Status** | PENDING |

---

## MEDIUM (Fix When Convenient)

### #11 — `_valid_actions()` has fragile fallback logic
| | |
|---|---|
| **Location** | `npc_sim/llm/npc_serializer.py:162-167` |
| **Issue** | `ctx.world._get_action_library_if_set()` method doesn't exist on `SimWorldAdapter`. Fallback to `ctx._action_library` works but relies on undocumented attribute. |
| **Impact** | `valid_actions` list may be empty if fallback fails, causing LLM to hallucinate invalid action IDs. |
| **Fix** | Add `get_action_library()` method to `SimWorldAdapter` or pass `ActionLibrary` directly to `NPCSerializer`. |
| **Status** | PENDING |

---

### #12 — `GatherAction.execute()` doesn't check inventory caps
| | |
|---|---|
| **Location** | `npc_sim/decisions/actions/builtin.py:246-259` |
| **Issue** | `is_valid()` caps at 5 items (line 226), but `execute()` just adds without checking. NPC could accumulate beyond cap over multiple ticks if `is_valid()` threshold is met but cap not enforced. |
| **Impact** | Inventory exploits — NPCs can hoard beyond intended limits. |
| **Fix** | Add cap check in `execute()`: `if inv.get_amount(ItemIds.FOOD) >= 5: return`. |
| **Status** | PENDING |

---

### #13 — Action lock created AFTER execution
| | |
|---|---|
| **Location** | `npc_sim/decisions/decision_system.py:86-95` |
| **Issue** | Lock is created after `execute()` runs (line 86), meaning the action runs once before lock state is saved. Multi-tick actions lose their first tick of lock enforcement. |
| **Impact** | First tick of multi-tick actions (Work, Sleep) can be interrupted immediately. |
| **Fix** | Create lock BEFORE execute, store it, then execute. Or pass lock to execute for continuity. |
| **Status** | PENDING |

---

### #14 — EOS token stripping is fragile
| | |
|---|---|
| **Location** | `npc_sim/llm/llm_backend.py:159-162` |
| **Issue** | Sequential `find()` calls for each stop artifact means overlapping artifacts could leave residuals. Example: `<|eot_id|>` contains `<|eot` — first strip removes long form, second strip might find false positive. |
| **Impact** | Malformed JSON passed to parser, causing parse failures and fallbacks. |
| **Fix** | Use regex: `re.sub(r'<\|?(eot_id|end_of_text|eot)\|?>', '', content)`. |
| **Status** | PENDING |

---

### #15 — Work efficiency logged but never used
| | |
|---|---|
| **Location** | `npc_sim/simulation/simulation_manager.py:268-270` |
| **Issue** | `efficiency` variable computed and logged but never affects `WorkAction.execute()` output. Resource generation should scale with energy. |
| **Impact** | Work action produces same output regardless of NPC energy level. |
| **Fix** | Pass efficiency to WorkAction or compute resource generation in SimulationManager. |
| **Status** | PENDING |

---

## LOW (Cleanup / Polish)

### #16 — Dual-LLM pipeline documented but not implemented
| | |
|---|---|
| **Location** | `docs/architecture.md:157-383` |
| **Issue** | Architecture doc describes `DualLLMBackend` with Reasoner (3B) + Formatter (1B) components. No such class exists in `npc_sim/llm/`. Only `OllamaBackend` is implemented. |
| **Impact** | Contributors will be confused. Documentation credibility受损. |
| **Fix** | Either implement `DualLLMBackend` class OR remove/archive the Dual-LLM section with a note. |
| **Status** | PENDING |

---

### #17 — `llm_tick_every` config unused
| | |
|---|---|
| **Location** | `npc_sim/core/sim_config.py:64` |
| **Issue** | `llm_tick_every: int = 5` is set but never read. `LLMDecisionSystem` only fires on interrupt (H2). Per docs, tick counter was "deliberately removed". |
| **Impact** | Dead configuration. Confuses users expecting periodic LLM calls. |
| **Fix** | Remove config field or restore tick-based calling as optional mode. |
| **Status** | PENDING |

---

### #18 — Priority queue doesn't preempt in-flight requests
| | |
|---|---|
| **Location** | `npc_sim/llm/llm_request_queue.py:65-86` |
| **Issue** | `max_concurrent=1` means even `INTERRUPT` priority (0) waits for any in-flight request to complete. A `BACKGROUND` (10) request that started first blocks an interrupt. |
| **Impact** | High-priority interrupts delayed by low-priority background processing. |
| **Fix** | Implement preemption: cancel lowest-priority in-flight request when INTERRUPT arrives. |
| **Status** | PENDING |

---

### #19 — `FleeAction` lock duration = 0
| | |
|---|---|
| **Location** | `npc_sim/decisions/actions/builtin.py:153-156` |
| **Issue** | `min_duration_sim_seconds=0.0` means lock expires immediately. NPC flees one tick then re-evaluates. Defeats purpose of action locking for sustained fleeing behavior. |
| **Impact** | NPCs may freeze or oscillate between flee and other actions during danger. |
| **Fix** | Set reasonable duration (5-10 seconds) or use distance-based exit condition. |
| **Status** | PENDING |

---

### #20 — `_enforce_trait_coherence` only handles 2 cases
| | |
|---|---|
| **Location** | `npc_sim/llm/llm_decision_system.py:221-263` |
| **Issue** | Only `flee→attack` (Brave) and `attack→flee` (Pacifist) are handled. Docs mention `Devout→pray`, `Greedy→hoard`, `Aggressive→attack` but these aren't implemented. |
| **Impact** | Trait incoherence bugs for unhandled traits. |
| **Fix** | Add remaining trait coherence rules or remove from documentation. |
| **Status** | PENDING |

---

## Summary by Category

| Category | Count |
|----------|-------|
| CRITICAL | 5 |
| HIGH | 5 |
| MEDIUM | 5 |
| LOW | 5 |
| **Total** | **20** |

### By Module

| Module | Issues |
|--------|--------|
| `llm/` | 8 (#1, #2, #5, #6, #11, #14, #16, #18) |
| `decisions/` | 5 (#4, #7, #12, #13, #19) |
| `simulation/` | 2 (#3, #15) |
| `npc/` | 1 (#8) |
| `diagnostics/` | 1 (#10) |
| `core/` | 1 (#17) |
| Cross-module | 1 (#9, #20) |

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
