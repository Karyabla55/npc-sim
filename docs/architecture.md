# NPC-Sim Architecture Reference

**Version:** 1.0.3 · **Author:** Sadık Abdusselam Albayrak · **License:** Apache 2.0

This document is the authoritative reference for contributors extending the simulation. Read this before modifying any decision-system code.

---

## Extension Points — Quick Reference

If you are new to the codebase, start here. The table below tells you exactly where to add code for common extension scenarios.

| What you want to add | Where to change | What NOT to touch |
|---|---|---|
| New trigger for LLM brain (e.g. social encounter) | `LLMDecisionSystem._check_interrupt()` only | Any other call site |
| New interrupt priority level | `LLMRequestQueue.Priority` + `LLMDecisionSystem._compute_priority()` | `LLMRequestQueue` internals |
| Extra context for LLM (new JSON fields) | `NPCSerializer._build_dict()` | Prompt formatting code |
| New action | `builtin.py` (new class) + `ActionLibrary` registration | `DecisionSystem`, `UtilityEvaluator`, `LLMDecisionSystem` |
| New post-inference validation rule | `LLMDecisionSystem._enforce_trait_coherence()` | `_apply_pending()` logic flow |
| New NPC psychological trait | `NPCTraits` + `get_weight_modifier()` + training data | Core action ontology |

---

## Two-Layer Decision Model

The simulation runs on two co-existing layers that mirror how real decision-making works.

**Layer 1 — Utility AI (autopilot):** `DecisionSystem` + `UtilityEvaluator` + builtin actions. Runs every simulation tick. Pure math, no LLM. Handles routine behaviour: eating, sleeping, working, wandering. This is the NPC's "autopilot" — just as humans navigate familiar environments without consciously deliberating, NPCs follow utility scores for ordinary moments.

**Layer 2 — LLM Brain (deliberation):** `LLMDecisionSystem` fires an async LLM call **only on interrupt**. The LLM receives the NPC's full cognitive state (traits, memories, beliefs, emotions, percepts) and returns a deliberate decision. This captures the moments when humans *do* stop and think — unexpected threats, social encounters, moral crises.

Crucially, the utility AI keeps running while the LLM call is in flight (`_utility_fallback()`), so the NPC never freezes. The LLM result is applied on the next tick via `_apply_pending()`. This design preserves both responsiveness and deliberate intelligence.

---

## Tick Flow

The following sequence describes what happens each simulation tick, in execution order:

```
SimulationManager.tick()
├── StimulusDispatcher.dispatch()          # broadcast pending events to NPCs
├── FactionRegistry.tick_decay()           # decay faction trust over time
└── [per NPC, deterministic order]
    ├── PerceptionSystem.tick()            # update active_percepts list
    ├── NPC.tick()                         # decay vitals, emotions (decay_emotions)
    ├── NPC.refresh_need_goals()           # need pipeline → goal objects (prune stale)
    ├── LLMDecisionSystem.tick()           # action selection
    │   ├── [H2] _check_interrupt()        # fear spike + LLM trigger test
    │   ├── _apply_pending()               # apply previous async LLM result
    │   │    └── [H5] _enforce_trait_coherence()  # Brave/Pacifist guard
    │   ├── _fire_llm_call()               # queue async call if triggered
    │   │    └── LLMRequestQueue → OllamaBackend.call() → LLMResponse
    │   │         └── [H4] _guided_retry() on invalid action_id
    │   └── _utility_fallback()            # UtilityEvaluator while LLM in flight
    └── SimLogger.log_npc_tick()           # logs/sim_full.csv
```

Each NPC processes its own `ActionContext` — an immutable snapshot of percepts, vitals, goals, and world references valid for that tick.

---

## Interrupt System

`LLMDecisionSystem._check_interrupt()` is the **only** place in the codebase that decides when the LLM brain activates. It must stay as the single entry point.

**Current triggers:**

```python
# 1. High-threat stimulus
threat = ctx.get_top_percept("Threat")
if threat and threat.threat_level >= self._interrupt_threat:   # default 0.8
    # side effect: fear spike proportional to threat × neuroticism
    return True

# 2. Sudden HP drop (took significant damage since last tick)
if self._last_hp > 0 and (self._last_hp - health) >= self._interrupt_hp_drop:   # default 15
    return True
```

