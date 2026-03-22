# Changelog

All notable changes to **NPC-Sim** are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

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
