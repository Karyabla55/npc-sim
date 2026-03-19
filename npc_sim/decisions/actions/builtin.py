# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""All 11 built-in NPC actions for the utility AI system."""

from __future__ import annotations
from npc_sim.decisions.action import IAction
from npc_sim.decisions.action_context import ActionContext
from npc_sim.events.sim_event import SimEvent
from npc_sim.npc.inventory import ItemIds
from npc_sim.npc.goals import GoalType
from npc_sim.core.sim_vector3 import SimVector3


# ═══════════════════════════════════════════════════════════════════════════════
# EAT
# ═══════════════════════════════════════════════════════════════════════════════

class EatAction(IAction):
    action_id = "eat"
    action_type = "Eat"

    _HUNGER_THRESHOLD = 0.35
    _HUNGER_REDUCTION = 0.55
    _ENERGY_GAIN_FRAC = 0.08
    _HAPPINESS_GAIN = 0.08

    def is_valid(self, ctx: ActionContext) -> bool:
        if ctx.self_npc.vitals.hunger < self._HUNGER_THRESHOLD:
            return False
        return ctx.self_npc.inventory.has(ItemIds.FOOD) or ctx.has_percept("Food")

    def evaluate(self, ctx: ActionContext) -> float:
        h = ctx.self_npc.vitals.hunger
        return h * h

    def execute(self, ctx: ActionContext) -> None:
        v = ctx.self_npc.vitals
        p = ctx.self_npc.psychology
        ate_inv = ctx.self_npc.inventory.remove(ItemIds.FOOD, 1)
        v.set_hunger(max(0.0, v.hunger - self._HUNGER_REDUCTION))
        v.restore_energy(self._ENERGY_GAIN_FRAC * v.max_energy)
        p.set_happiness(min(1.0, p.happiness + self._HAPPINESS_GAIN))
        for g in ctx.goals.get_by_type(GoalType.FIND_FOOD):
            g.set_progress(1.0)
        src = "from pack" if ate_inv else "from ground"
        if ctx.world:
            ctx.world.publish_event(SimEvent(
                self.action_type, ctx.self_npc.identity.npc_id, None,
                f"{ctx.self_npc.identity.display_name} eats {src}.",
                0.2, ctx.current_time, ctx.self_npc.position, ctx.rng, "health"))


# ═══════════════════════════════════════════════════════════════════════════════
# SLEEP
# ═══════════════════════════════════════════════════════════════════════════════

class SleepAction(IAction):
    action_id = "sleep"
    action_type = "Sleep"

    def is_valid(self, ctx: ActionContext) -> bool:
        return ctx.self_npc.vitals.energy_norm < 0.4

    def evaluate(self, ctx: ActionContext) -> float:
        fatigue = 1.0 - ctx.self_npc.vitals.energy_norm
        schedule_pref = ctx.self_npc.schedule.preference_at("sleep", ctx.sim_day_hour)
        return fatigue * 0.7 + schedule_pref * 0.3

    def execute(self, ctx: ActionContext) -> None:
        v = ctx.self_npc.vitals
        restore = 0.15 * v.max_energy * ctx.delta_time
        v.restore_energy(restore)
        v.set_stress(max(0.0, v.stress - 0.02 * ctx.delta_time))
        for g in ctx.goals.get_by_type(GoalType.REST):
            g.set_progress(min(1.0, g.progress + 0.1))
        if ctx.world:
            ctx.world.publish_event(SimEvent(
                self.action_type, ctx.self_npc.identity.npc_id, None,
                f"{ctx.self_npc.identity.display_name} rests.",
                0.1, ctx.current_time, ctx.self_npc.position, ctx.rng, "health"))


# ═══════════════════════════════════════════════════════════════════════════════
# FLEE
# ═══════════════════════════════════════════════════════════════════════════════

