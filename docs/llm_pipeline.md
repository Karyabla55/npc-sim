# NPC-Sim LLM Pipeline — Canonical Reference (v1.6.0)

**Author:** Sadık Abdusselam Albayrak · **License:** Apache 2.0  
**Created:** 2026-05-17 · **Replaces:** The scattered dual-LLM sections in `architecture.md` and `llm_data_spec.md`

This document is the single source of truth for anyone who wants to:
(a) generate training data, (b) fine-tune both models on Kaggle, (c) deploy to Ollama, or (d) configure the runtime for dual-LLM mode.

---

## 1. Why Dual-LLM

A single 3B model asked to "read NPC state JSON → output strict JSON" fails for two reasons:

1. **Reasoning collapse**: the model learns to copy templates ("Cesaretim beni öne atılmaya itiyor") without actually computing from the input values. A Brave Guard with fear=0.10 and a Brave Guard with fear=0.45 produce identical CoT sentences.
2. **Format confusion**: the same model must simultaneously be a Turkish prose reasoner and a strict JSON emitter. Packing examples made EOS invisible; the model learns to keep generating past the end of its turn.

The fix: split the cognitive load.

| Component | Model | Task | Training loss |
|-----------|-------|------|---------------|
| **Reasoner** | Hermes-3-Llama-3.2-3B + LoRA r=16 | NPC state JSON + persona → Turkish CoT prose | On assistant tokens only (`DataCollatorForCompletionOnlyLM`) |
| **Formatter** | Llama-3.2-1B-**Instruct** + LoRA r=8 | CoT prose → strict JSON `LLMResponse` | On assistant tokens only |

The Reasoner never sees JSON output requirements. The Formatter never has to reason from raw scalars — it just translates coherent prose into structure.

---

## 2. Runtime Architecture

```
NPC tick
 └─ LLMDecisionSystem._check_interrupt()    ← H2: threat ≥ 0.8 or HP drop ≥ 15
     └─ LLMRequestQueue.submit()            ← H3: priority async queue
         └─ DualLLMBackend.call()
             ├─ Stage 1: Reasoner (port 11434)
             │    POST /api/chat  {model: "reasoner-lora-v5", messages: [sys+state]}
             │    Response: Turkish CoT prose (3-5 sentences)
             │
             ├─ H6 gate: validate CoT
             │    non-empty, 50-600 chars, not JSON-shaped
             │    FAIL → OllamaBackend fallback (single-pass, same port)
             │
             ├─ Stage 2: Formatter (port 11435)
             │    POST /api/chat  {model: "formatter-lora-v5", messages: [sys+CoT]}
             │    Response: JSON {"reasoning":..., "selected_action":..., "emotion":...}
             │
             └─ npc_id injection + return LLMResponse
                 └─ _on_response() callback
                     └─ _apply_pending() next tick
                         ├─ H5: trait coherence guard
                         └─ execute action
```

**Key invariant:** the simulation never blocks on LLM. If the chain takes longer than `llm_timeout_seconds`, the exception propagates to the callback which clears `_pending` and lets Utility AI fill the tick.

---

## 3. Training Pipeline

### 3.1 Dataset Generation

```bash
# Full run (requires local Ollama + gemma3:4b for bootstrap CoT)
python Stateful_NPC/generator/npc_sim_generator_v2.py

# Skip Gemma bootstrap (uses template CoT — faster, lower quality)
python Stateful_NPC/generator/npc_sim_generator_v2.py --no-gemma
```

Output files in `Stateful_NPC/data/`:
- `train_reasoner.jsonl` — 10 000 examples (NPC state + persona → Turkish CoT)
- `test_reasoner.jsonl`  — 2 000 evaluation examples
- `train_formatter.jsonl` — ~12 000+ examples (CoT → JSON), ~17.5% paraphrase-augmented

