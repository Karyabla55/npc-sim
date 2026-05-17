# NPC-Sim v1.6.0 — LLM Pipeline Overhaul (Training, Runtime, Docs)

> **Status:** Approved 2026-05-16. Plan is the source of truth for the v1.6.0 release. Execute in phases; Phase 0 first.
>
> **Predecessor:** v1.5.0 shipped 2026-05-12. v1.5.1 audit work (13 files modified, 18 issues closed, 68/68 tests passing, 30-day strict run validated) is staged in working tree, NOT yet committed. Phase 0 of this plan commits it.

## Context

The Dual-LLM training pipeline (`notebooks/newgen-rpg.ipynb`) is broken:

- **Reasoner** (Hermes-3-Llama-3.2-3B + LoRA r=16, 10k Turkish CoT examples) — eval says 99% good-length, 100% non-JSON. But the **end-to-end test** (notebook cell 29) reveals two real failures:
  1. Output **never stops** at `<|eot_id|>`. After the 5-sentence monologue, the model emits `?>` glitches, then re-emits the system prompt, then a fake user turn with a totally different NPC.
  2. **Logical role incoherence**: test NPC is a Brave Guard with fear=0.10, threat=0.85. The Reasoner produces *"Cesaretim beni öne atılmaya itiyor… Bu yüzden geri çekilmek…"* — saying both "my bravery pushes me forward" AND "therefore I should retreat" in adjacent sentences. The Reasoner is reciting templates from the trait→sentence dict verbatim with numbers plugged in, not reasoning.
- **Formatter** (Llama-3.2-1B *base* + LoRA r=8, 12k examples) — **0/200 JSON parse, 0/200 valid action_id**. Echoes input as Turkish prose, eventually emits truncated JSON way too late.

This plan is a v1.6.0 patch covering: generator redesign, training-mechanics fix, Dual-LLM runtime backend (G9 from `docs/nextsteps.md`), and a full documentation sweep.

---

## Root Causes

### Category A — Training mechanics (notebook bugs)

| ID | Where | Why it breaks the model |
|----|-------|-------------------------|
| **R1** | `SFTTrainer(packing=True)` in cells 11 & 19 | Multiple examples concatenated into fixed-length sequences; `<\|eot_id\|>` becomes "just a token in the middle." Model never learns to stop. |
| **R2** | No response-only loss masking | Loss is computed on system+user+assistant tokens. Model learns to **regenerate the system prompt** (exactly what we see leaking after the assistant turn). |
| **R3** | Formatter uses `NousResearch/Llama-3.2-1B` (**base** model) | Base completion model never saw `<\|start_header_id\|>` chat tags during pretraining. It cannot switch roles. |
| **R4** | `tokenizer.pad_token = eos_token` + right-padding + packing | Triple combo where pad == eos confuses stop-signal learning. |

### Category B — Generator semantics & schema

| ID | Where | What's wrong |
|----|-------|--------------|
| **R5** | `_select_action_standard()` — heuristic picks action FIRST, CoT is written to justify it | Model learns to **rationalize a pre-chosen action**, not to reason from rules |
| **R6** | Heuristic action selector contradicts `SYSTEM_PROMPT` "Trait behaviour rules" | Model sees inconsistent training signal |
| **R7** | Formatter must output `npc_id` but it isn't in the input | Model **invents** random IDs (eval output: `"npc_3e7b0d8d"` — unrelated to input) |
| **R8** | `DualLLMBackend` doesn't exist in `npc_sim/llm/llm_backend.py` | Even if both adapters trained perfectly, there's no runtime path. Roadmap task G9. |
| **R9** | `generate_cot_reasoning()` lines 437–498 — S1–S5 sentences are **fixed string templates** | Model memorizes templates. Eval output recites *"Cesaretim beni öne atılmaya itiyor (0.10 korku hissetsem de)"* word-for-word. |
| **R10** | `build_formatter_example()` line 757 puts `npc_id=state["id"]` in assistant JSON but the user turn is only `cot_text` | Schema mismatch — see R7 |
| **R11** | Formatter target JSON has `reasoning = base_reasoning` (1 sentence) but SYSTEM_PROMPT_FORMATTER line 689 says `"reasoning":"<girdiyi kopyala>"` | **Label contradicts prompt instruction**. |
| **R12** | D8 (trauma-driven flee) lines 632–643 fires for **any** archetype including Brave | Breaks "Brave + interrupt → attack" rule. Subsumed into new multi-factor model. |
| **R13** | NPC state encoded as pure scalars (`b5={e:0.67,...}`, `vitals={hp:85,...}`) | 3B model has to tokenize numbers, map scalar → behavior, then apply trait rules. Hardest possible encoding. |
| **R14** | No persona-card / no narrative identity preamble | Model has no "who am I" anchor — only a JSON blob. |

