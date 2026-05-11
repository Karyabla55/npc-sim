# Integration Map — Data Subsystems → Action Consumers

**Status:** Current as of v1.4.0.
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

## 2. v1.4.0 wiring

`✅` = consumer reads this subsystem, `—` = no integration. "Read via" names the
`ActionContext` helper that bridges the two.

| Subsystem  | Read via                                | Eat | Drink | Sleep | Heal | Flee | Attack | Gather | Socialize | Trade | Work | Pray | WalkTo |
|------------|-----------------------------------------|-----|-------|-------|------|------|--------|--------|-----------|-------|------|------|--------|
| **Goals**      | `ctx.goal_bonus(GoalType)`             | ✅  | ✅    | ✅    | ✅   | ✅   | ✅¹   | ✅     | ✅        | ✅    | ✅   | ✅   | —      |
| **Memory**     | `ctx.get_memory_threat_bias(subject)`  | —   | —     | —     | —    | ✅²  | —      | —      | ✅³       | —     | —    | —    | ✅     |
| **Beliefs**    | `ctx.belief_score(subject)`            | —   | —     | —     | —    | —    | ✅     | —      | ✅⁴       | —     | —    | —    | ✅     |
| **Social**     | `npc.social.get_relation(target).trust` | —   | —     | —     | —    | —    | —      | —      | ✅⁵       | —     | —    | —    | —      |
| **Traits**     | `npc.traits.has(...)` / weight modifier | —   | —     | —     | —    | ✅   | ✅     | —      | —         | ✅    | —    | ✅   | —      |
| **Schedule**   | `npc.schedule.preference_at(...)`      | —   | —     | ✅    | —    | —    | —      | —      | ✅        | —     | ✅   | —    | ✅     |
| **Vitals**     | `npc.vitals.*`                          | ✅  | ✅    | ✅    | ✅   | —    | —      | ✅     | —         | —     | ✅   | ✅   | ✅     |
| **Psychology** | `npc.psychology.*`                      | ✅  | ✅    | —    | ✅   | ✅   | ✅     | —      | ✅        | —     | ✅   | ✅   | —      |
| **Inventory**  | `npc.inventory.*`                       | ✅  | ✅    | —    | ✅   | —    | —      | ✅     | —         | ✅    | —    | —    | ✅     |

Footnotes:
- ¹ `AttackAction` retains its multiplicative `goal_boost = 1.3` for `GoalType.ATTACK` in addition to the new additive `goal_bonus`.
- ² `FleeAction.evaluate()` adds `(-mem_bias) * 0.15` to the flee score for the threat's identity.
- ³ `SocializeAction.execute()` writes a `Dialogue` `MemoryEntry` into the **listener's** memory (not the speaker's).
- ⁴ `SocializeAction.execute()` propagates the speaker's top-confidence belief to the listener, attenuated by `valence × 0.7`, `confidence × 0.6`, gated by `trust ≥ 0.3`.
- ⁵ Trust gate determines whether gossip transfer happens at all.

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

## 4. Still missing — v1.5 backlog

- **G7** — `LLM reasoning → NPC memory`. The model's chain-of-thought is logged but never written into `npc.memory`, so a long campaign run loses the model's narrative continuity.
- **G8** — `target_context` payload field for social actions. Right now the LLM decides to `socialize`/`trade` without seeing the target's mood, known facts, or current relation — output quality is bounded by what the speaker alone knows.
- **`NPCSocial.reputation`** — stored, never read by any action.
- **`FactionRegistry` dispositions** — exposed to the LLM, but Utility AI doesn't bias attack/socialize/trade by faction stance.
- **`TradeAction`** still uses a hardcoded `0.4 * trait_mod` formula and ignores beliefs/memory entirely; no price negotiation loop.
- **`WorkAction`** ignores beliefs (e.g. "Farm is dangerous") — it commits based on schedule + energy only.

These are tracked in `docs/nextsteps.md` §5 (v1.5 section) and §10.

---

## 5. How to add a new wiring

The pattern v1.4.0 established:

1. Add a helper on `ActionContext` that wraps the subsystem query (e.g. `ctx.belief_score(subject)`). Keep the helper defensive — `try/except`, return a neutral value on failure.
2. Call the helper from the action's `evaluate()` or `execute()`. Keep the magnitude small (rule of thumb: bias terms in `[-0.4, +0.4]`, additive bonuses around `+0.25`) so they tune the existing score rather than dominate it.
3. Update this map and the regression table in [`docs/psychology_model.md`](psychology_model.md) §7 if the change moves a baseline metric.

Avoid wiring directly from `action.evaluate()` into `npc.<subsystem>` — go
through `ActionContext`. This keeps action code testable (you can pass a
synthetic context) and keeps the subsystems decoupled from action internals.