**Per-example pipeline:**
1. `generate_npc_state()` → random NPC with archetype, vitals, percepts, memories, beliefs
2. `build_persona_card(state)` → 2-3 Turkish sentences (name, role, faction, traits, b5 deciles)
3. `pick_action_multifactor(state)` → `(action_id, factors)` via 3-zone decision model
4. Optional deviation (15%): D1–D7 override action with intentional "irrational" choice
5. `generate_via_gemma(state, action_id, factors, persona)` → Gemma 3 4B generates CoT
6. Fallback: `generate_cot_reasoning(state, action_id, base_reasoning)` if Gemma unavailable
7. User payload = `"{persona}\n\n{state_json}"` — persona preamble before raw JSON
8. Formatter target = `{"reasoning": full_cot, "selected_action": {...}, "emotion": "..."}`

### 3.2 Notebook Training (Kaggle T4×2)

File: `notebooks/newgen-rpg.ipynb`

| Cell | What it does | Key config |
|------|-------------|------------|
| 11 — Reasoner training | Fine-tune Hermes-3-Llama-3.2-3B + LoRA r=16 | `packing=False`, `DataCollatorForCompletionOnlyLM(response_template="<\|start_header_id\|>assistant<\|end_header_id\|>\n\n")` |
| 17 — Formatter base | Load `unsloth/Llama-3.2-1B-Instruct` | Instruct variant, not base |
| 19 — Formatter training | Fine-tune 1B-Instruct + LoRA r=8 | Same collator as Reasoner |
| After 11 / after 19 | Trait stress test | 50 prompts × 5 archetypes × triggers; compute trait coherence % |

**Why `packing=False`?** With packing, multiple examples are concatenated into fixed-length sequences. The EOS token `<|eot_id|>` becomes "just a token in the middle" — the model never learns to stop. Without packing, each sequence is one example.

**Why `DataCollatorForCompletionOnlyLM`?** Computes loss only on assistant tokens (everything after the `assistant` header). Without this, the model learns to regenerate the system prompt (the observed system-prompt leakage in v1.5.x).

**Why Instruct base for Formatter?** The base `NousResearch/Llama-3.2-1B` never saw `<|start_header_id|>` chat tags during pretraining — it cannot switch roles reliably. The Instruct variant already knows the chat format.

### 3.3 Kaggle → Ollama Deployment

```bash
# After Kaggle training: merge adapter + convert to GGUF Q4_K_M
python -m llama_cpp.convert ... --outtype q4_k_m
ollama create reasoner-lora-v5 -f Modelfile_reasoner
ollama create formatter-lora-v5 -f Modelfile_formatter

# Run two Ollama instances (different ports)
OLLAMA_HOST=0.0.0.0:11434 ollama serve   # Reasoner
OLLAMA_HOST=0.0.0.0:11435 ollama serve   # Formatter
```

---

## 4. Multi-Factor Decision Model

Used in the generator (`decision_factors.py`) to produce the training labels. Replaces the old heuristic that picked action first and wrote CoT to justify it (R5 root cause).

```
self_power = 0.40 * (hp / hp_max)
           + 0.20 * energy
           + 0.15 * role_combat_modifier(occ)        # Guard/Knight/Bandit=0.8, Priest/Scholar=0.2
           + 0.15 * weapon_factor(inv)               # has weapon=1.0, else 0.3
           + 0.10 * (0.5 + trait_courage_modifier)   # Brave +0.2, Aggressive +0.3, Cautious -0.2

perceived_threat = top_threat.threat
                 + memory_bias(memories, threat_id)  # negative memory → +up to 0.3
                 + crowd_factor(percepts)             # each extra threat → +0.1

duty_pull = trait_duty(traits)                       # Loyal/Honorable/Devout → +0.3 each
          + faction_loyalty_bonus(faction, threat)   # community under threat → +0.3
          + 0.2 * b5["c"]                            # conscientiousness
```

**3-zone decision:**

| Zone | Condition | Action |
|------|-----------|--------|
| `no_threat` | No threat percept | vitals/role-based non-combat |
| `low_threat` | `perceived_threat ≤ 0.30` | non-combat despite threat |
| `dominant` | `self_power > perceived_threat + 0.15` | **attack** |
| `duty_attack` | Weaker, but `duty_pull > 0.60` + faction threatened | **attack** |
| `retreat` | `self_power < perceived_threat − 0.15` | **flee** |
| `ambivalent` | Balanced | `heal` if medicine + low HP, else `gather` |