---

## Design Decisions (user-confirmed 2026-05-16)

| Decision | Choice |
|----------|--------|
| Pipeline architecture | **Dual-LLM, fix training bugs** (G9 implemented this release) |
| Language | **Turkish CoT + English JSON keys** (unchanged) |
| Decision model in generator | **Weighted score + 3-zone decision** (self_power vs perceived_threat + duty_pull) |
| Bootstrap LLM | **Local Gemma 3 4B** (`gemma3:4b` via Ollama). Free, decent quality under a *constrained* prompt that feeds it the decision factors + persona; not freelance generation. |
| Persona card source | **Generator-derived** from random Turkish name + occupation + traits + b5 deciles |
| Formatter schema | **Drop `npc_id`** (runtime injects it post-parse). `reasoning = full CoT copy`. |
| D8 (trauma-flee) | **Replaced by multi-factor model** — no fixed-archetype rule, decision emerges from power vs threat + memory bias + duty |
| Runtime Utility AI | **Unchanged for v1.6** — only LLM brain layer learns the new model. Align in v1.7 (G16). |
| Docs | **Full sweep**: new canonical `docs/llm_pipeline.md` + refresh existing 3 docs + add notebook cell explanations |

### Multi-factor decision formula (target — implemented in `Stateful_NPC/generator/decision_factors.py`)

```
self_power = 0.40 * (hp / hp_max)
           + 0.20 * energy
           + 0.15 * role_combat_modifier(occ)        # Guard/Knight/Bandit=0.8, Priest/Scholar=0.2
           + 0.15 * weapon_factor(inv)               # has weapon = 1.0, else 0.3
           + 0.10 * trait_courage_modifier(traits, b5)  # Brave +0.2, Cautious -0.2, Aggressive +0.3

perceived_threat = threat_level
                 + memory_bias(memories, threat_id)  # negative ew about same/similar entity → +up to 0.3
                 + crowd_factor(percepts)            # multiple threats → +0.1 each

duty_pull = trait_duty(traits)                       # Loyal/Honorable/Devout +0.3 each
          + faction_loyalty(faction, threat_faction) # community under threat → +0.3
          + 0.2 * b5["c"]                            # conscientiousness

# 3-zone decision:
if perceived_threat <= 0.30:                         # no real threat
    → pick from non-combat actions (eat/work/social/etc.)
elif self_power > perceived_threat + 0.15:           # I'm stronger
    → attack
elif duty_pull > 0.60 and faction_under_threat:     # weaker but duty compels me
    → attack
elif self_power < perceived_threat - 0.15:           # I'm weaker
    → flee
else:                                                # ambivalent zone
    → defensive: gather(equip) / heal / walk_to(reinforcements)
```

Deterministic (no stochasticity). Action label and the factor breakdown are passed to the bootstrap LLM so the CoT can verbalize *why* this zone won.

---

## Implementation Phases

### Phase 0 — Commit pending v1.5.1 audit work
- 13 files modified in working tree from completed bug-audit sweep (CRITICAL/HIGH/MEDIUM/LOW closures, 68/68 tests passing, 30-day strict run validated). See git status at session start: `M docs/bugs_and_issues.md`, `M npc_sim/decisions/...`, `M npc_sim/llm/...`, `M npc_sim/diagnostics/sim_logger.py`, `M npc_sim/simulation/world_map.py`, `M run_diagnostic.py`, `M tests/test_queue_preemption.py`, plus `D Stateful_NPC/newgen-rpg.ipynb`.
- Commit as v1.5.1, tag, update CHANGELOG. **Then** start Phase 1.

### Phase 1 — Generator redesign

**New files:**