**Designed extension triggers** (add here, nowhere else):

```python
# Social encounter — NPC sees another NPC → deliberate response
# if ctx.has_percept("NPC") or ctx.has_percept("Ally"):
#     return True

# Vital crisis — desperation overrides routine
# if ctx.self_npc.vitals.hunger > 0.92 or ctx.self_npc.vitals.thirst > 0.92:
#     return True

# Disaster memory — high-salience negative event triggers deliberation
# recent = ctx.self_npc.memory.get_recent(ctx.current_time, window_seconds=60)
# if any(m.emotional_weight < -0.7 for m in recent):
#     return True

# Acute stress spike — trauma response
# if ctx.self_npc.vitals.stress > 0.85:
#     return True
```

Each commented block represents a distinct human decision pattern. Add priority assignments in `_compute_priority()` alongside any new trigger.

---

## Action Contract

Every `IAction` subclass must implement three methods. The contract is strict.

| Method | Signature | Responsibility |
|--------|-----------|----------------|
| `is_valid` | `(ctx: ActionContext) -> bool` | Returns `True` if this action is currently possible. Gates entry into scoring. Must be side-effect-free. |
| `evaluate` | `(ctx: ActionContext) -> float` | Returns a normalised score `[0.0, 1.0]` for how desirable this action is right now. **Must never mutate state**. Side effects belong only in `execute()`. |
| `execute` | `(ctx: ActionContext) -> None` | Carries out the action: modifies NPC state, publishes events, moves NPCs. Only called once per tick for the winning action. |

`evaluate()` must return values strictly within `[0.0, 1.0]`. Use `max(0.0, min(raw, 1.0))` to clamp. Returning values above 1.0 breaks the utility comparator.

`UtilityEvaluator.evaluate()` multiplies the action's raw score by `traits.get_weight_modifier(action_type)`, so trait modifiers are automatically applied without any action needing to call `get_weight_modifier()` manually — unless the action wants to apply modifiers internally for subtle effects (e.g. `AttackAction` applies a Brave courage boost inside `evaluate()` before the evaluator's trait multiplier).

---

## Hardening Mechanisms (H1–H5)

| ID | Name | Location | Purpose |
|----|------|----------|---------|
| H1 | Semantic spatial context | `NPCSerializer._build_dict()` | Maps raw coordinates → zone labels for LLM clarity |
| H2 | Event-driven interrupt | `LLMDecisionSystem._check_interrupt()` | Triggers LLM only on significant events |
| H3 | Priority request queue | `LLMRequestQueue` | Prevents VRAM saturation; serial Ollama inference |
| H4 | Guided retry | `LLMDecisionSystem._guided_retry()` | Recovers from invalid `action_id` with one corrective re-prompt |
| H5 | Trait coherence guard | `LLMDecisionSystem._enforce_trait_coherence()` | Post-inference override for logical contradictions (Brave→attack, Pacifist→no-attack) |

---

## What NOT To Do

The following patterns will break the simulation or destroy real-time performance. They are listed here explicitly to prevent well-intentioned but destructive changes.

**Do not call the LLM from anywhere except `_check_interrupt()`.**  
Adding an LLM call inside `DecisionSystem.tick()`, an action's `execute()`, or any event handler will flood the queue and bypass the priority system. All LLM activation goes through `_check_interrupt()`.

**Do not make `_should_call_llm()` time-based (e.g. "call every N ticks").**  
The tick-counter path was deliberately removed. Interrupt-only is the correct model — it fires when something meaningful happens, not on a metronome. Restoring a tick counter causes gratuitous LLM calls during quiet simulation periods.

**Do not apply LLM results synchronously inside the response callback.**  
`_on_response()` runs on the worker thread. Applying the action there would race with the simulation tick. The result is stored in `_pending_response` and applied next tick via `_apply_pending()`. This is intentional.

