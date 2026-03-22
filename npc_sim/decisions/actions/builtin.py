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
        # Urgency multiplier: score rises steeply past threshold so it beats Work
        # at hunger>0.65, Eat score > 0.80 (Work is typically 0.6-0.9)
        urgency = 1.0 + max(0.0, (h - 0.35)) * 3.0
        return min(1.0, h * h * urgency)

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
# DRINK
# ═══════════════════════════════════════════════════════════════════════════════

class DrinkAction(IAction):
    action_id = "drink"
    action_type = "Drink"

    _THIRST_THRESHOLD = 0.35
    _THIRST_REDUCTION = 0.60
    _HAPPINESS_GAIN = 0.05

    def is_valid(self, ctx: ActionContext) -> bool:
        if ctx.self_npc.vitals.thirst < self._THIRST_THRESHOLD:
            return False
        return ctx.self_npc.inventory.has(ItemIds.WATER)

    def evaluate(self, ctx: ActionContext) -> float:
        t = ctx.self_npc.vitals.thirst
        # Same urgency curve as EatAction — survival beats Work at thirst>0.65
        urgency = 1.0 + max(0.0, (t - 0.35)) * 3.0
        return min(1.0, t * t * urgency)

    def execute(self, ctx: ActionContext) -> None:
        v = ctx.self_npc.vitals
        p = ctx.self_npc.psychology
        ctx.self_npc.inventory.remove(ItemIds.WATER, 1)
        v.set_thirst(max(0.0, v.thirst - self._THIRST_REDUCTION))
        p.set_happiness(min(1.0, p.happiness + self._HAPPINESS_GAIN))
        for g in ctx.goals.get_by_type(GoalType.FIND_WATER):
            g.set_progress(1.0)
        if ctx.world:
            ctx.world.publish_event(SimEvent(
                self.action_type, ctx.self_npc.identity.npc_id, None,
                f"{ctx.self_npc.identity.display_name} drinks water.",
                0.2, ctx.current_time, ctx.self_npc.position, ctx.rng, "health"))


# ═══════════════════════════════════════════════════════════════════════════════
# SLEEP
# ═══════════════════════════════════════════════════════════════════════════════

class SleepAction(IAction):
    action_id = "sleep"
    action_type = "Sleep"

    def is_valid(self, ctx: ActionContext) -> bool:
        v = ctx.self_npc.vitals
        # Never sleep when dying of hunger or thirst — survival takes priority
        if v.hunger > 0.75 or v.thirst > 0.75:
            return False
        return v.energy_norm < 0.35   # tighter threshold: was 0.4

    def evaluate(self, ctx: ActionContext) -> float:
        fatigue      = 1.0 - ctx.self_npc.vitals.energy_norm
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
        inv = ctx.self_npc.inventory
        # Only gather if genuinely low on the resource AND not already stocked.
        # Cap: < 5 items so NPCs don't hoard infinitely.
        needs_food  = v.hunger > 0.3 and inv.get_amount(ItemIds.FOOD)  < 5
        needs_water = v.thirst > 0.3 and inv.get_amount(ItemIds.WATER) < 5
        return needs_food or needs_water

    def evaluate(self, ctx: ActionContext) -> float:
        v   = ctx.self_npc.vitals
        inv = ctx.self_npc.inventory
        urgency = max(v.hunger, v.thirst)
        has_food  = inv.has(ItemIds.FOOD)
        has_water = inv.has(ItemIds.WATER)
        # If inventory is empty: Gather is the ONLY way to get resources; score must
        # beat WalkTo (which just wanders with no percepts in most maps).
        if not has_food and not has_water:
            return min(1.0, urgency * 0.85)  # beats WalkTo cap of 0.5
        # Both stocked: near-zero so Eat/Drink win
        if has_food and has_water:
            return urgency * 0.08
        # Partially stocked: medium score
        return urgency * 0.55

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

    # Maps GoalType string → percept tag to look for
    _GOAL_TAG_MAP = {
        GoalType.FIND_FOOD:  "Food",
        GoalType.FIND_WATER: "Water",
        GoalType.HEAL:       "Resource",
    }

    def is_valid(self, ctx: ActionContext) -> bool:
        return True  # Always valid as fallback idle/wander

    def evaluate(self, ctx: ActionContext) -> float:
        v   = ctx.self_npc.vitals
        inv = ctx.self_npc.inventory
        # High urgency only when desperate AND inventory empty AND a percept exists to
        # actually move toward.  Cap at 0.5 so Gather (0.85 when inv empty) always wins
        # when gathering is available — WalkTo wanders randomly but can't produce items.
        if v.hunger > 0.65 and not inv.has(ItemIds.FOOD):
            target = ctx.get_top_percept("Food")
            if target:
                return min(1.0, v.hunger * 0.85)   # directed move to Food percept
            return min(0.5, v.hunger * 0.5)         # random wander — Gather should win
        if v.thirst > 0.65 and not inv.has(ItemIds.WATER):
            target = ctx.get_top_percept("Water")
            if target:
                return min(1.0, v.thirst * 0.85)    # directed move to Water percept
            return min(0.5, v.thirst * 0.5)         # random wander — Gather should win
        return 0.05   # low baseline — pure wandering

    def execute(self, ctx: ActionContext) -> None:
        npc = ctx.self_npc
        if not ctx.world:
            return

        speed = 2.0
        direction = None

        # Move toward a percept matching the top active goal
        top_goal = npc.goals.get_top_goal()
        if top_goal:
            target_tag = self._GOAL_TAG_MAP.get(top_goal.goal_type)
            if target_tag:
                target_percept = ctx.get_top_percept(target_tag)
                if target_percept:
                    delta = target_percept.last_known_position - npc.position
                    if delta.magnitude > 0.5:  # don't jitter when already there
                        direction = delta.normalized()

        # Fallback: random wander
        if direction is None:
            dx = ctx.rng.next_float(-1.0, 1.0)
            dz = ctx.rng.next_float(-1.0, 1.0)
            direction = SimVector3(dx, 0, dz).normalized()

        new_pos = npc.position + direction * speed * ctx.delta_time
        ctx.world.move_npc(npc.identity.npc_id, new_pos)
        npc.vitals.consume_energy(0.5 * ctx.delta_time)
