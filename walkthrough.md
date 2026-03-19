# NPC-Sim — Walkthrough

## What Was Done

Converted the **ForgeProject.Sim** C# Unity package (49 source files, ~3,500 lines) into a standalone **Python simulation framework + local web dashboard**.

### Rebranding
- LICENSE → **Apache 2.0** under **Sadık Abdusselam Albayrak**
- Removed Unity artifacts: [package.json](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/package.json), [.meta](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/Runtime.meta) files, `Editor/` directory
- All `ForgeProject.Sim` references replaced with `npc_sim`

### Python Port — 31 Source Files

| Module | Files | Key Types |
|--------|-------|-----------|
| `npc_sim/core/` | 4 | SimVector3, SimRng, SimulationClock, SimulationConfig |
| `npc_sim/events/` | 2 | SimEvent, Stimulus + StimulusType enum |
| `npc_sim/npc/` | 12 | NPC, NPCFactory, Identity, Vitals, Psychology, Social, Memory, Beliefs, Goals, Traits, Inventory, Schedule |
| `npc_sim/perception/` | 4 | PerceptionSystem, SensorRange, PerceptionFilter, PerceivedObject |
| `npc_sim/decisions/` | 7 | IAction ABC, ActionContext, ActionLibrary, DecisionSystem, UtilityEvaluator, 11 built-in actions |
| `npc_sim/simulation/` | 6 | SimulationManager, SimWorldAdapter, StimulusDispatcher, FactionRegistry, PopulationStats, DictionaryGrid |

### Web Dashboard
- **Server**: Flask + Flask-SocketIO with background simulation thread
- **UI**: Dark-mode single-page dashboard with Inter font, glassmorphism, micro-animations
- **Features**: 2D map canvas, NPC list, detail panel (Big Five, vitals, inventory, traits), event log, speed/pause/reset controls, stimulus injection

## Verification

### Server Startup ✅
`python server.py` starts cleanly on port 5000.

### Browser Smoke Test ✅

````carousel
![Full dashboard with 10 NPC agents, world map, and population stats](C:/Users/Sadik/.gemini/antigravity/brain/3231c010-c1bc-4fa6-b670-e16bbe6aa98f/npc_sim_dashboard_full_1773877936114.png)
<!-- slide -->
![NPC detail panel showing Aldric's Big Five psychology, vitals, and emotions](C:/Users/Sadik/.gemini/antigravity/brain/3231c010-c1bc-4fa6-b670-e16bbe6aa98f/npc_detail_panel_1773877946503.png)
````

- ✅ 10 NPCs visible on canvas with color-coded occupation dots
- ✅ Real-time tick counter (Day 2, Tick 526+, Hour advancing)
- ✅ NPC list populated with mood and current action
- ✅ Detail panel: Identity, Vitals bars, Big Five traits, Emotions, Traits, Inventory
- ✅ Event log streaming events (Sleep, Gather, Work)
- ✅ Population stats (Hunger, Thirst, Happiness, Stress aggregates)

## How to Run the Simulation

```bash
cd d:\DeepLearning\Projects\NLP_ABM_Sim
python server.py
# Open http://localhost:5000
```

---

## LLM Integration (Phase 2)

### What Was Added

**6 new LLM modules** in `npc_sim/llm/`:

| File | Purpose |
|------|---------|
| `world_registry.py` | H1: coords → semantic zone labels (`MarketSquare`, `Tavern`, ...) |
| `npc_serializer.py` | Builds minified JSON payload for LLM (token-efficient) |
| `llm_backend.py` | `OllamaBackend` + `MockBackend` — local model API via `/api/chat` |
| `llm_request_queue.py` | H3: priority heap, caps concurrent workers, drops overflow silently |
| `llm_decision_system.py` | H2 interrupt + H4 guided retry + UtilityEvaluator fallback |
| `npc_serializer.py` | Full NPC state → minified JSON with zone, memories, beliefs, percepts |

**2 existing files extended:**
- `sim_config.py` — 10 new LLM fields (`llm_enabled`, `llm_backend`, `llm_model`, ...)
- `simulation_manager.py` — `enable_llm_for()`, `enable_llm_for_all()`, `get_llm_stats_full()`

**Upgraded dataset generator:** `Stateful_NPC/generator/npc_sim_generator_v2.py`
- Produces 20k training examples in Llama-3 instruct format
- Full NPC-Sim state: Big Five, 11 actions, zones, percepts, memories, beliefs, interrupt flag

**Data spec doc:** `llm_data_spec.md` — complete input/output schema reference

### 4 Hardening Mechanisms

| | Mechanism | Solution |
|-|-----------|----------|
| H1 | Semantik konum | `WorldRegistry` AABB zone lookup → `pos.zone`, `pos.landmark` |
| H2 | Event-driven interrupt | Threat≥0.8 veya HP drop≥15 → tick counter sıfırla, anında çağır |
| H3 | Priority queue | `LLMRequestQueue` heap: interrupt=0, focused=1, normal=5, bg=10 |
| H4 | Guided retry | Geçersiz action_id → düzeltici prompt, 1 kere tekrar; sonra fallback |

### Smoke Test Results ✅

```
[OK] LLM module imports
[OK] WorldRegistry: resolve(54.2,48.7) → {zone:MarketSquare, landmark:CentralFountain}
[OK] MockBackend
[OK] SimConfig LLM fields: backend=ollama model=npc-sim-decision:latest
[OK] SimulationManager LLM api: _LLM_AVAILABLE=True
[OK] Dataset generator v2: action=sleep emotion=Tired
All checks passed!
```

### Dataset Generator Usage

```bash
cd d:\DeepLearning\Projects\NLP_ABM_Sim\Stateful_NPC\generator
python npc_sim_generator_v2.py
# → data/train_v2.jsonl (20k examples, ~18MB)
# → data/test_v2.jsonl  (2k examples, ~1.8MB)
```

### Enabling LLM in Simulation (after model training)

```python
# In server.py / Python
mgr = SimulationManager(SimulationConfig(
    llm_enabled=True,
    llm_backend="ollama",
    llm_model="npc-sim-decision:latest",
    llm_tick_every=5,
))
mgr.enable_llm_for("npc_aldric_id")  # single NPC
mgr.enable_llm_for_all()             # all NPCs
```