| Path | Purpose |
|---|---|
| `Stateful_NPC/generator/decision_factors.py` | Pure functions: `self_power(state)`, `perceived_threat(state, threat_id)`, `duty_pull(state)`, `pick_action_multifactor(state)` returning `(action_id, factors_dict)` |
| `Stateful_NPC/generator/persona_card.py` | Turkish name pools (male/female ~30 each), occupation labels in Turkish, trait blurb dict, `build_persona_card(state) → str` (2-3 Turkish sentences) |
| `Stateful_NPC/generator/bootstrap_cot.py` | Calls `ollama run gemma3:4b` with structured prompt; input = (state, action_id, factors, persona); output = 3-5 sentence Turkish CoT. SHA-keyed disk cache to avoid re-runs. Fallback to existing template `generate_cot_reasoning()` if Gemma fails. |

**Modified file: `Stateful_NPC/generator/npc_sim_generator_v2.py`**

- Replace `_select_action_standard()` body: route through `decision_factors.pick_action_multifactor()` for threat-containing states; keep simple needs-based fallback (hunger > 0.75, thirst > 0.75, energy < 0.25) for low-threat states.
- Delete `_select_action_with_deviation()` D8 case (now redundant). Keep D1–D7 as additional 15% deviation noise.
- `build_example()`: prepend `build_persona_card(state)` to the user-turn payload, before the JSON. Format: `"{persona_card}\n\n{state_json}"`.
- `build_example()` line 717: remove `"npc_id": state["id"]` from `structured_out`. Final schema:
  ```python
  structured_out = {
      "reasoning": cot,           # FULL CoT, not base_reasoning
      "selected_action": {"action_id": ..., "target_id": ..., "dialogue": ...},
      "emotion": emotion,
  }
  ```
- `SYSTEM_PROMPT_FORMATTER`: remove the `"npc_id":"<string>"` line from the documented schema; update the `valid_actions:` line to reflect ordering.
- Wire `bootstrap_cot.generate_via_gemma()` as the primary CoT source; template `generate_cot_reasoning()` becomes fallback only.

### Phase 2 — Notebook training fixes

**Modified file: `notebooks/newgen-rpg.ipynb`**

- **Cell 11 (Reasoner training):**
  - `packing=False` in SFTTrainer/SFTConfig
  - Use `DataCollatorForCompletionOnlyLM` with `response_template = "<|start_header_id|>assistant<|end_header_id|>\n\n"` so loss is computed only on assistant tokens
  - Add `eos_token_id` explicitly to `tokenizer.eos_token_id` (Hermes-3 sometimes has multiple EOS variants)
- **Cell 17 (Formatter base):** change `FORMATTER_MODEL_ID = "NousResearch/Llama-3.2-1B-Instruct"` (or `unsloth/Llama-3.2-1B-Instruct` if Kaggle mirrors it faster).
- **Cell 19 (Formatter training):** same packing+collator fix as cell 11.
- **New cell after each training:** "Trait stress test" — 50 hand-crafted prompts covering all 5 archetypes × major action triggers; print model outputs side-by-side with expected action. Compute trait coherence percentage as the new eval target.
- **Cells 8, 17 (tokenizer):** add comment explaining why `pad_token = eos_token` is safe now that packing is off.
- **Markdown headers in every code cell** explaining what it does and what the expected output is.

### Phase 3 — Full retraining run

1. Run new generator locally: `python Stateful_NPC/generator/npc_sim_generator_v2.py` → 10k Reasoner train + 2k test + ~12k Formatter. Gemma-bootstrap CoT pass: ~3–6 hours wall-clock (10k examples × ~2 sec/example on local GPU/CPU). SHA cache means incremental edits won't re-bootstrap unchanged states.
2. Upload datasets to Kaggle dataset (replacing `rpg-dataset-llama-3` v4 with v5).
3. Run notebook end-to-end on Kaggle T4×2. Reasoner Phase A ~6 hours, Formatter Phase B ~3 hours.
4. Eval acceptance criteria:
   - Reasoner non-JSON ≥ 95%, output length 50–600 chars ≥ 95%, **trait coherence ≥ 80%** on the new 50-prompt stress test, **stops at `<|eot_id|>` 100%** (no system-prompt leak)
   - Formatter JSON parse ≥ 95%, valid action_id ≥ 90%
