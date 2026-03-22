# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Flask + SocketIO server for the NPC-Sim web dashboard."""

from __future__ import annotations
import time
import threading
import math
from flask import Flask, send_from_directory, jsonify, request
from flask_socketio import SocketIO

from npc_sim.core.sim_config import SimulationConfig
from npc_sim.core.sim_vector3 import SimVector3
from npc_sim.simulation.simulation_manager import SimulationManager
from npc_sim.llm.world_registry import WorldRegistry
from npc_sim.simulation.world_map import WorldMap
from npc_sim.npc.inventory import ItemIds
from npc_sim.events.stimulus import Stimulus, StimulusType
from npc_sim.npc.npc_factory import NPCFactory
from npc_sim.decisions.actions.builtin import (
    EatAction, DrinkAction, SleepAction, FleeAction, GatherAction, HealAction,
    AttackAction, SocializeAction, TradeAction, WorkAction, PrayAction, WalkToAction,
)

# ── Flask app ──
app = Flask(__name__, static_folder="static", static_url_path="")
app.config["SECRET_KEY"] = "npc-sim-secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ── Simulation state ──
manager: SimulationManager | None = None
sim_thread: threading.Thread | None = None
sim_running = False
sim_paused = False


def create_simulation(seed: int = 42, npc_count: int = 5, start_hour: float = 6.0, 
                      time_scale: float = 1.0, llm_enabled: bool = False, 
                      logger_enabled: bool = True) -> SimulationManager:
    config = SimulationConfig(
        seed=seed,
        tick_rate=10.0,
        day_length_seconds=1440.0,
        initial_time_scale=time_scale,
        initial_sim_hour=start_hour,
        npc_count=npc_count,
        logger_enabled=logger_enabled,
        llm_enabled=llm_enabled,
        max_npc_count=max(50, npc_count * 2),
    )
    mgr = SimulationManager(config)

    # Register all built-in actions
    for action_cls in [EatAction, DrinkAction, SleepAction, FleeAction, GatherAction, HealAction,
                       AttackAction, SocializeAction, TradeAction, WorkAction, PrayAction, WalkToAction]:
        mgr.action_library.register(action_cls())

    # Spawn diverse NPCs at spread positions
    rng = mgr.rng
    factory_funcs = [
        NPCFactory.create_farmer,
        NPCFactory.create_guard,
        NPCFactory.create_merchant,
        NPCFactory.create_priest,
        NPCFactory.create_scholar,
    ]
    archetype_labels = ["Farmer", "Guard", "Merchant", "Priest", "Scholar"]

    npcs = []
    for i in range(npc_count):
        idx = i % len(factory_funcs)
        fn = factory_funcs[idx]
        label = archetype_labels[idx]
        npc = fn(rng)
        npc.identity.occupation = label
        home = WorldMap.get_home_for_occupation(label)
        npc.home_pos = home
        npcs.append(npc)

    for i, npc in enumerate(npcs):
        angle = (2 * math.pi / npc_count) * i if npc_count > 0 else 0
        radius = 2.0
        
        npc.position = SimVector3(npc.home_pos.x + math.cos(angle) * radius,
                                  npc.home_pos.y,
                                  npc.home_pos.z + math.sin(angle) * radius)
        
        # Face origin roughly
        npc.forward = (SimVector3(50, 0, 50) - npc.position).normalized()
        npc.inventory.add(ItemIds.FOOD, rng.next_int(1, 4))
        npc.inventory.add(ItemIds.WATER, rng.next_int(1, 3))
        npc.inventory.add(ItemIds.GOLD, rng.next_int(0, 3))
        npc.vitals.set_hunger(rng.next_float(0.1, 0.5))
        npc.vitals.set_thirst(rng.next_float(0.1, 0.4))
        mgr.add_npc(npc)

    return mgr


def simulation_loop():
    global manager, sim_running, sim_paused
    tick_interval_base = 0.1  # 100ms base interval (tick_rate=10)

    while sim_running:
        if sim_paused or manager is None:
            time.sleep(0.1)
            continue

        real_delta = tick_interval_base
        state = manager.tick(real_delta)

        if state:
            socketio.emit("tick", state)

        time.sleep(tick_interval_base)


# ── Routes ──

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/state")
def get_state():
    if manager:
        return jsonify(manager.get_state_snapshot())
    return jsonify({})

@app.route("/api/start", methods=["POST"])
def start_sim():
    global manager, sim_running, sim_thread, sim_paused
    
    if sim_running:
        return jsonify({"error": "Simulation already running"}), 400
        
    data = request.json or {}
    
    start_hour_str = data.get("start_hour", "06:00")
    try:
        h, m = map(int, start_hour_str.split(":"))
        start_hour = h + m / 60.0
    except:
        start_hour = 6.0
        
    seed = data.get("seed", 42)
    if seed == "" or seed is None:
        import random
        seed = random.randint(1, 1000000)
    else:
        try: seed = int(seed)
        except: seed = 42
    
    npc_count = int(data.get("npc_count", 5))
    time_scale = float(data.get("time_scale", 1.0))
    llm_enabled = bool(data.get("llm_enabled", False))
    logger_enabled = bool(data.get("logger_enabled", True))
    
    manager = create_simulation(seed=seed, npc_count=npc_count, start_hour=start_hour, 
                                time_scale=time_scale, llm_enabled=llm_enabled, 
                                logger_enabled=logger_enabled)
                                
    sim_paused = False
    sim_running = True
    sim_thread = threading.Thread(target=simulation_loop, daemon=True)
    sim_thread.start()
    
    return jsonify({"status": "started", "speed": manager.clock.time_scale})


@app.route("/api/control", methods=["POST"])
def control():
    global sim_paused, manager, sim_running, sim_thread
    data = request.json or {}

    if "paused" in data:
        sim_paused = data["paused"]
    if "speed" in data and manager:
        speed = max(0.1, min(float(data["speed"]), 300.0))
        manager.clock.set_time_scale(speed)
    if "reset" in data and data["reset"]:
        sim_running = False
        if sim_thread:
            sim_thread.join(timeout=2)
        manager = None # Clear state for next /api/start
        sim_paused = False

    current_speed = manager.clock.time_scale if manager else 1.0
    return jsonify({"paused": sim_paused, "speed": current_speed})


# ── SocketIO events ──

@socketio.on("connect")
def on_connect():
    if manager:
        socketio.emit("tick", manager.get_state_snapshot())


@socketio.on("inject_stimulus")
def on_inject_stimulus(data):
    if not manager:
        return
    stim_type_map = {
        "Visual": StimulusType.VISUAL,
        "Audio": StimulusType.AUDIO,
        "Social": StimulusType.SOCIAL,
        "Olfactory": StimulusType.OLFACTORY,
    }
    st = stim_type_map.get(data.get("type", "Visual"), StimulusType.VISUAL)
    pos = data.get("position", {"x": 50, "y": 0, "z": 50})
    manager.world.publish_stimulus(Stimulus(
        st, data.get("source_id", "manual"),
        SimVector3(pos["x"], pos["y"], pos["z"]),
        float(data.get("intensity", 0.8)),
        manager.clock.current_time,
        tag=data.get("tag", "Threat"),
    ))


# ── Main ──

if __name__ == "__main__":
    print("\n  ╔══════════════════════════════════════════════╗")
    print("  ║     NPC-Sim  •  http://localhost:5000        ║")
    print("  ║     by Sadık Abdusselam Albayrak             ║")
    print("  ╚══════════════════════════════════════════════╝\n")
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)
