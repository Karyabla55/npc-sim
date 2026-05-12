# Integration Map — Data Subsystems → Action Consumers

**Status:** Current as of v1.5.0.
**Purpose:** Single-page answer to "which action reads which subsystem?" The
data half of the codebase (Memory, Beliefs, Goals, Social, Traits) is much
older than the consumer half (Utility AI action `evaluate()` / `execute()`),
and the gap has been the project's biggest credibility issue. This file makes
the wiring explicit so contributors can see what's connected and what isn't.

For the architectural philosophy and tick flow, see
[`docs/architecture.md`](architecture.md). For the psychology balance, see
[`docs/psychology_model.md`](psychology_model.md).

---

## 1. Pre-v1.4.0 baseline

> Memory/Beliefs/Goals/Social existed but nothing read them in scoring.

Only the LLM payload exposed these subsystems — the Utility AI was effectively
trait-and-vitals-only. The result was the "anti-learning" pattern described in
`nextsteps.md` §3.3: an NPC could be robbed in Market and still walk into
Market on the next tick because `WalkToAction.evaluate()` didn't look at memory.

---

## 2. v1.5.0 wiring

`✅` = consumer reads this subsystem, `—` = no integration. "Read via" names the
`ActionContext` helper that bridges the two.

| Subsystem      | Read via                                  | Eat | Drink | Sleep | Heal | Flee | Attack | Gather | Socialize | Trade | Work | Pray | WalkTo |
|----------------|-------------------------------------------|-----|-------|-------|------|------|--------|--------|-----------|-------|------|------|--------|
| **Goals**      | `ctx.goal_bonus(GoalType)`                | ✅  | ✅    | ✅    | ✅   | ✅   | ✅¹   | ✅     | ✅        | ✅    | ✅   | ✅   | —      |
| **Memory**     | `ctx.get_memory_threat_bias(subject)`     | —   | —     | —     | —    | ✅²  | —      | —      | ✅³       | —     | —    | —    | ✅     |
| **Beliefs**    | `ctx.belief_score(subject)`               | —   | —     | —     | —    | —    | ✅     | —      | ✅⁴       | ✅⁶   | ✅⁷  | —    | ✅     |
| **Social.relations** | `npc.social.get_relation(target).trust` | —   | —     | —     | —    | —    | —      | —      | ✅⁵       | —     | —    | —    | —      |
| **Social.reputation** | `target.social.reputation`         | —   | —     | —     | —    | —    | —      | —      | ✅⁸       | ✅⁸   | —    | —    | —      |
| **Faction**    | `ctx.faction_disposition(target_id)`      | —   | —     | —     | —    | —    | ✅⁹   | —      | ✅⁹       | —     | —    | —    | —      |
| **Traits**     | `npc.traits.has(...)` / weight modifier   | —   | —     | —     | —    | ✅   | ✅     | —      | —         | ✅    | —    | ✅   | —      |
| **Schedule**   | `npc.schedule.preference_at(...)`         | —   | —     | ✅    | —    | —    | —      | —      | ✅        | —     | ✅   | —    | ✅     |
| **Vitals**     | `npc.vitals.*`                            | ✅  | ✅    | ✅    | ✅   | —    | —      | ✅     | —         | —     | ✅   | ✅   | ✅     |
| **Psychology** | `npc.psychology.*`                        | ✅  | ✅    | —    | ✅   | ✅   | ✅     | —      | ✅        | —     | ✅   | ✅   | —      |
| **Inventory**  | `npc.inventory.*`                         | ✅  | ✅    | —    | ✅   | —    | —      | ✅     | —         | ✅    | —    | —    | ✅     |