5. Export both LoRA adapters; merge with base; convert to GGUF Q4_K_M; push to Ollama as `reasoner-lora-v5` (port 11434) and `formatter-lora-v5` (port 11435).

### Phase 4 — Runtime DualLLMBackend (closes G9)

**Modified file: `npc_sim/llm/llm_backend.py`**

- Extract `OllamaBackend._post_chat(model, messages, base_url) → dict` helper (refactor existing inline POST).
- New class `DualLLMBackend(ILLMBackend)`:
  - `__init__(reasoner_model, reasoner_url, formatter_model, formatter_url, timeout)`
  - `call(payload)`:
    1. Build Reasoner messages with `SYSTEM_PROMPT_REASONER`
    2. POST to reasoner_url → Turkish CoT text
    3. Validate CoT (non-empty, length 50–600, doesn't start with `{`) — implements **H6** gate
    4. If CoT invalid, fall back to single-pass `OllamaBackend` against reasoner_url with combined Reasoner+JSON prompt
    5. Build Formatter messages with `SYSTEM_PROMPT_FORMATTER` and CoT as user content
    6. POST to formatter_url → JSON string
    7. Parse JSON, inject `npc_id` from input payload (was dropped from training schema in R10 fix), return `LLMResponse`
  - On any HTTP error, return None so `LLMRequestQueue` falls back to Utility AI (existing behavior)

**Modified file: `npc_sim/core/sim_config.py`**

- New fields:
  ```python
  llm_reasoner_model: str = "reasoner-lora-v5"
  llm_formatter_model: str = "formatter-lora-v5"
  llm_reasoner_base_url: str = "http://localhost:11434"
  llm_formatter_base_url: str = "http://localhost:11435"
  ```
- Existing `llm_backend: str` accepts new value `"dual"`.

**Modified file: `npc_sim/llm/llm_decision_system.py`**

- Backend factory selects `DualLLMBackend` when `config.llm_backend == "dual"`.

**New file: `tests/test_dual_llm_backend.py`**

- `test_dual_chain_happy_path()` — mock both HTTP endpoints, verify chain
- `test_reasoner_failure_triggers_h6_fallback()`
- `test_formatter_invalid_json_returns_none()`
- `test_npc_id_injected_post_parse()`
- `test_timeout_propagates_to_queue()`

### Phase 5 — Documentation sweep

**New file: `docs/llm_pipeline.md`** — single canonical source. Sections:
1. Why dual-LLM (rationale)
2. Runtime architecture (interrupt → queue → backend → response → trait coherence)
3. Training pipeline (generator → notebook → Kaggle → merge → GGUF → Ollama)
4. Decision model (multi-factor formula, 3-zone rule, trait modifiers table)
5. Persona card spec (template, example)
6. Bootstrap CoT prompt (Gemma 3 4B prompt template, expected output format)
7. Schema reference (input JSON full key list, output JSON, all field types)
8. Eval criteria (trait coherence, JSON validity, action validity, latency targets)
9. Troubleshooting playbook (Reasoner doesn't stop / Formatter outputs prose / model recites templates / etc.)
10. Future work pointers (runtime alignment v1.7, grammar-constrained decoding v1.8 if needed)

**Refresh `docs/architecture.md`** — remove the 200+ line dual-LLM section; replace with one paragraph + link to `docs/llm_pipeline.md`. Keep the H1–H5 + new H6 table.

**Refresh `docs/llm_data_spec.md`** — output schema drops `npc_id`; align trait list with current `_enforce_trait_coherence`; update example payload to match new persona-card-prefixed format.

**Refresh `docs/dataset_training.md`** — corrected hyperparams (`packing=False`, `DataCollatorForCompletionOnlyLM`, `Llama-3.2-1B-Instruct`), new eval metrics (trait coherence), persona-card section, Gemma-bootstrap section.

**Refresh `docs/nextsteps.md`** — mark G9 (DualLLMBackend) as ✅ done. Add **G10–G16: Runtime LLM-depth utilization roadmap** (see next section) — these are NOT implemented in v1.6.0; they are forward-looking tasks for v1.7+ chats.

#### Append to `docs/nextsteps.md` — § "LLM Çıktısının Derin Kullanımı (v1.7+ Yol Haritası)"

> **Bağlam**: v1.6.0 sonrası `LLMResponse` derin bir biliş sinyali taşıyor (`reasoning` CoT, `emotion`, `dialogue`, `target_id`, `selected_action`). Ancak çalışma zamanı (runtime) bu zenginliğin yalnızca `action_id` ve `dialogue`-for-socialize/trade kısmını tüketiyor. Aşağıdaki görevler, LLM beyninin ürettiği derinliği NPC'nin uzun süreli durumuna geri besleyerek "düşünen NPC" hissini kazandırır.

| Görev | Dosya | Açıklama |
|-------|-------|----------|
| **G10** | `npc_sim/llm/llm_decision_system.py` `_apply_pending()` | LLM `reasoning` (tam CoT) bir `SelfThought` event'i olarak `npc.memory.add()`'e yazılsın. `emotional_weight` = (happiness − fear) baz alınsın. Diyalog dışı tüm action'lar için bu yapılmalı. (G7'nin tamamlanması.) |
| **G11** | `npc_sim/llm/llm_decision_system.py` `_apply_pending()` | LLM `emotion` alanı NPC'nin baskın duygusuna 0.3 ağırlıkla harmanlansın (`set_happiness/fear/anger` üzerinden, mood label yeniden hesaplansın). Şu an emotion runtime'da kullanılmıyor. |
| **G12** | `npc_sim/llm/cot_parser.py` (yeni) | CoT içindeki entity referansları + sentiment kelimeleri (T5'te "kurttan korkuyorum", "Elena'ya güveniyorum") regex/keyword ile yakalansın → `BeliefSystem.add_belief()` düşük confidence (0.3) ile yazsın. İlk versiyon kelime listesi tabanlı; v1.8'de Formatter'a "implicit_beliefs" alanı ekleme seçeneği. |
| **G13** | `npc_sim/npc/goals.py` + parser | CoT'ta gelecek-niyet ifadeleri ("sonra tapınağa gideceğim", "yarın pazara") → `NPCGoals.enqueue()` düşük öncelikli soft-goal olarak. Saturation guard: tek seferde max 2 enqueue. |
| **G14** | `npc_sim/social/dialogue_state.py` (yeni) + `SocializeAction.execute()` | Diyalog tek-atış değil; konuşma durumu (last_speaker, last_topic, turn_count, target_id) per-NPC ring buffer'da tutulsun. LLM bir sonraki socialize için bu bağlamı görsün (`npc_serializer.py` payload'a `dialogue_context` alanı ekle). Çok-turn konuşmalar mümkün olur. |
| **G15** | `npc_sim/npc/traits.py` + `_apply_pending()` | LLM N tik üst üste aynı emergent trait sergilerse (örn. `emotion="Devout"` 10× / 50 tik) NPC'nin `traits` listesine eklensin (cap = 6). LLM gözleminden trait kazan(ım)/kayıp loop. Kalıcı kişilik evrimi. |
| **G16** | `npc_sim/decisions/utility_evaluator.py` + tüm 12 action `evaluate()` | Generator'da kullanılan multi-factor karar modelini (`self_power`, `perceived_threat`, `duty_pull`) `UtilityEvaluator`'a entegre et. Şu an LLM ile Utility AI farklı puanlama yapıyor → LLM Brain devre dışıyken NPC davranışı farklı görünüyor. Hizalama, LLM offline'ken sade hissini korur. (v1.6'da non-goal idi; v1.7'de devreye alınacak.) |

**Bağımlılıklar**: G10→G11→G12 sıralı (memory üretimi → emotion update → belief update). G13 bağımsız. G14 G10'a bağlı (memory'de SelfThought varsa context tutarlı). G15 G10+G11 üzerine kurulur (gözlem→trait için emotion+memory sinyalleri lazım). G16 bağımsız ama büyük refactor.