Deterministic (no stochasticity). `factors` dict is passed to Gemma so the CoT can verbalize *why* this zone won.

---

## 5. Persona Card Spec

Built by `persona_card.py`. Prepended to every training example's user turn (fixes R14 — "no 'who am I' anchor").

**Format:** 2-3 Turkish sentences.
- **S1:** Name + role + faction. Example: *"Mehmet, Şehir Muhafızları bünyesinde görev yapan bir muhafız."*
- **S2:** Dominant traits + b5 decile summary. Example: *"Cesur ve sadık biri olarak tanınır; dışadönüklük yüksek, öz-denetim orta, uyumluluk düşük."*
- **S3 (optional):** Extreme b5 elaboration (only when max b5 ≥ 0.75 or min ≤ 0.25). Example: *"Sorumluluklarını hiç ihmal etmez; düzen ve disiplin onun için vazgeçilmezdir."*

B5 decile labels: `yüksek` (≥ 0.70), `orta` (0.45–0.69), `düşük` (< 0.45).

Name pools: 30 Turkish male names + 30 Turkish female names, sampled 50/50.

---

## 6. Bootstrap CoT Prompt (Gemma 3 4B)

Template in `bootstrap_cot.py`:

```
Sen bir ortaçağ simülasyonundaki NPC'nin iç sesisin.
Aşağıdaki bilgilere göre NPC'nin kararını açıklayan 3-5 cümlelik Türkçe iç monolog yaz.

Persona: {persona}

Karar analizi:
  - Öz güç (self_power): {self_power:.3f}
  - Algılanan tehdit (perceived_threat): {perceived_threat:.3f}
  - Görev çekimi (duty_pull): {duty_pull:.3f}
  - Karar bölgesi: {zone}
  - Seçilen eylem: {action_id}

Kurallar:
- ASLA JSON yazma, ASLA "action_id" kelimesini kullanma
- Birinci şahıs iç monolog (Türkçe), nokta ile bitir
- Kararın mantığını sayısal faktörlere dayandır (güç, tehdit, görev)
- 3-5 cümle, kısa ve özlü
```

**Expected output format:** 3-5 Turkish sentences of first-person reasoning. No JSON. No action_id names. Grounded in the numeric factors.

**Cache:** SHA-256 of state content (excluding UUID) + action_id → `.cot_cache/<sha16>.txt`. Incremental runs with the same seed reuse cached CoT.

**Ollama endpoint:** `POST http://localhost:11434/api/generate` with `gemma3:4b`, temperature 0.75, max 300 tokens.

---

## 7. Schema Reference

### Reasoner Input (user turn)

```
{persona_card — 2-3 Turkish sentences}

{npc_state_json}
```

`npc_state_json` fields: `id`, `arch`, `occ`, `faction`, `b5` (5 keys), `traits`, `vitals` (`hp`, `hp_max`, `en`, `hun`, `thi`, `str`), `emo` (`hap`, `fear`, `ang`, `mood`), `inv` (list), `time` (`day`, `hr`), `pos` (`x`, `z`, `zone`, `landmark`), `sched`, `percepts`, `memories`, `beliefs`, `factions`, `goals_top`, `interrupt`, `valid_actions`.

### Reasoner Output (assistant turn)

3-5 sentences of Turkish prose. No JSON. No action_id.

### Formatter Input (user turn)

The Reasoner's output verbatim (optionally paraphrase-augmented during training).

### Formatter Output (assistant turn)

```json
{
  "reasoning": "<full CoT copied from input>",
  "selected_action": {
    "action_id": "<one of valid_actions>",
    "target_id": null,
    "dialogue": null
  },
  "emotion": "<single Turkish or English word>"
}
```

