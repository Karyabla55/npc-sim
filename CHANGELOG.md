# Changelog

All notable changes to **NPC-Sim** are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

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