**Kabul kriteri (v1.7 release-gate)**:
- 24-saatlik diagnostic run sonunda her NPC'nin memory'sinde ≥ 1 `SelfThought` entry (G10)
- LLM-driven emotion shift CSV'de gözlemlenebilir; mood label değişimi LLM call'lar etrafında lokalize (G11)
- En az %30 NPC'de LLM-kaynaklı belief entry mevcut (G12)
- Çok-turn diyalog: aynı çiftin 2+ sıralı socialize'ı CSV'de görülüyor (G14)
- LLM kapalı vs açık run'da action distribution farkı < %15 (G16 hizalama testi)

**Refresh `CHANGELOG.md`** — v1.6.0 entry covering: training fixes (R1–R4), generator redesign (R5–R14), DualLLMBackend (G9), documentation sweep.

---

## Files to Create / Modify

### New
| Path | Purpose |
|---|---|
| `docs/llm_pipeline.md` | Canonical pipeline doc |
| `Stateful_NPC/generator/decision_factors.py` | Multi-factor decision module |
| `Stateful_NPC/generator/persona_card.py` | Persona builder |
| `Stateful_NPC/generator/bootstrap_cot.py` | Gemma 3 4B bootstrap |
| `tests/test_dual_llm_backend.py` | Backend chain tests |