class FleeAction(IAction):
    action_id = "flee"
    action_type = "Flee"

    def is_valid(self, ctx: ActionContext) -> bool:
        return ctx.has_percept("Threat")

    def evaluate(self, ctx: ActionContext) -> float:
        threat = ctx.get_top_percept("Threat")
        if not threat:
            return 0.0
        fear = ctx.self_npc.psychology.fear
        neuroticism = ctx.self_npc.psychology.neuroticism
        return max(0.0, min((threat.threat_level * 0.5 + fear * 0.3 + neuroticism * 0.2), 1.0))

    def execute(self, ctx: ActionContext) -> None:
        threat = ctx.get_top_percept("Threat")
        if not threat or not ctx.world:
            return
        direction = (ctx.self_npc.position - threat.last_known_position).normalized()
        speed = 5.0
        new_pos = ctx.self_npc.position + direction * speed * ctx.delta_time
        ctx.world.move_npc(ctx.self_npc.identity.npc_id, new_pos)
        ctx.self_npc.vitals.consume_energy(2.0 * ctx.delta_time)
        ctx.world.publish_event(SimEvent(
            self.action_type, ctx.self_npc.identity.npc_id, threat.object_id,
            f"{ctx.self_npc.identity.display_name} flees from {threat.object_id}.",
            -0.3, ctx.current_time, ctx.self_npc.position, ctx.rng, "safety"))


# ═══════════════════════════════════════════════════════════════════════════════
# GATHER
# ═══════════════════════════════════════════════════════════════════════════════

class GatherAction(IAction):
    action_id = "gather"
    action_type = "Gather"

    def is_valid(self, ctx: ActionContext) -> bool:
        v = ctx.self_npc.vitals
        return v.hunger > 0.3 or v.thirst > 0.3

    def evaluate(self, ctx: ActionContext) -> float:
        v = ctx.self_npc.vitals
        urgency = max(v.hunger, v.thirst)
        return urgency * 0.6

    def execute(self, ctx: ActionContext) -> None:
        v = ctx.self_npc.vitals
        if v.hunger >= v.thirst:
            ctx.self_npc.inventory.add(ItemIds.FOOD, 1)
            resource = "food"
        else:
            ctx.self_npc.inventory.add(ItemIds.WATER, 1)
            resource = "water"
        v.consume_energy(3.0 * ctx.delta_time)
        if ctx.world:
            ctx.world.publish_event(SimEvent(
                self.action_type, ctx.self_npc.identity.npc_id, None,
                f"{ctx.self_npc.identity.display_name} gathers {resource}.",
                0.15, ctx.current_time, ctx.self_npc.position, ctx.rng, "resource"))


# ═══════════════════════════════════════════════════════════════════════════════
# HEAL
# ═══════════════════════════════════════════════════════════════════════════════

class HealAction(IAction):
    action_id = "heal"
    action_type = "Heal"

    def is_valid(self, ctx: ActionContext) -> bool:
        v = ctx.self_npc.vitals
        return v.health < v.max_health * 0.7 and ctx.self_npc.inventory.has(ItemIds.MEDICINE)

    def evaluate(self, ctx: ActionContext) -> float:
        v = ctx.self_npc.vitals
        return (1.0 - v.health / v.max_health) * 0.8

    def execute(self, ctx: ActionContext) -> None:
        ctx.self_npc.inventory.remove(ItemIds.MEDICINE, 1)
        ctx.self_npc.vitals.heal(25.0)
        ctx.self_npc.psychology.set_fear(max(0.0, ctx.self_npc.psychology.fear - 0.1))
        if ctx.world:
            ctx.world.publish_event(SimEvent(
                self.action_type, ctx.self_npc.identity.npc_id, None,
                f"{ctx.self_npc.identity.display_name} uses medicine.",
                0.3, ctx.current_time, ctx.self_npc.position, ctx.rng, "health"))


# ═══════════════════════════════════════════════════════════════════════════════
# ATTACK
# ═══════════════════════════════════════════════════════════════════════════════

