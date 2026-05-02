# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

NPC-Sim is a deterministic, civilization-scale NPC simulation framework for RPG AI research. NPCs have full cognitive state (vitals, psychology, memory, beliefs, goals, traits, inventory) and make decisions via two co-existing layers: a pure-math Utility AI (runs every tick) and an LLM brain (fires only on interrupt via Ollama). Same seed + same config always produces an identical replay.

## Commands

### Run the Web Dashboard
```bash
python server.py
# Opens http://localhost:5000
```

### Headless Diagnostic Run (6 sim-hours, 5 archetypal NPCs)
```bash
python run_diagnostic.py [--hours 6.0] [--speed 1.0] [--seed 42] [--npc-count 5]
# Outputs: logs/sim_full.csv (44 columns, 1 row per NPC per tick)
```

### Smoke Tests
```bash
python test_llm_smoke.py
# Tests WorldRegistry, MockBackend, OllamaBackend, SimConfig, dataset generator
```

### Install
```bash
pip install -r requirements.txt
# Optional dev deps: pip install -e ".[dev]"
```

There is no Makefile, no CI, and no pytest suite yet. `pyproject.toml` defines optional `pytest>=8.0` deps but no tests use it.

## Architecture

### Two-Layer Decision Model

Every NPC tick runs both layers sequentially inside `SimulationManager.tick()`:

**Layer 1 — Utility AI** (`npc_sim/decisions/`): Pure math, runs every tick without LLM. `UtilityEvaluator` scores all 12 built-in actions and picks the highest. Trait modifiers adjust scores (e.g., `Brave` suppresses flee; `Pacifist` suppresses attack).

**Layer 2 — LLM Brain** (`npc_sim/llm/`): Fires only on interrupt (threat ≥ 0.8 or HP drop ≥ 15). Async — the simulation never blocks waiting for LLM. Uses a **Dual-LLM pipeline** in v1.1.0+:
- **Reasoner** (3B Llama 3.2): receives full NPC state JSON, outputs Turkish Chain-of-Thought
- **Formatter** (1B Llama 3.2): receives CoT, outputs strict JSON `LLMResponse` with `action_id`, `target_id`, `dialogue`, `emotion`

The LLM result is applied on the *next* tick via `_apply_pending()`, not immediately.

### 5 LLM Hardening Mechanisms

| ID | Component | What It Does |
|----|-----------|--------------|
| H1 | `WorldRegistry` | Maps raw XY coordinates → zone labels (`MarketSquare`, `Tavern`, …) so the LLM sees meaningful location names |
| H2 | `LLMDecisionSystem._check_interrupt()` | Only fires LLM on threat ≥ 0.8 or HP drop ≥ 15 — prevents spam |
| H3 | `LLMRequestQueue` | Priority-based async queue (interrupt=0, normal=5, background=10); serial Ollama calls prevent VRAM saturation |
| H4 | `_guided_retry()` | Invalid `action_id` → one corrective prompt to Formatter only (not expensive Reasoner) |
| H5 | `_enforce_trait_coherence()` | Post-inference override: `Brave`+low fear+high threat → `attack`; `Pacifist` → no-attack |

### Tick Execution Order (per `SimulationManager.tick()`)

```
StimulusDispatcher.dispatch()            ← broadcast pending events
FactionRegistry.tick_decay()             ← decay faction trust
[for each NPC in deterministic order]
├── PerceptionSystem.tick()              ← update active_percepts
├── NPC.tick()                           ← decay vitals + emotions
├── NPC.refresh_need_goals()             ← need pipeline → goal objects
├── LLMDecisionSystem.tick() or DecisionSystem.tick()
│   ├── _check_interrupt()               ← H2 guard
│   ├── _apply_pending()                 ← apply previous async LLM result (H5 here)
│   ├── _fire_llm_call()                 ← async via H3 queue (H1 inside serializer)
│   └── _utility_fallback()             ← Utility AI while LLM is in flight
└── SimLogger.log_npc_tick()             ← CSV row
```

### Key Module Map

