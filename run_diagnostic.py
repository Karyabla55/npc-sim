#!/usr/bin/env python
# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""
run_diagnostic.py — Headless 6 sim-hour diagnostic run for NPC-Sim.

Usage:
    cd d:\DeepLearning\Projects\npc-sim
    python run_diagnostic.py

Runs 5 archetypes (Farmer, Guard, Merchant, Priest, Scholar) with
starting inventory food=2, water=2, medicine=1 for exactly 6 sim-hours
(21,600 sim-seconds at time_scale=1.0), logging every tick to
logs/sim_full.csv, then prints a console summary.
"""

from __future__ import annotations
import math
import os
import sys
import time
from collections import Counter, defaultdict

# ── Ensure project root is on path ───────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

# ── Simulation imports ────────────────────────────────────────────────────────
from npc_sim.core.sim_config import SimulationConfig
from npc_sim.core.sim_vector3 import SimVector3
from npc_sim.simulation.simulation_manager import SimulationManager
from npc_sim.npc.npc_factory import NPCFactory
from npc_sim.npc.inventory import ItemIds
from npc_sim.simulation.world_map import WorldMap
from npc_sim.decisions.actions.builtin import (
    EatAction, DrinkAction, SleepAction, FleeAction, GatherAction, HealAction,
    AttackAction, SocializeAction, TradeAction, WorkAction, PrayAction, WalkToAction,
)

# ── Configuration ─────────────────────────────────────────────────────────────
TICK_RATE       = 10.0                      # ticks per real second (virtual)
REAL_DELTA      = 1.0 / TICK_RATE          # 0.1s per tick

import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Headless diagnostic run for NPC-Sim")
    parser.add_argument("--hours", type=float, default=6.0, help="sim-hours to run (default=6)")
    parser.add_argument("--speed", type=float, default=1.0, help="time_scale multiplier (default=1)")
    parser.add_argument("--seed", type=int, default=42, help="rng seed (default=42)")
    parser.add_argument("--npc-count", type=int, default=5, dest="npc_count", help="number of NPCs (default=5)")
    return parser.parse_args()


def build_simulation(args) -> SimulationManager:
    config = SimulationConfig(
        seed=args.seed,
        tick_rate=TICK_RATE,
        day_length_seconds=1440.0,
        initial_time_scale=args.speed,
        initial_sim_hour=6.0,
        npc_count=args.npc_count,
        logger_enabled=True,
    )
    mgr = SimulationManager(config)

    # Register all actions
    for cls in [EatAction, DrinkAction, SleepAction, FleeAction, GatherAction,
                HealAction, AttackAction, SocializeAction, TradeAction,
                WorkAction, PrayAction, WalkToAction]:
        mgr.action_library.register(cls())

    rng = mgr.rng

    # Spawn archetypes in a ring
    factory_funcs = [
        NPCFactory.create_farmer,
        NPCFactory.create_guard,
        NPCFactory.create_merchant,
        NPCFactory.create_priest,
        NPCFactory.create_scholar,
    ]
    archetype_labels = ["Farmer", "Guard", "Merchant", "Priest", "Scholar"]

    for i in range(args.npc_count):
        idx = i % len(factory_funcs)
        fn = factory_funcs[idx]
        label = archetype_labels[idx]
        npc = fn(rng)
        # Force occupation label for clarity
        npc.identity.occupation = label

        # Fixed starting inventory: food=2, water=2, medicine=1
        npc.inventory.clear()
        npc.inventory.add(ItemIds.FOOD, 2)
        npc.inventory.add(ItemIds.WATER, 2)
        npc.inventory.add(ItemIds.MEDICINE, 1)

        # Starting vitals: moderate values
        npc.vitals.set_hunger(0.2)
        npc.vitals.set_thirst(0.2)
        npc.vitals.set_energy(npc.vitals.max_energy * 0.8)

        # Assign physical home based on occupation
        home = WorldMap.get_home_for_occupation(npc.identity.occupation)
        npc.home_pos = home
        
        # Add slight jitter to position so they don't perfectly overlap
        angle = (2 * math.pi / args.npc_count) * i if args.npc_count > 0 else 0
        radius = 2.0
        npc.position = SimVector3(home.x + math.cos(angle) * radius,
                                  home.y,
                                  home.z + math.sin(angle) * radius)
        mgr.add_npc(npc)

    sim_seconds = args.hours * (config.day_length_seconds / 24.0)
    print(f"Simulation config: day={config.day_length_seconds}s "
          f"time_scale={config.initial_time_scale} "
          f"hunger_rate={config.hunger_decay_rate} "
          f"thirst_rate={config.thirst_decay_rate} "
          f"energy_rate={config.energy_decay_rate}")
    print(f"NPCs spawned: {[n.identity.display_name for n in mgr.world.all_npcs]}")
    print(f"Target: {args.hours}h = {sim_seconds:.0f} sim-seconds")
    print(f"Log: {os.path.abspath(mgr.logger.log_path)}")
    print("-" * 60)

    return mgr


def run(mgr: SimulationManager, args) -> None:
    """Drive the simulation loop for exactly args.hours * configured sim-seconds."""
    sim_elapsed = 0.0
    sim_seconds = args.hours * (mgr.config.day_length_seconds / 24.0)
    t0 = time.perf_counter()
    tick = 0
    report_interval = int(TICK_RATE * 60 * 30)  # print progress every 30 sim-min

    while sim_elapsed < sim_seconds:
        mgr.tick(REAL_DELTA)
        sim_elapsed += REAL_DELTA * args.speed
        tick += 1

        if tick % report_interval == 0:
            h = sim_elapsed / (mgr.config.day_length_seconds / 24.0)
            alives = sum(1 for n in mgr.world.all_npcs if n.vitals.is_alive)
            print(f"  [{h:.1f}h] tick={tick}  alive={alives}/{args.npc_count}  "
                  f"sim_t={sim_elapsed:.0f}s")

    real_elapsed = time.perf_counter() - t0
    print(f"\nRun complete: {tick} ticks in {real_elapsed:.1f}s real time")
    mgr.logger.close()


def print_summary(log_path: str) -> None:
    """Read logs/sim_full.csv and print the diagnostic summary."""
    import csv

    if not os.path.exists(log_path):
        print(f"[ERROR] Log not found: {log_path}")
        return

    rows = []
    with open(log_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    total_rows = len(rows)
    print(f"\n{'='*60}")
    print(f"DIAGNOSTIC SUMMARY — {total_rows} rows in {log_path}")
    print(f"{'='*60}")

    # ── Per-NPC collection ──
    npc_names   = {}         # npc_id → display_name
    action_dist = Counter()  # action → count (global)
    npc_actions = defaultdict(Counter)    # npc_id → Counter
    npc_last_vital = {}      # npc_id → last row
    npc_dead   = {}          # npc_id → death_cause
    npc_alive  = {}          # npc_id → is_alive at end

    for row in rows:
        nid  = row["npc_id"]
        name = row["npc_name"]
        npc_names[nid] = name

        act = row.get("action_selected", "")
        if act:
            action_dist[act] += 1
            npc_actions[nid][act] += 1

        if row.get("event_type") == "Death" and nid not in npc_dead:
            npc_dead[nid] = row.get("death_cause", "unknown")

        npc_alive[nid]      = row.get("is_alive", "1")
        npc_last_vital[nid] = row

    # ── 1. Survivors and deaths ──
    print("\n── 1. Survivors & Deaths ─────────────────────────────────")
    for nid, name in npc_names.items():
        alive_flag = npc_alive.get(nid, "1") == "1"
        if alive_flag:
            last = npc_last_vital.get(nid, {})
            print(f"  ALIVE   {name:20s}  HP={last.get('hp','?'):>6}  "
                  f"hunger={last.get('hunger','?'):>7}  "
                  f"thirst={last.get('thirst','?'):>7}  "
                  f"energy={last.get('energy','?'):>7}")
        else:
            cause = npc_dead.get(nid, "unknown")
            print(f"  DEAD    {name:20s}  cause={cause}")

    # ── 2. Action distribution ──
    print("\n── 2. Action Distribution (global) ───────────────────────")
    total_acts = sum(action_dist.values()) or 1
    for act, cnt in action_dist.most_common():
        print(f"  {act:15s}  {cnt:6d}  ({cnt/total_acts*100:.1f}%)")

    # ── 3. NPCs that never drank ──
    print("\n── 3. NPCs that never executed DrinkAction ───────────────")
    no_drink = [name for nid, name in npc_names.items()
                if npc_actions[nid].get("Drink", 0) == 0]
    if no_drink:
        for n in no_drink:
            print(f"  NEVER DRANK: {n}")
    else:
        print("  All NPCs drank at least once ✓")

    # ── 4. NPCs that never ate ──
    print("\n── 4. NPCs that never executed EatAction ─────────────────")
    no_eat = [name for nid, name in npc_names.items()
              if npc_actions[nid].get("Eat", 0) == 0]
    if no_eat:
        for n in no_eat:
            print(f"  NEVER ATE: {n}")
    else:
        print("  All NPCs ate at least once ✓")

    # ── 5. LLM stats ──
    print("\n── 5. LLM Stats ──────────────────────────────────────────")
    llm_calls    = sum(1 for r in rows if r.get("llm_called") == "1")
    llm_fallback = sum(1 for r in rows if r.get("llm_fallback") == "1")
    fb_rate = llm_fallback / llm_calls * 100 if llm_calls else 0
    print(f"  Total LLM calls  : {llm_calls}")
    print(f"  Total fallbacks  : {llm_fallback}  ({fb_rate:.1f}%)")

    # ── 6. Row count ──
    print(f"\n── 6. Log File ───────────────────────────────────────────")
    print(f"  {log_path}")
    print(f"  Rows: {total_rows}")

    # ── Pass / Fail checklist ──
    print(f"\n── PASS/FAIL Checklist ───────────────────────────────────")
    deaths = [nid for nid, alive in npc_alive.items() if alive != "1"]
    hunger_deaths = [npc_names.get(n, n) for n in npc_dead
                     if "hunger" in npc_dead[n].lower() or "thirst" in npc_dead[n].lower()]

    checks = [
        ("Zero NPC deaths from hunger/thirst",
         len(hunger_deaths) == 0,
         f"Deaths: {hunger_deaths}" if hunger_deaths else ""),
        (f"All {args.npc_count} NPCs alive at end",
         len(deaths) == 0,
         f"Dead: {[npc_names.get(d, d) for d in deaths]}"),
        ("DrinkAction present in distribution",
         "Drink" in action_dist,
         f"drink_count={action_dist.get('Drink', 0)}"),
        ("EatAction present in distribution",
         "Eat" in action_dist,
         f"eat_count={action_dist.get('Eat', 0)}"),
        ("LLM fallback rate ≤ 5%",
         fb_rate <= 5.0 or llm_calls == 0,
         f"rate={fb_rate:.1f}%"),
    ]

    all_pass = True
    for desc, passed, detail in checks:
        status = "PASS ✓" if passed else "FAIL ✗"
        if not passed:
            all_pass = False
        line = f"  [{status}] {desc}"
        if detail:
            line += f"  | {detail}"
        print(line)

    print(f"\n{'SIMULATION: ALL CHECKS PASSED ✓' if all_pass else 'SIMULATION: ISSUES FOUND — see report above'}")
    print("=" * 60)


if __name__ == "__main__":
    args = parse_args()
    mgr = build_simulation(args)
    run(mgr, args)
    print_summary(mgr.logger.log_path)
