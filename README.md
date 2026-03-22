# NPC-Sim

**`npc_sim` · Version 1.0.1 · Python 3.10+**

> A **deterministic, civilization-scale NPC simulation framework** — originally conceived as a Unity package, now a fully standalone Python system with a local web dashboard and LLM-driven autonomous agent support.
>
> Designed for deep RPG AI research, emergent city-scale behavior, and as a foundation for Q1-level academic publication.
> **Author:** Sadık Abdusselam Albayrak · **License:** Apache 2.0

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)

---

## Quick Start

```bash
pip install flask flask-socketio simple-websocket
python server.py
# Open http://localhost:5000

# Run headless 6-hour diagnostic (no Flask, no browser required)
python run_diagnostic.py
# → logs/sim_full.csv  (per-tick CSV log)
```

---

## Features

### 🧠 Cognitive NPC Architecture
- **Big Five Psychology** — Extraversion, Agreeableness, Conscientiousness, Neuroticism, Openness
- **Utility-Based AI** — actions score themselves against NPC state; highest scorer wins
- **LLM Decision Engine** — drop-in replacement for the utility evaluator; locally hosted custom model via Ollama
- **Goal System** — need-driven pipeline converts hunger/thirst/fatigue into prioritised goals
- **Episodic Memory** — O(1) circular ring buffer; most salient memories feed LLM context
- **Belief System** — NPCs hold world beliefs updated by witnessed events
- **Trait System** — named traits (Brave, Greedy, Devout…) modify action weights

### 🌍 Civilization Systems
- **Inventory** — slot-based item system (food, water, medicine, gold, grain, tools, weapons)
- **Daily Schedules** — work/sleep/social hours per occupation archetype
- **Factions** — asymmetric inter-faction disposition matrix with time-decay
- **Population Stats** — per-tick aggregate metrics (health, hunger, happiness, famine/war flags)

### 👁️ Perception
- **Multi-channel sensors** — Visual / Audio / Social with per-archetype range presets
- **Field-of-View** — directional cone filtering on visual stimuli
- **Salience evaluation** — psychology-aware attention (stressed NPCs prioritise threats)
- **Percept expiry** — stale percepts automatically pruned

### 🤖 LLM Integration (4 hardening mechanisms)
| | Mechanism | Implementation |
|-|-----------|---------------|
| H1 | Semantic spatial context | `WorldRegistry` maps coordinates → zone labels (`MarketSquare`, `Tavern`, …) |
| H2 | Event-driven interrupt | Threat ≥ 0.8 or HP drop ≥ 15 → LLM called immediately, bypassing tick counter |
| H3 | Priority request queue | `LLMRequestQueue` — interrupt=0, focused=1, normal=5, background=10; serial Ollama |
| H4 | Guided retry | Invalid `action_id` → one corrective prompt before fallback to `UtilityEvaluator` |

### 🌐 Web Dashboard
- Real-time 2D spatial map with colour-coded NPC dots
- NPC detail panel: vitals, Big Five, emotions, inventory, memories
- Live event log, population stats, speed controls
- LLM inner monologue display, speech bubbles, stats badge

### ⚡ Performance & Determinism
- Same seed + same config → identical replay
- Seeded `SimRng` (wraps `random.Random`)
- `DictionaryGrid` for O(1) spatial queries

---

## Project Structure

```
npc_sim/
├── core/          SimVector3, SimRng, SimulationClock, SimulationConfig
├── events/        SimEvent, Stimulus
├── npc/           NPC, NPCFactory + 10 subsystems (vitals, psychology, memory, …)
├── perception/    PerceptionSystem, SensorRange, PerceptionFilter
├── decisions/     DecisionSystem, UtilityEvaluator, ActionLibrary + 12 built-in actions
├── diagnostics/   SimLogger (per-tick CSV), VitalThresholdTracker
├── simulation/    SimulationManager, SimWorldAdapter, StimulusDispatcher, …
└── llm/           WorldRegistry, NPCSerializer, OllamaBackend, LLMRequestQueue,
                   LLMDecisionSystem

Stateful_NPC/
├── generator/     npc_sim_generator_v2.py  (upgraded dataset generator)
│                  config.py, npc_state_machine.py  (original v6 generator)
└── data/          train_v2.jsonl (~14 MB, 20k examples)
                   test_v2.jsonl  (~4 MB, 2k examples)

server.py          Flask + SocketIO backend
run_diagnostic.py  Headless 6-hour sim runner + CSV log analyser
logs/              sim_full.csv  (per-tick NPC diagnostic log, one row per NPC per tick)
static/            index.html, style.css, app.js  (web dashboard)
```