**Note:** `npc_id` is intentionally absent from the Formatter schema. The runtime `DualLLMBackend.call()` injects it from the request's `npc_id` parameter after parsing.

**valid_actions:** `["eat","drink","sleep","flee","gather","heal","attack","socialize","trade","work","pray","walk_to"]`

---

## 8. Eval Criteria

### After Training (Kaggle)

| Model | Metric | Target |
|-------|--------|--------|
| Reasoner | Non-JSON output rate | ≥ 95% |
| Reasoner | Output length 50-600 chars | ≥ 95% |
| Reasoner | **Trait coherence** on 50-prompt stress test | **≥ 80%** |
| Reasoner | Stops at `<|eot_id|>` (no system-prompt leak) | **100%** |
| Formatter | JSON parse rate | ≥ 95% |
| Formatter | Valid `action_id` | ≥ 90% |

**Trait coherence** = % of prompts where the chosen action matches the multi-factor model's prediction given the NPC's traits, hp, and threat level. Checked by the notebook's "trait stress test" cell (50 hand-crafted prompts × 5 archetypes × major triggers).

### Runtime Integration

```bash
# Mock Ollama, all 76 tests green
python -m pytest tests/ -q

# 24-hour strict run with dual backend
python run_diagnostic.py --hours 24 --strict --seed 42
# Expect: 5/5 alive, 0 invariant violations
```

---

## 9. Troubleshooting

| Symptom | Root cause | Fix |
|---------|-----------|-----|
| Reasoner keeps emitting after `<|eot_id|>` | `packing=True` during training | Cell 11: `packing=False` + `DataCollatorForCompletionOnlyLM` |
| Reasoner output starts with `{` | Formatter system prompt bled into Reasoner | Verify `SYSTEM_PROMPT_REASONER` is the one without JSON schema |
| Formatter outputs Turkish prose instead of JSON | Base model (not Instruct) used | Cell 17: use `Llama-3.2-1B-**Instruct**` |
| Formatter produces `"npc_id": "npc_3e7b0d8d"` | Old schema without the R10/R11 fix | Regenerate dataset; check `build_example()` — `structured_out` must not contain `npc_id` |
| CoT recites templates verbatim | Gemma bootstrap unavailable, fell back to `generate_cot_reasoning()` | Run Ollama with `gemma3:4b`; or accept template CoT for ≤ 10k examples |
| H6 gate firing constantly | Reasoner leaking JSON | Verify `response_format=None` in `DualLLMBackend` Stage 1 call (no `"format":"json"`) |
| Brave Guard flees from wolf | Old heuristic `_select_action_standard` was used | Verify `decision_factors.pick_action_multifactor` is wired in the generator |
| Formatter `action_id` hallucination | `valid_actions` list missing/truncated in SYSTEM_PROMPT | Check `SYSTEM_PROMPT_FORMATTER` — all 12 actions must be listed |

---

## 10. Future Work

| Release | Task | Key file |
|---------|------|---------|
| v1.7 | G10: CoT → NPC memory as SelfThought event | `llm_decision_system.py` `_apply_pending()` |
| v1.7 | G11: LLM emotion blended into NPC psychology (0.3 weight) | `llm_decision_system.py` `_apply_pending()` |
| v1.7 | G12: CoT-parsed implicit beliefs → `BeliefSystem` | `llm/cot_parser.py` (new) |
| v1.7 | G13: CoT future-intents → `NPCGoals.enqueue()` | `npc/goals.py` + parser |
| v1.7 | G14: Multi-turn dialogue state (`dialogue_context` ring buffer) | `social/dialogue_state.py` (new) |
| v1.7 | G15: Emergent trait acquisition from consistent LLM emotion | `npc/traits.py` |
| v1.7 | G16: Runtime UtilityEvaluator ← multi-factor model alignment | `decisions/utility_evaluator.py` |
| v1.8 | Grammar-constrained Formatter decoding (GBNF / Outlines) | Only if JSON parse < 95% after v1.6 training |

See `docs/nextsteps.md` § 11 for full G10–G16 spec with acceptance criteria.
