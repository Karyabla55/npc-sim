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

# Long-run validation with invariant assertions every N ticks (default 1000):
python run_diagnostic.py --hours 720 --strict --strict-every 1000 --seed 42
# Exit code 2 + violation listing if any long-run invariant breaks.
```

### Smoke Tests
```bash
python test_llm_smoke.py
# Tests WorldRegistry, MockBackend, OllamaBackend, SimConfig, dataset generator
```

### pytest Suite
```bash
python -m pytest tests/ -q
# 76 cases as of v1.6.0 (inventory cap, dict eviction, multiplicative decay,
# CSV rotation, invariants, action wiring, trait coherence, queue preemption,
# config hygiene, DualLLMBackend chain + H6 fallback + npc_id injection)
```

### Install
```bash
pip install -r requirements.txt
# Optional dev deps: pip install -e ".[dev]"   # adds pytest, pytest-cov
```

There is no Makefile and no CI yet. `pyproject.toml` defines `pytest>=8.0` under `[dev]` extras; the suite lives under `tests/`.

## Architecture

### Two-Layer Decision Model

Every NPC tick runs both layers sequentially inside `SimulationManager.tick()`:

**Layer 1 — Utility AI** (`npc_sim/decisions/`): Pure math, runs every tick without LLM. `UtilityEvaluator` scores all 12 built-in actions and picks the highest. Trait modifiers adjust scores (e.g., `Brave` suppresses flee; `Pacifist` suppresses attack).

**Layer 2 — LLM Brain** (`npc_sim/llm/`): Fires only on interrupt (threat ≥ 0.8 or HP drop ≥ 15). Async — the simulation never blocks waiting for LLM. v1.6.0: **DualLLMBackend is fully implemented** — enable with `llm_backend="dual"` in `SimulationConfig`.

Dual-LLM split (v1.6.0+):
- **Reasoner** (Hermes-3-Llama-3.2-3B + LoRA r=16): receives persona card + NPC state JSON, outputs Turkish Chain-of-Thought (3-5 sentences)
- **Formatter** (Llama-3.2-1B-Instruct + LoRA r=8): receives CoT, outputs strict JSON `LLMResponse` with `action_id`, `target_id`, `dialogue`, `emotion`; `npc_id` injected at runtime by `DualLLMBackend`

The LLM result is applied on the *next* tick via `_apply_pending()`, not immediately.

### 5 LLM Hardening Mechanisms

| ID | Component | What It Does |
|----|-----------|--------------|
| H1 | `WorldRegistry` | Maps raw XY coordinates → zone labels (`MarketSquare`, `Tavern`, …) so the LLM sees meaningful location names |
| H2 | `LLMDecisionSystem._check_interrupt()` | Only fires LLM on threat ≥ 0.8 or HP drop ≥ 15 — prevents spam |
| H3 | `LLMRequestQueue` | Priority-based async queue (interrupt=0, normal=5, background=10); serial Ollama calls prevent VRAM saturation. v1.5.0+: an arriving INTERRUPT marks any in-flight lower-priority request `_cancelled` so its callback short-circuits to `(None, None)` instead of clobbering the interrupt path |
| H4 | `_guided_retry()` | Invalid `action_id` → one corrective prompt to Formatter only (not expensive Reasoner) |
| H5 | `_enforce_trait_coherence()` | Post-inference override. v1.5.0+ covers 5 named traits: `Brave`+low fear+high threat → `attack`; `Pacifist` → no-attack; `Coward`+threat≥0.5 → `flee`; `Greedy`+gold+valid trade → `trade`; `Devout`+stress≥0.6+valid pray → `pray` |

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
| `npc_sim/simulation/faction_registry.py` | Asymmetric inter-faction disposition matrix; cleanup threshold `0.01` (v1.5.0+) |
| `npc_sim/diagnostics/sim_logger.py` | Per-tick CSV logger (44 columns; zero-overhead when disabled). v1.5.0+: rotates `sim_full.csv` → `sim_full.NNNN.csv` every `rotate_every_rows=1_000_000` rows |
| `npc_sim/diagnostics/invariants.py` | Long-run safety net (v1.5.0+): `check_invariants(mgr) → list[InvariantViolation]` covering vital range/finiteness, dict caps, inventory cap, memory ring overflow. Wired into `run_diagnostic.py --strict` |
| `server.py` | Flask + SocketIO web dashboard |
| `run_diagnostic.py` | Headless runner for regression testing |
| `Stateful_NPC/generator/npc_sim_generator_v2.py` | Training data generator — wires decision_factors + persona_card + bootstrap_cot |
| `Stateful_NPC/generator/decision_factors.py` | Multi-factor decision model: `self_power` vs `perceived_threat` + `duty_pull` → 3-zone action label |
| `Stateful_NPC/generator/persona_card.py` | Turkish NPC identity preamble (2-3 sentences) prepended to Reasoner user turn |
| `Stateful_NPC/generator/bootstrap_cot.py` | Gemma 3 4B CoT bootstrap via Ollama + SHA-keyed disk cache |
| `notebooks/newgen-rpg.ipynb` | Kaggle-ready v5 training notebook (Reasoner + Formatter, packing=False, stress test) |

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
| `llm_backend` | `"ollama"` | `"ollama"` \| `"mock"` \| `"dual"` |
| `llm_model` | `"hermes-lora"` | Model name for `OllamaBackend` |
| `ollama_base_url` | `http://localhost:11434` | Ollama API (single-model backend) |
| `llm_reasoner_model` | `"reasoner-lora-v5"` | Reasoner model name (dual backend) |
| `llm_formatter_model` | `"formatter-lora-v5"` | Formatter model name (dual backend) |
| `llm_reasoner_base_url` | `http://localhost:11434` | Reasoner Ollama port |
| `llm_formatter_base_url` | `http://localhost:11435` | Formatter Ollama port |
| `llm_interrupt_threat_threshold` | 0.8 | H2 trigger |
| `llm_interrupt_hp_drop` | 15.0 | H2 trigger |
| `logger_enabled` | True | Writes `logs/sim_full.csv` |

