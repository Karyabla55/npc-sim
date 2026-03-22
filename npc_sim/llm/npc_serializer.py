# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""NPCSerializer: builds the minified JSON payload sent to the LLM each decision tick.

Design goals:
- Token-efficient: short keys, no redundant whitespace
- Semantically rich: zone labels (H1), interrupt flag (H2), valid_actions list
- Deterministic: same NPC state always produces the same payload bytes
"""

from __future__ import annotations
import json
from typing import TYPE_CHECKING
from npc_sim.llm.world_registry import get_default_registry, WorldRegistry
from npc_sim.decisions.action_context import ActionContext

if TYPE_CHECKING:
    from npc_sim.npc.npc import NPC


class NPCSerializer:
    """
    Converts NPC state + ActionContext into a compact JSON string for the LLM.
    Short-key schema is documented in docs/llm_data_spec.md.
    """

    MAX_MEMORIES = 3
    MAX_PERCEPTS = 5
    MAX_BELIEFS = 5
    MAX_INVENTORY = 8

    def __init__(self, registry: WorldRegistry = None):
        self._registry = registry or get_default_registry()

    def build_payload(self, npc, ctx: ActionContext,
                      interrupt: bool = False) -> str:
        """
        Returns a compact, minified JSON string suitable for the LLM system prompt.
        """
        payload = self._build_dict(npc, ctx, interrupt)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def _build_dict(self, npc, ctx: ActionContext, interrupt: bool) -> dict:
        v = npc.vitals
        p = npc.psychology
        pos = self._registry.resolve(npc.position.x, npc.position.z)

        return {
            "id": npc.identity.npc_id,
            "arch": npc.identity.personality_archetype,
            "occ": npc.identity.occupation,
            "faction": npc.identity.faction,
            "b5": {
                "e": round(p.extraversion, 2),
                "a": round(p.agreeableness, 2),
                "c": round(p.conscientiousness, 2),
                "n": round(p.neuroticism, 2),
                "o": round(p.openness, 2),
            },
            "traits": list(npc.traits.tags),
            "vitals": {
                "hp": round(v.health, 1),
                "hp_max": round(v.max_health, 1),
                "en": round(v.energy_norm, 2),
                "hun": round(v.hunger, 2),
                "thi": round(v.thirst, 2),
                "str": round(v.stress, 2),
            },
            "emo": {
                "hap": round(p.happiness, 2),
                "fear": round(p.fear, 2),
                "ang": round(p.anger, 2),
                "mood": p.mood_label,
            },
            "inv": self._serialize_inventory(npc),
            "time": {
                "day": ctx.current_time // (ctx.self_npc._config.day_length_seconds
                                            if ctx.self_npc._config else 1440),
                "hr": round(ctx.sim_day_hour, 1),
            },
            "pos": {
                "x": round(npc.position.x, 1),
                "z": round(npc.position.z, 1),
                **pos,
            },
            "percepts": self._serialize_percepts(ctx),
            "memories": self._serialize_memories(npc, ctx.current_time),
            "beliefs": self._serialize_beliefs(npc),
            "factions": self._serialize_factions(npc),
            "goals_top": npc.goals.get_top_goal().goal_type
                         if npc.goals.get_top_goal() else None,
            "sched": {
                "act":      npc.schedule.get_suggested_activity(ctx.sim_day_hour),
                "wk_start": npc.schedule.work_start_hour,
                "wk_end":   npc.schedule.work_end_hour,
                "sleep":    npc.schedule.sleep_start_hour,
                "wake":     npc.schedule.wake_hour,
            },
            "interrupt": interrupt,
            "valid_actions": self._valid_actions(ctx),
        }

    def _serialize_inventory(self, npc) -> list[dict]:
        result = []
        for stack in npc.inventory.stacks[:self.MAX_INVENTORY]:
            result.append({"id": stack.item_id, "n": stack.amount})
        return result

    def _serialize_percepts(self, ctx: ActionContext) -> list[dict]:
        percepts = sorted(ctx.active_percepts, key=lambda p: -p.salience)
        result = []
        for perc in percepts[:self.MAX_PERCEPTS]:
            entry = {
                "id": perc.object_id,
                "tag": perc.tag,
                "sal": round(perc.salience, 2),
            }
            if perc.threat_level > 0:
                entry["threat"] = round(perc.threat_level, 2)
            result.append(entry)
        return result

    def _serialize_memories(self, npc, current_time: float) -> list[dict]:
        """Top N most salient recent memories."""
        entries = npc.memory.to_list()
        # Sort by |emotional_weight|, take top MAX
        entries.sort(key=lambda e: abs(e.emotional_weight), reverse=True)
        result = []
        for mem in entries[:self.MAX_MEMORIES]:
            dt = round(current_time - mem.recorded_at, 0)
            result.append({
                "evt": mem.event.event_type,
                "desc": mem.event.description[:80],  # truncate for token savings
                "ew": round(mem.emotional_weight, 2),
                "dt": int(dt),
            })
        return result

    def _serialize_beliefs(self, npc) -> list[dict]:
        result = []
        for subj, node in list(npc.beliefs.nodes.items())[:self.MAX_BELIEFS]:
            result.append({
                "subj": subj[:20],
                "conf": round(node.confidence, 2),
                "val": round(node.valence, 2),
            })
        return result

    def _serialize_factions(self, npc) -> dict:
        # Use first 5 relations sorted by absolute Trust deviation from 0
        rels = npc.social.get_all_relations()
        rels.sort(key=lambda r: abs(r.trust), reverse=True)
        result = {}
        for rel in rels[:5]:
            result[rel.target_id[:12]] = round(rel.trust, 2)
        return result

    def _valid_actions(self, ctx: ActionContext) -> list[str]:
        """Only include actions that pass is_valid() for token efficiency."""
        from npc_sim.decisions.utility_evaluator import UtilityEvaluator
        valid = []
        for action in ctx.world._get_action_library_if_set() if hasattr(ctx.world, '_get_action_library_if_set') else []:
            if action.is_valid(ctx):
                valid.append(action.action_id)
        # Fallback: include all action IDs from the library
        if not valid and hasattr(ctx, '_action_library'):
            valid = [a.action_id for a in ctx._action_library.get_all() if a.is_valid(ctx)]
        return valid