### Modified
| Path | Changes |
|---|---|
| `Stateful_NPC/generator/npc_sim_generator_v2.py` | Rewrite `_select_action_standard`, delete D8, integrate persona+bootstrap, fix Formatter schema (R10/R11), update SYSTEM_PROMPT_FORMATTER |
| `notebooks/newgen-rpg.ipynb` | `packing=False`, response masking, swap Formatter base, add 50-prompt trait stress eval, markdown cell headers |
| `npc_sim/llm/llm_backend.py` | Extract `_post_chat`; add `DualLLMBackend` class with H6 gate |
| `npc_sim/llm/llm_decision_system.py` | Backend factory based on `config.llm_backend` |
| `npc_sim/core/sim_config.py` | New dual-LLM config keys |
| `docs/architecture.md` | Trim dual-LLM section; link to llm_pipeline.md |
| `docs/llm_data_spec.md` | Schema refresh (no npc_id in Formatter output, persona preamble) |
| `docs/dataset_training.md` | Corrected hyperparams, new eval metrics, persona+bootstrap sections |
| `docs/nextsteps.md` | G9 done; G10–G16 added |
| `CHANGELOG.md` | v1.6.0 entry |

---

## Reuse — Don't Reinvent

- `LLMRequestQueue` — unchanged; `DualLLMBackend` flows through the same queue
- `_check_interrupt`, `_apply_pending`, `_enforce_trait_coherence` — unchanged
- Existing dataset infrastructure (`generate_dataset`, `generate_formatter_dataset`, oversampling, paraphrase) — keep, only the per-example builder changes
- `trait_sentences` dict and `action_rationale` dict in generator — keep as **fallback** for when Gemma bootstrap fails
- `OllamaBackend._post_chat` (to be extracted) — `DualLLMBackend` reuses it for both ports
- `WorldRegistry` (H1 zone mapping) — unchanged
- Existing eval cells in notebook — keep; add stress-test cell alongside

---

## Verification

### Generator
- Run 100 examples through new generator; manually inspect: each persona distinct, action choice matches multi-factor scores, CoT not templated verbatim
- Diff first 100 lines of new vs old `train_reasoner.jsonl` — persona present, schema correct

### Training (smoke, locally without Kaggle)
- 200-example smoke train of Reasoner for 30 steps: verify loss drops AND output stops at `<|eot_id|>` on a held-out prompt (no system-prompt leak)
- 200-example smoke train of Formatter for 30 steps: verify JSON parse ≥ 50% (smoke target)

### Training (full Kaggle)
- Reasoner trait coherence ≥ 80% on 50-prompt stress test
- Formatter JSON parse ≥ 95% on the existing 200-example eval cell
- End-to-end test cell (cell 29): both outputs clean, no leakage, JSON parses, action_id valid, npc_id injected by Python wrapper

### Runtime
- `pytest tests/ -q` → 68 existing + 5 new dual backend tests all green
- `python run_diagnostic.py --hours 24 --strict` with `llm_backend=dual` against mocked Ollama → 5/5 alive, 0 invariant violations
- Manual integration: load both LoRA-merged GGUFs into local Ollama on ports 11434+11435; run sim 1 sim-hour with one Brave Guard and seeded wolf threat; verify the Brain output is sane Turkish CoT + valid action JSON + correct trait coherence (attack expected)