| Module | Role |
|--------|------|
| `npc_sim/npc/npc.py` | NPC container — aggregates all 10 subsystems |
| `npc_sim/npc/vitals.py` | HP, hunger, thirst, energy, stress |
| `npc_sim/npc/psychology.py` | Big Five traits + emotions (fear, happiness, anger) |
| `npc_sim/npc/memory.py` | Episodic memory (O(1) circular ring buffer) |
| `npc_sim/npc/traits.py` | Named traits (Brave, Coward, Greedy, Devout, Pacifist, …) |
| `npc_sim/decisions/actions/builtin.py` | All 12 actions — each has `is_valid()`, `evaluate()`, `execute()` |
| `npc_sim/decisions/action_context.py` | Immutable per-tick snapshot passed to every action |
| `npc_sim/llm/llm_decision_system.py` | LLM brain layer with all 5 hardening mechanisms |
| `npc_sim/llm/llm_backend.py` | `OllamaBackend`, `MockBackend`, `DualLLMBackend` |
| `npc_sim/llm/npc_serializer.py` | NPC state → minified JSON payload for Ollama |
| `npc_sim/simulation/simulation_manager.py` | Top-level tick orchestrator |
| `npc_sim/simulation/world_map.py` | 10 zones + named landmarks |
| `npc_sim/simulation/spatial_grid.py` | `DictionaryGrid` — O(1) coordinate → NPC lookups |
| `npc_sim/simulation/faction_registry.py` | Asymmetric inter-faction disposition matrix |
| `npc_sim/diagnostics/sim_logger.py` | Per-tick CSV logger (44 columns; zero-overhead when disabled) |
| `server.py` | Flask + SocketIO web dashboard |
| `run_diagnostic.py` | Headless runner for regression testing |
| `Stateful_NPC/generator/npc_sim_generator_v2.py` | Training data generator (CoT + JSON pairs) |

### The 12 Built-in Actions

`eat`, `drink`, `sleep`, `flee`, `gather`, `heal`, `attack`, `socialize`, `trade`, `work`, `pray`, `walk_to` — all in `npc_sim/decisions/actions/builtin.py`. Each action scores itself in `evaluate()` using the immutable `ActionContext`; the highest score wins.

### Determinism

All randomness flows through `SimRng` (wraps `random.Random` with a seeded constructor). No global random state. Same seed → identical replay.

## SimulationConfig Defaults (`npc_sim/core/sim_config.py`)

| Key | Default | Notes |
|-----|---------|-------|
| `seed` | 42 | RNG seed |
| `tick_rate` | 10.0 | Ticks/real-second |
| `day_length_seconds` | 1440.0 | 1 sim-day |
| `llm_enabled` | False | Requires Ollama running |
| `llm_model` | `"hermes-lora"` | Fine-tuned model name |
| `ollama_base_url` | `http://localhost:11434` | Ollama API |
| `llm_interrupt_threat_threshold` | 0.8 | H2 trigger |
| `llm_interrupt_hp_drop` | 15.0 | H2 trigger |
| `logger_enabled` | True | Writes `logs/sim_full.csv` |

## Critical Architecture Notes

### What Exists vs What's Integrated

The project has strong **data structures** but a partial **integration layer**. Key gap: Goals, Beliefs, Memory, and Social Relations are stored correctly but do **not** currently influence Utility AI action scoring. They are only visible to the LLM via `NPCSerializer`.

- `BeliefSystem` → stored, decayed, but no action reads beliefs
- `NPCGoals` → stored, but action `is_valid()`/`evaluate()` never queries the goal stack
- `NPCMemory` → stored, sent to LLM payload (top 3 salient), but Utility AI ignores it
- `NPCSocial` → stored, but `SocializeAction` doesn't use trust/affinity in scoring

### DualLLMBackend Status

**`DualLLMBackend` is documented in `docs/llm_data_spec.md` and `docs/architecture.md` but does NOT exist in code.** Only `OllamaBackend` (single model) and `MockBackend` are implemented. The CLAUDE.md reference to "Dual-LLM pipeline" in the architecture section describes the intended design, not the current implementation.

### LLM Trigger Conditions

LLM only fires on: `threat ≥ 0.8` OR `HP drop ≥ 15`. All other ticks use Utility AI. `dialogue` output from LLM is generated but currently not propagated to the target NPC.

## Documentation

- `docs/architecture.md` — v2.0 Dual-LLM architecture, tick flow, extension points, "What NOT to Do"
- `docs/llm_data_spec.md` — NPC JSON payload schema, Reasoner/Formatter data specs
- `docs/dataset_training.md` — Dataset generation pipeline and training targets
- `docs/bugs_and_issues.md` — Known issues and regression results (20 bugs, 8 fixed in v1.2.0)
- `docs/nextsteps.md` — **Yol haritası**: eksikler, v1.3/v2.0/v3.0 görev listesi, LLM hedef şeması, dataset gereksinimleri
- `walkthrough.md` — Diagnostic session walkthroughs (v1.0.1 + v1.2.0)
- `CHANGELOG.md` — Per-version history

## LLM Setup (Ollama)

The Ollama server must be running locally at `http://localhost:11434` before enabling `llm_enabled=True`. The default model name `hermes-lora` refers to a custom fine-tuned model. Use `llm_backend="mock"` in `SimulationConfig` for offline development/testing.

For the planned `DualLLMBackend`: two Ollama instances are needed (ports 11434 + 11435). See `docs/nextsteps.md` Section 6 for the implementation sketch.