---

## Built-in Actions (11)

| `action_id` | Category | Behaviour |
|-------------|---------|-----------|
| `eat` | Survival | Eats from inventory; scores quadratically on hunger with urgency multiplier |
| `drink` | Survival | Drinks water from inventory; scores quadratically on thirst with urgency multiplier |
| `sleep` | Survival | Restores energy when low; blocked when starving or critically thirsty |
| `flee` | Safety | Moves NPC away from highest-threat percept |
| `gather` | Survival | Harvests food/water based on need urgency; capped at 5 items per resource |
| `heal` | Health | Consumes medicine; reduces fear |
| `attack` | Combat | Melee damage + belief propagation + reputation penalty |
| `socialize` | Social | Trust/affinity gain; gossips salient memory to ally |
| `trade` | Economy | Gold ↔ food exchange; both parties gain trust |
| `work` | Economy | Occupation-specific resource generation |
| `pray` | Spiritual | Stress relief; emits Prayer social stimulus |
| `walk_to` | Navigation | Goal-aware NPC movement; directed toward percepts when lacking resources |

---

## LLM Integration

The `LLMDecisionSystem` replaces `DecisionSystem` per-NPC:

```python
from npc_sim.core.sim_config import SimulationConfig
from npc_sim.simulation.simulation_manager import SimulationManager

mgr = SimulationManager(SimulationConfig(
    llm_backend="ollama",
    llm_model="npc-sim-decision:latest",  # your fine-tuned model
    llm_tick_every=5,
))
mgr.enable_llm_for_all()   # or enable_llm_for("npc_id")
```

See [`docs/llm_data_spec.md`](docs/llm_data_spec.md) for the full input/output schema.

### Training Data

Generate v2 dataset (Big Five + all 11 actions + zone labels + memories):

```bash
cd Stateful_NPC/generator
python npc_sim_generator_v2.py
# → data/train_v2.jsonl  (20k examples)
# → data/test_v2.jsonl   (2k examples)
```

---

## Architecture

```
SimulationManager.tick()
├── StimulusDispatcher.dispatch()
├── FactionRegistry.tick_decay()
└── [per NPC, deterministic order]
    ├── PerceptionSystem.tick()      → active_percepts
    ├── NPC.tick()                   → vitals/emotions decay
    ├── NPC.refresh_need_goals()     → need → goal pipeline (stale goals pruned)
    ├── LLMDecisionSystem.tick()     → action selection
    │   ├── [H2] interrupt check
    │   ├── NPCSerializer.build_payload()
    │   ├── LLMRequestQueue.submit()
    │   │    └── OllamaBackend.call() → LLMResponse
    │   │         └── [H4] guided retry on invalid action_id
    │   └── fallback: UtilityEvaluator
    └── SimLogger.log_npc_tick()     → logs/sim_full.csv (one row per NPC per tick)
```

---

## Research & Publications

This project is intended as an open-source foundation for agent-based modelling (ABM) research. Planned contributions:
- Deterministic reproducible simulation environment
- LLM-as-cognitive-agent benchmark dataset (`train_v2.jsonl`)
- Evaluation metrics: action validity ≥ 98%, fallback rate ≤ 5%, interrupt accuracy ≥ 85%

---

## License

Licensed under the **Apache License, Version 2.0**.
Copyright 2025-2026 **Sadık Abdusselam Albayrak**

See [LICENSE](LICENSE) for the full text.