class AttackAction(IAction):
    action_id = "attack"
    action_type = "Attack"

    def is_valid(self, ctx: ActionContext) -> bool:
        if not ctx.has_percept("Threat"):
            return False
        if ctx.self_npc.traits.has("Pacifist"):
            return False
        return ctx.self_npc.traits.has("Aggressive") or ctx.self_npc.psychology.anger > 0.65

    def evaluate(self, ctx: ActionContext) -> float:
        anger = ctx.self_npc.psychology.anger
        bravery = 1.0 - ctx.self_npc.psychology.neuroticism
        trait_mod = ctx.self_npc.traits.get_weight_modifier(self.action_type)
        goal_boost = 1.3 if ctx.has_goal(GoalType.ATTACK) else 1.0
        raw = ((anger + bravery) / 2.0) * trait_mod * goal_boost
        return max(0.0, min(raw, 1.0))

    def execute(self, ctx: ActionContext) -> None:
        threat = ctx.get_top_percept("Threat")
        if not threat:
            return
        npc = ctx.self_npc
        npc.vitals.set_stress(min(1.0, npc.vitals.stress + 0.1))
        npc.psychology.set_anger(max(0.0, npc.psychology.anger - 0.2))

        melee_dist = 3.0
        sq_dist = SimVector3.sqr_distance(npc.position, threat.last_known_position)
        if sq_dist <= melee_dist ** 2 and ctx.world:
            target_npc = ctx.world.get_npc_by_id(threat.object_id)
            if target_npc:
                damage = 10.0 + ctx.rng.next_float(-3.0, 3.0)
                target_npc.vitals.apply_damage(damage)
                ev = SimEvent("Combat", npc.identity.npc_id, threat.object_id,
                              f"{npc.identity.display_name} attacks {threat.object_id} for {damage:.0f} damage!",
                              -0.8, ctx.current_time, npc.position, ctx.rng, "combat")
                target_npc.witness_event(ev, [npc.identity.npc_id, "World_Safety"], ctx.current_time)
                ctx.world.publish_event(ev)
                npc.social.modify_reputation(-0.05)
                target_npc.social.modify_reputation(0.02)
        elif ctx.world:
            direction = (threat.last_known_position - npc.position).normalized()
            new_pos = npc.position + direction * 4.0 * ctx.delta_time
            ctx.world.move_npc(npc.identity.npc_id, new_pos)

        if ctx.world:
            ctx.world.publish_event(SimEvent(
                "AttackAttempt", npc.identity.npc_id, threat.object_id,
                f"{npc.identity.display_name} attempts to attack {threat.object_id}.",
                -0.6, ctx.current_time, npc.position, ctx.rng, "combat"))


# ═══════════════════════════════════════════════════════════════════════════════
# SOCIALIZE
# ═══════════════════════════════════════════════════════════════════════════════

class SocializeAction(IAction):
    action_id = "socialize"
    action_type = "Socialize"

    def is_valid(self, ctx: ActionContext) -> bool:
        return ctx.has_percept("Ally") or ctx.has_percept("NPC")

    def evaluate(self, ctx: ActionContext) -> float:
        ext = ctx.self_npc.psychology.extraversion
        sched = ctx.self_npc.schedule.preference_at("social", ctx.sim_day_hour)
        return ext * 0.5 + sched * 0.5

    def execute(self, ctx: ActionContext) -> None:
        ally = ctx.get_top_percept("Ally") or ctx.get_top_percept("NPC")
        if not ally or not ctx.world:
            return
        target = ctx.world.get_npc_by_id(ally.object_id)
        if target:
            ctx.self_npc.interact(target, 0.05, 0.03, 0.02, ctx.current_time)
            target.interact(ctx.self_npc, 0.04, 0.03, 0.02, ctx.current_time)
            salient = ctx.self_npc.memory.get_most_salient()
            if salient:
                target.witness_event(salient.event,
                                     [ctx.self_npc.identity.npc_id], ctx.current_time)
        ctx.world.publish_event(SimEvent(
            self.action_type, ctx.self_npc.identity.npc_id,
            ally.object_id if ally else None,
            f"{ctx.self_npc.identity.display_name} socializes.",
            0.2, ctx.current_time, ctx.self_npc.position, ctx.rng, "social"))


# ═══════════════════════════════════════════════════════════════════════════════
# TRADE
# ═══════════════════════════════════════════════════════════════════════════════

class TradeAction(IAction):
    action_id = "trade"
    action_type = "Trade"

    def is_valid(self, ctx: ActionContext) -> bool:
        npc = ctx.self_npc
        has_gold = npc.inventory.has(ItemIds.GOLD)
        has_food = npc.inventory.has(ItemIds.FOOD)
        return (has_gold or has_food) and (ctx.has_percept("Ally") or ctx.has_percept("NPC"))

    def evaluate(self, ctx: ActionContext) -> float:
        trait_mod = ctx.self_npc.traits.get_weight_modifier(self.action_type)
        return 0.4 * trait_mod

    def execute(self, ctx: ActionContext) -> None:
        ally = ctx.get_top_percept("Ally") or ctx.get_top_percept("NPC")
        if not ally or not ctx.world:
            return
        target = ctx.world.get_npc_by_id(ally.object_id)
        npc = ctx.self_npc
        if target and npc.inventory.has(ItemIds.GOLD) and target.inventory.has(ItemIds.FOOD):
            npc.inventory.remove(ItemIds.GOLD, 1)
            target.inventory.add(ItemIds.GOLD, 1)
            target.inventory.remove(ItemIds.FOOD, 1)
            npc.inventory.add(ItemIds.FOOD, 1)
            npc.interact(target, 0.05, 0.03, 0.03, ctx.current_time)
            target.interact(npc, 0.05, 0.03, 0.03, ctx.current_time)
        ctx.world.publish_event(SimEvent(
            self.action_type, npc.identity.npc_id,
            ally.object_id if ally else None,
            f"{npc.identity.display_name} trades.",
            0.25, ctx.current_time, npc.position, ctx.rng, "economy"))