### Documentation
- Read `docs/llm_pipeline.md` cold: can a new contributor (a) generate dataset, (b) train both models on Kaggle, (c) deploy to Ollama, (d) configure SimConfig for dual mode? If yes → doc is sufficient.

---

## Estimated Effort
- Phase 0 (commit v1.5.1): 30 min
- Phase 1 (generator redesign): 1–2 days code + 0.5 day Gemma bootstrap run
- Phase 2 (notebook fixes): 0.5 day
- Phase 3 (Kaggle full training + eval iteration): 1–2 days
- Phase 4 (DualLLMBackend + tests): 1 day
- Phase 5 (docs sweep): 1 day
- **Total: ~5–7 working days**

---

## Non-goals (deferred, but TRACKED in `docs/nextsteps.md` G10–G16)

v1.6.0 fixes training + adds DualLLMBackend, but the runtime still only consumes `action_id` and (limited) `dialogue` from the LLM's rich output. The following are explicitly out of scope for v1.6.0 and are written into `docs/nextsteps.md` as G10–G16 for subsequent chats:

- **G10**: CoT → NPC.memory as `SelfThought` event (closes G7)
- **G11**: LLM `emotion` blended into NPC.psychology (0.3 weight)
- **G12**: CoT-parsed implicit beliefs → `BeliefSystem` (low confidence)
- **G13**: CoT-parsed future intents → `NPCGoals.enqueue()`
- **G14**: Multi-turn dialogue state (`dialogue_context` in serializer payload, ring buffer)
- **G15**: Emergent trait acquisition from LLM observation (N-consistent emotion → trait list)
- **G16**: Runtime Utility AI alignment with generator's multi-factor decision model

Other deferrals:
- **Grammar-constrained decoding** (llama.cpp GBNF / Outlines) → v1.8, only if Formatter JSON parse stays < 95% after this plan's fixes
- **Switching reasoning language to English** → kept Turkish per user choice
- **API-based bootstrap** (Claude / GPT) → unless Gemma 4B output quality blocks Phase 3 acceptance

---

## Session Handoff Notes (2026-05-16)

**Where to resume next session:**

1. Verify v1.5.1 staged work is intact: `git status` — should show 13 modified files (sim_logger.py, world_map.py, builtin.py, action_context.py, action_lock.py, decision_system.py, llm_backend.py, llm_decision_system.py, llm_request_queue.py, npc_serializer.py, world_map.py, run_diagnostic.py, tests/test_queue_preemption.py, docs/bugs_and_issues.md). v1.6.0 work has NOT started yet.
2. Read this plan top-to-bottom.
3. Read user's auto-memory at `C:\Users\Sadik\.claude\projects\D--DeepLearning-Projects-npc-sim\memory\` — especially `feedback_npc_roleplay_vision.md` and `feedback_turkish_in_codebase.md`.
4. Start with **Phase 0**: commit v1.5.1 cleanly, tag, update CHANGELOG. Sample commit message structure already exists in recent git log (see `7c63486 docs(v1.5.0): post-release sweep across 9 files`).
5. Then **Phase 1**: create `decision_factors.py`, `persona_card.py`, `bootstrap_cot.py`; modify `npc_sim_generator_v2.py`. Smoke-test with 100 generated examples before scaling to 10k.

**Open semantic question to confirm with user when resuming Phase 1:**
- Turkish name pool composition (male/female/unisex ratios) — pick once and document
- Whether the bootstrap_cot SHA-cache should live in `Stateful_NPC/generator/.cot_cache/` (gitignored) or persistent dataset directory
- Whether to keep the existing 10k/2k/12k dataset sizes or scale up given the richer per-example signal

**Things to NOT do in next session:**
- Don't change runtime `UtilityEvaluator` scoring — that's G16, v1.7 work
- Don't switch the bootstrap LLM to a cloud API unless Gemma 3 4B local output proves unusable (acceptance criterion: 100-example manual review shows ≥ 80% coherent CoT)
- Don't drop Turkish from CoT — user explicitly chose to keep it
- Don't add G10–G15 runtime depth utilization to v1.6.0 — explicitly deferred to v1.7+