## Critical Architecture Notes

### What Exists vs What's Integrated

The project has strong **data structures** with a **largely-wired integration layer**. As of v1.5.0, Memory/Beliefs/Goals/Social/Faction all influence at least one Utility AI action; the residual gaps are in higher-level systems (lifecycle, world events) deferred to v2.0+. See `docs/integration_map.md` for the full data-source → consumer matrix.

- `BeliefSystem` → consumed by `WalkToAction` (zone bias), `AttackAction` (target valence), `TradeAction` (target valence; success reinforces beliefs — B1), and `WorkAction` (workplace-safety belief about the home zone — B2) via `ActionContext.belief_score()`.
- `NPCGoals` → consumed by every survival/behaviour action via `ActionContext.goal_bonus()` (+0.25 when the related goal is active).
- `NPCMemory` → consumed by `WalkToAction` (zone threat bias via `get_memory_threat_bias()`). `SocializeAction.execute()` writes a `Dialogue` event into the listener's memory, carrying the LLM-authored line. `MemoryEntry.decay()` is multiplicative (v1.5.0+) so old salient memories preserve relative ordering forever.
- `NPCSocial.relations` → consumed by `SocializeAction.execute()` for trust-gated belief propagation (gossip retelling, attenuated valence/confidence). LRU-capped at 200 with `<0.05` magnitude prune (v1.5.0+).
- `NPCSocial.reputation` → consumed by `SocializeAction.evaluate()` (`+0.20 × (rep − 0.5)`) and `TradeAction.evaluate()` (`−0.30` when `rep < 0.3`) — B3.
- `FactionRegistry.disposition` → consumed by `AttackAction` (boosts attack on enemy factions, suppresses on allied) and `SocializeAction` (mirror weights) via `ActionContext.faction_disposition()` — B4.
- All five tracker polish bugs (#15, #16, #17, #18, #20) closed in v1.5.0; see `docs/bugs_and_issues.md`.

### LLM Trigger Conditions

LLM only fires on: `threat ≥ 0.8` OR `HP drop ≥ 15`. All other ticks use Utility AI. As of v1.4.0, `dialogue` output is propagated: `LLMDecisionSystem._apply_pending()` stores it on `NPC.pending_dialogue`, and `SocializeAction.execute()` consumes it and writes a `Dialogue` event into the listener's `NPCMemory`.

## Documentation

- `docs/llm_pipeline.md` — **Canonical v1.6.0 reference**: runtime architecture, training pipeline, schema, eval criteria, troubleshooting
- `docs/architecture.md` — v2.0 Dual-LLM architecture, tick flow, extension points, "What NOT to Do"
- `docs/llm_data_spec.md` — NPC JSON payload schema, Reasoner/Formatter data specs
- `docs/dataset_training.md` — Dataset generation pipeline and training targets
- `docs/bugs_and_issues.md` — Known issues and regression results (29 bugs tracked; all closed by v1.5.0)
- `docs/nextsteps.md` — **Yol haritası**: eksikler, v1.4/v1.5/v2.0/v3.0 görev listesi, LLM hedef şeması, dataset gereksinimleri
- `docs/psychology_model.md` — Vitals decay, stress balance, emotion cross-inhibition, mood label algorithm (v1.4.0+)
- `docs/integration_map.md` — Memory/Beliefs/Goals/Social/Traits → action consumer matrix (v1.4.0+)
- `docs/glossary.md` — Tüm kısaltmalar ve teknik terimler sözlüğü (Türkçe açıklamalı)
- `walkthrough.md` — Diagnostic session walkthroughs (v1.0.1 + v1.2.0)
- `CHANGELOG.md` — Per-version history

## LLM Setup (Ollama)

The Ollama server must be running locally at `http://localhost:11434` before enabling `llm_enabled=True`. The default model name `hermes-lora` refers to a custom fine-tuned model. Use `llm_backend="mock"` in `SimulationConfig` for offline development/testing.

For `DualLLMBackend` (v1.6.0+): two Ollama instances are needed (ports 11434 + 11435). Set `llm_backend="dual"` in `SimulationConfig`. See `docs/llm_pipeline.md` §3 for Kaggle training + Ollama deployment steps.

## Log Analysis

To analyze `logs/sim_full.csv` interactively, open the Jupyter notebook:

```bash
jupyter notebook notebooks/log_analysis.ipynb
```

The notebook covers 9 sections: quick overview (shape, NPCs, zones), vital trends, emotion tracking, action distribution, LLM call stats, zone/movement scatter, inventory over time, events & deaths, and a per-NPC summary table. Re-run **Cell 2** after each new diagnostic run to reload fresh data.