# ═══════════════════════════════════════════════════════════════════════════════
# WORK
# ═══════════════════════════════════════════════════════════════════════════════

class WorkAction(IAction):
    action_id = "work"
    action_type = "Work"

    def is_valid(self, ctx: ActionContext) -> bool:
        return ctx.self_npc.vitals.energy_norm > 0.2

    def evaluate(self, ctx: ActionContext) -> float:
        sched = ctx.self_npc.schedule.preference_at("work", ctx.sim_day_hour)
        consc = ctx.self_npc.psychology.conscientiousness
        return sched * 0.6 + consc * 0.4

    def execute(self, ctx: ActionContext) -> None:
        npc = ctx.self_npc
        npc.vitals.consume_energy(5.0 * ctx.delta_time)
        occ = npc.identity.occupation.lower()
        if occ == "farmer":
            npc.inventory.add(ItemIds.GRAIN, 1)
        elif occ == "merchant":
            npc.inventory.add(ItemIds.GOLD, 1)
        elif occ == "guard":
            pass
        elif occ == "scholar":
            pass
        else:
            npc.inventory.add(ItemIds.TOOLS, 1)
        if ctx.world:
            ctx.world.publish_event(SimEvent(
                self.action_type, npc.identity.npc_id, None,
                f"{npc.identity.display_name} works as {npc.identity.occupation}.",
                0.1, ctx.current_time, npc.position, ctx.rng, "economy"))


# ═══════════════════════════════════════════════════════════════════════════════
# PRAY
# ═══════════════════════════════════════════════════════════════════════════════

class PrayAction(IAction):
    action_id = "pray"
    action_type = "Pray"

    def is_valid(self, ctx: ActionContext) -> bool:
        return ctx.self_npc.traits.has("Devout") or ctx.self_npc.vitals.stress > 0.5

    def evaluate(self, ctx: ActionContext) -> float:
        stress = ctx.self_npc.vitals.stress
        devout = 0.3 if ctx.self_npc.traits.has("Devout") else 0.0
        return min(1.0, stress * 0.5 + devout)

    def execute(self, ctx: ActionContext) -> None:
        npc = ctx.self_npc
        npc.vitals.set_stress(max(0.0, npc.vitals.stress - 0.1 * ctx.delta_time))
        npc.psychology.set_happiness(min(1.0, npc.psychology.happiness + 0.03))
        if ctx.world:
            ctx.world.publish_stimulus_from_action(
                npc.identity.npc_id, npc.position, "Social", "Prayer", 0.3, ctx.current_time)
            ctx.world.publish_event(SimEvent(
                self.action_type, npc.identity.npc_id, None,
                f"{npc.identity.display_name} prays.",
                0.15, ctx.current_time, npc.position, ctx.rng, "spiritual"))


# ═══════════════════════════════════════════════════════════════════════════════
# WALK TO
# ═══════════════════════════════════════════════════════════════════════════════

class WalkToAction(IAction):
    action_id = "walk_to"
    action_type = "WalkTo"

    def is_valid(self, ctx: ActionContext) -> bool:
        return True  # Always valid as fallback idle/wander

    def evaluate(self, ctx: ActionContext) -> float:
        return 0.05  # Low baseline — only selected when nothing else is valid

    def execute(self, ctx: ActionContext) -> None:
        npc = ctx.self_npc
        if not ctx.world:
            return
        # Wander randomly within wander_radius
        dx = ctx.rng.next_float(-1.0, 1.0)
        dz = ctx.rng.next_float(-1.0, 1.0)
        direction = SimVector3(dx, 0, dz).normalized()
        speed = 2.0
        new_pos = npc.position + direction * speed * ctx.delta_time
        ctx.world.move_npc(npc.identity.npc_id, new_pos)
        npc.vitals.consume_energy(0.5 * ctx.delta_time)