**Do not introduce `asyncio`.**  
`LLMRequestQueue` uses a `threading.Thread` + `threading.Lock` concurrency model intentionally. Mixing `asyncio` into the simulation tick loop (which runs in Flask's thread) would require an event loop bridge and create subtle deadlocks in the priority queue.

**Do not put side effects in `evaluate()`.**  
`evaluate()` is called for *every* action every tick. Side effects there would fire 12+ times per tick per NPC. All state mutations belong in `execute()`, which is called for the winning action only.

---

---

# Architecture v2.0 — Dual-LLM Cognitive Motor Pipeline

**Added:** 2026-04-20 · **Status:** Active

## Motivation

The monolithic `OllamaBackend` was simultaneously responsible for NPC *reasoning* (why act?) and output *formatting* (produce valid JSON). These goals require conflicting fine-tuning signals: expressive Chain-of-Thought training loosens schema adherence; strict JSON training suppresses reasoning depth. The observable failure mode was correct state payloads producing behaviourally inert decisions.

The fix is separation of concerns across two independently trainable models.

---

## High-Level Flow

```
NPC State JSON
      │
      ▼
┌─────────────────────────────────────────┐
│  Component A — Logic Node (Reasoner)    │  ← Llama 3.2 3B, fine-tuned on Turkish CoT
│  Input : full NPC state JSON            │
│  Output: Turkish first-person rationale │
│  e.g.  "Canım kritik ve açım.           │
│          İlk önce kendimi iyileştirip   │
│          sonra yiyecek aramalıyım."     │
└────────────────┬────────────────────────┘
                 │ plain Turkish text
                 ▼
┌─────────────────────────────────────────┐
│  Component B — Translation Node         │  ← Llama 3.2 1B, GGUF Q4_K_M
│               (Formatter)              │
│  Input : Component A text              │
│  Output: strictly typed JSON           │
│  e.g.  {"action_id": "heal",           │
│          "target_id": null,            │
│          "dialogue": null,             │
│          "emotion": "Fearful"}         │
└────────────────┬────────────────────────┘
                 │ LLMResponse
                 ▼
         _apply_pending()   ← unchanged
         _enforce_trait_coherence() (H5) ← unchanged
```

---

## Deployment: Asymmetric Dual-Process

Two separate Ollama processes on different ports. Process A hosts the 3B Reasoner; Process B hosts the 1B Formatter.

**Why asymmetric:** Game runtime (Unity or other engine) already consumes significant VRAM for rendering. Keeping the Formatter at 1B / Q4_K_M (~0.6 GB VRAM) ensures the total LLM footprint stays within budget: ~2.0 GB (3B Q4) + ~0.6 GB (1B Q4) = **≈2.6 GB combined**.

**Concurrency pattern:** Component A and Component B run on separate processes but are called sequentially inside the single `LLMRequestQueue` worker thread. This means:
- While tick N's Reasoner call runs on Process A, Process B idles (no wasted inference).
- On completion, the same worker immediately calls Process B — no thread switch overhead.
- The existing `max_concurrent=1` serial model is preserved.

**Configuration:**
```python
# SimulationConfig additions
llm_reasoner_url  : str  = "http://localhost:11434"   # Ollama process A
llm_reasoner_model: str  = "llama3.2-3b-npc-cot"     # fine-tuned CoT checkpoint
llm_formatter_url : str  = "http://localhost:11435"   # Ollama process B
llm_formatter_model: str = "llama3.2-1b-npc-fmt"     # fine-tuned formatter checkpoint
```

> **Never** load both models into the same Ollama process. Concurrent model switching in Ollama requires a full model unload/reload and will stall the queue for 5–15 seconds.

---

## Component A — Logic Node (Reasoner)

| Property | Value |
|---|---|
| Base model | Llama 3.2 3B Instruct |
| Quantization | GGUF Q4_K_M (~2.0 GB VRAM) |
| Training objective | Turkish Chain-of-Thought fine-tuning |
| Training corpus | `train_reasoner.jsonl` — CoT-expanded examples (see Data section) |
| Input | Minified NPC state JSON (same payload as current `OllamaBackend`) |
| Output | Turkish first-person internal monologue, 3–5 sentences |
| Schema awareness | None — explicitly ignores `action_id`, `valid_actions` |
| Inference speed | ~40–60 tok/s on RTX 3060 @ Q4 |

**System prompt (Turkish, consistent with training data):**
```
Sen bir ortaçağ simülasyonundaki NPC'nin iç ses motorusun.
Sana NPC'nin anlık durumunu JSON olarak göndereceğim.
Görevin: NPC'nin ne yapması gerektiğini ve NEDEN yapması gerektiğini
3-5 cümlelik Türkçe iç monolog olarak yaz.
ASLA JSON üretme. ASLA action_id adı kullanma. Sadece düşün.
Kişilik özellikleri, hayatta kalma ihtiyaçları, tehdit algısı,
duygusal durum, hafıza ve sosyal bağlamı değerlendir.
```

**Training data format** (`train_reasoner.jsonl`):
```jsonl
{"text": "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{npc_state_json}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n{cot_reasoning}<|eot_id|>"}
```

---

## Component B — Translation Node (Formatter)

| Property | Value |
|---|---|
| Base model | Llama 3.2 1B Instruct |
| Quantization | GGUF Q4_K_M (~0.6 GB VRAM) |
| Training objective | Turkish NL → strict JSON extraction |
| Training corpus | `train_formatter.jsonl` — (cot_reasoning, json_output) pairs + paraphrase augmentation |
| Input | Component A's Turkish text output |
| Output | Strictly typed `LLMResponse` JSON |
| Context window used | ~100–250 tokens (tiny — reasoning string only) |
| Inference speed | ~80–120 tok/s on RTX 3060 @ Q4 — well under 1 second |

**System prompt:**
```
Sen bir NPC simülasyonu için JSON dönüştürücüsün.
Sana bir NPC'nin ne yapmak istediğini Türkçe olarak anlatacağım.
Bunu aşağıdaki JSON şemasına dönüştür:
{"npc_id":"<string>","reasoning":"<girdiyi kopyala>",
 "selected_action":{"action_id":"<listeden>","target_id":null,"dialogue":null},
 "emotion":"<tek kelime>"}
valid_actions: ["eat","drink","sleep","flee","gather","heal","attack","socialize","trade","work","pray","walk_to"]
SADECE JSON yaz. Kod bloğu veya açıklama ekleme.
```

**Robustness:** Component B is trained on paraphrase-augmented data so it tolerates imperfect phrasing from Component A (incomplete sentences, synonym variation, word order changes). Paraphrase augmentation target: **15–20% of training examples**.

**H4 retry applies to Component B only.** If `json.loads()` fails, `_guided_retry()` sends a corrective reprompt to the Formatter (cheap) — not back through the expensive Reasoner.

---

## Data Pipeline — v2 Corpus Generation

### Reasoner Corpus (`train_reasoner.jsonl`)

Generated by the updated `npc_sim_generator_v2.py`. Key additions over v1:

**`cot_reasoning` field** — 3–5 sentence Turkish expansion of the existing `reasoning` field. Each sentence covers one cognitive layer:
1. Primary need / threat assessment
2. Alternative consideration ("Bunu yapmak yerine X de yapabilirdim, ancak...")
3. Trait / emotion influence ("Kişiliğim beni / ruh halim beni...")
4. Final decision rationale ("Bu yüzden...")
5. Memory influence if applicable ("Daha önce yaşadıklarım bana gösteriyor ki...")

**New deviation cases (D5–D8):**

| Case | Trigger | Action | CoT rationale |
|------|---------|--------|---------------|
| D5 | `hp < 30` AND `hunger > 0.70` AND medicine in inv | `heal` | Dual-crisis: explains why HP beats hunger |
| D6 | arch=`Brave` AND `fear > 0.55` | `attack` | Conflicted courage: fear acknowledged, duty wins |
| D7 | `sched=work` AND `energy < 0.30` | `sleep` | Schedule override: body limits override duty |
| D8 | memory `ew < -0.7` for a percept entity | `flee` | Trauma response: past experience overrides current bravery |

**Updated oversampling:**
- `Brave × threat ≥ 0.7` → 3× (existing)
- `Fearful × social` → 2× (new — underrepresented social-anxiety case)
- `Honorable × attack-trigger` → 2× (new — morally complex self-defence case)

**Target counts:** 20,000 train / 2,000 test.

### Formatter Corpus (`train_formatter.jsonl`)

Auto-derived from the Reasoner corpus:
- **Input:** `cot_reasoning` field (or `reasoning` when CoT not available)
- **Output:** existing `json_output` block (`action_id`, `target_id`, `dialogue`, `emotion`)
- **Paraphrase augmentation:** 15–20% of examples are re-emitted with lightweight Turkish synonym substitution and sentence boundary variation. This teaches the Formatter to handle imperfect Reasoner output without JSON parse errors.

No new state generation needed — the Formatter corpus is fully derived. Size ≈ 23,000–24,000 examples after augmentation.

---

## Updated Hardening Mechanisms Table

| ID | Name | Location | Purpose | v2 Status |
|----|------|----------|---------|-----------|
| H1 | Semantic spatial context | `NPCSerializer._build_dict()` | Coordinates → zone labels | **Unchanged** |
| H2 | Event-driven interrupt | `LLMDecisionSystem._check_interrupt()` | Interrupt-only LLM activation | **Unchanged** |
| H3 | Priority request queue | `LLMRequestQueue` | Serial inference, VRAM safety | **Unchanged** |
| H4 | Guided retry | `LLMDecisionSystem._guided_retry()` | Invalid `action_id` recovery — **now targets Component B only** | **Modified** |
| H5 | Trait coherence guard | `LLMDecisionSystem._enforce_trait_coherence()` | Post-inference Brave/Pacifist override | **Unchanged** |
| H6 | Reasoner output validation | `DualLLMBackend._validate_rationale()` | Rejects empty/malformed Component A output before forwarding | **New** |

**H6 implementation rule:** `_validate_rationale()` rejects output that is empty, shorter than 10 tokens, or contains raw JSON brackets `{` / `}` at the start (indicates the Reasoner hallucinated a JSON response instead of reasoning text). On rejection, the Formatter is called with a fallback rationale string constructed from the NPC's `goals_top` field.

---

## Tick Flow — Updated

```
SimulationManager.tick()
├── StimulusDispatcher.dispatch()
├── FactionRegistry.tick_decay()
└── [per NPC]
    ├── PerceptionSystem.tick()
    ├── NPC.tick()                         # vitals / emotion decay
    ├── NPC.refresh_need_goals()
    ├── LLMDecisionSystem.tick()
    │   ├── [H2] _check_interrupt()
    │   ├── _apply_pending()
    │   │    └── [H5] _enforce_trait_coherence()
    │   ├── _fire_llm_call()               # queues async call
    │   │    └── DualLLMBackend.call()     ← NEW: replaces OllamaBackend
    │   │         ├── Component A: ReasonerBackend.call()  → Turkish rationale
    │   │         ├── [H6] _validate_rationale()           → reject/fallback
    │   │         └── Component B: FormatterBackend.call() → LLMResponse JSON
    │   │              └── [H4] _guided_retry() if JSON invalid (B only)
    │   └── _utility_fallback()            # UtilityEvaluator while A+B in flight
    └── SimLogger.log_npc_tick()
```

---

## What NOT To Do (v2 Additions)

**Do not send the raw NPC state JSON to Component B.**  
Component B is trained only on (reasoning text → JSON) pairs. Sending it the full state JSON will cause schema hallucination. Component B must receive only the text output of Component A.

**Do not run both Ollama processes on the same port.**  
Use distinct ports (e.g. 11434 for Reasoner, 11435 for Formatter). Ollama does not multiplex concurrent model loads on a single port.

**Do not add a second `LLMRequestQueue` for Component B.**  
Both components run sequentially inside the single worker thread. A second queue creates race conditions in `_pending_response` and bypasses the priority heap.

**Do not fine-tune Component B on CoT data.**  
Its job is JSON extraction, not reasoning. Training it on long CoT examples will increase output verbosity and break schema adherence.