Footnotes:
- ¹ `AttackAction` retains its multiplicative `goal_boost = 1.3` for `GoalType.ATTACK` in addition to the new additive `goal_bonus`.
- ² `FleeAction.evaluate()` adds `(-mem_bias) * 0.15` to the flee score for the threat's identity.
- ³ `SocializeAction.execute()` writes a `Dialogue` `MemoryEntry` into the **listener's** memory (not the speaker's).
- ⁴ `SocializeAction.execute()` propagates the speaker's top-confidence belief to the listener, attenuated by `valence × 0.7`, `confidence × 0.6`, gated by `trust ≥ 0.3`.
- ⁵ Trust gate determines whether gossip transfer happens at all. v1.5.0+: `NPCSocial.relations` is LRU-capped at 200 with `<0.05` magnitude prune.
- ⁶ **B1 (v1.5.0):** `TradeAction.evaluate()` adds `0.30 × belief` for negative target valence (deters), `0.15 × belief` for positive (favors). On success, both NPCs `witness_event(trade_event, [other_id], ...)` so trust compounds.
- ⁷ **B2 (v1.5.0):** `WorkAction.evaluate()` adds `0.25 × belief` for negative `belief_score(home_zone)` only — positive workplace beliefs don't inflate the score because scheduled work is already preferred. Zone name comes from `WorldMap.get_home_zone_name(occupation)`.
- ⁸ **B3 (v1.5.0):** `SocializeAction.evaluate()` adds `0.20 × (target.social.reputation − 0.5)`; `TradeAction.evaluate()` subtracts `0.30` when `target.social.reputation < 0.3`.
- ⁹ **B4 (v1.5.0):** `ActionContext.faction_disposition(target_id)` returns `[-1, +1]`. `AttackAction` adds `0.30 × (-disp)` for enemy factions, `-0.30 × disp` for allied. `SocializeAction` mirrors with `0.40 × disp` for enemies, `0.20 × disp` for allies. `BeliefSystem` is LRU-capped at 200 with `<0.05` prune; `FactionRegistry` cleanup threshold raised to `0.01`.

---

## 3. LLM bridge

`LLMDecisionSystem._apply_pending()` (`npc_sim/llm/llm_decision_system.py`)
hands off model-generated artefacts to the data layer:

| LLM output         | Destination                                            | Consumer                |
|--------------------|--------------------------------------------------------|-------------------------|
| `action_id`        | resolved via `ActionLibrary`                           | the action itself       |
| `reasoning`        | `LLMDecisionSystem.last_reasoning` (per-system field)  | UI / logger             |
| `dialogue`         | `NPC.pending_dialogue` (v1.4.0+)                       | `SocializeAction.execute()` writes it as a `Dialogue` event into the listener's memory |
| `emotion`          | `LLMDecisionSystem.last_emotion`                       | UI / logger             |
| `target_id`        | currently informational                                | — *(v1.5: target_context)* |

`H5` trait-coherence guard in the same file overrides `action_id` when it
contradicts hard trait rules (`Brave` standing ground, `Pacifist` refusing
combat).

---

## 4. Closed in v1.5.0

The Utility AI gaps the v1.4.0 version of this doc listed are now wired:

- **`TradeAction`** reads `ctx.belief_score(target_id)` and reinforces beliefs on success (B1).
- **`WorkAction`** reads `ctx.belief_score(home_zone)` so a Farmer avoids a farm it remembers as dangerous (B2).
- **`NPCSocial.reputation`** is read by `SocializeAction` and `TradeAction` (B3).
- **`FactionRegistry` dispositions** reach the Utility AI through new helper `ctx.faction_disposition(target_id)`; `AttackAction` and `SocializeAction` consume it (B4).

## 5. Still missing — v1.5+ backlog

- **G7** — `LLM reasoning → NPC memory`. The model's chain-of-thought is logged but never written into `npc.memory`, so a long campaign run loses the model's narrative continuity.
- **G8** — `target_context` payload field for social actions. Right now the LLM decides to `socialize`/`trade` without seeing the target's mood, known facts, or current relation — output quality is bounded by what the speaker alone knows.
- **G9** — `DualLLMBackend`: split Reasoner (3B) + Formatter (1B) across two Ollama instances. Currently `npc_sim/llm/llm_backend.py` ships only `OllamaBackend` (single model) and `MockBackend`.
- **`TradeAction` price negotiation** — current trade is still a 1:1 GOLD↔FOOD swap; no price discovery loop.

These are tracked in `docs/nextsteps.md` §5 (v1.5 section) and §10. World events / lifecycle aging are deferred to v2.0+ and v3.0 respectively.

---

## 6. How to add a new wiring

The pattern v1.4.0 established (still current in v1.5.0):

1. Add a helper on `ActionContext` that wraps the subsystem query (e.g. `ctx.belief_score(subject)`). Keep the helper defensive — `try/except`, return a neutral value on failure.
2. Call the helper from the action's `evaluate()` or `execute()`. Keep the magnitude small (rule of thumb: bias terms in `[-0.4, +0.4]`, additive bonuses around `+0.25`) so they tune the existing score rather than dominate it.
3. Update this map and the regression table in [`docs/psychology_model.md`](psychology_model.md) §7 if the change moves a baseline metric.

Avoid wiring directly from `action.evaluate()` into `npc.<subsystem>` — go
through `ActionContext`. This keeps action code testable (you can pass a
synthetic context) and keeps the subsystems decoupled from action internals.
