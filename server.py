# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""Flask + SocketIO server for the NPC-Sim web dashboard."""

from __future__ import annotations
import time
import threading
from flask import Flask, send_from_directory, jsonify, request
from flask_socketio import SocketIO

from npc_sim.core.sim_config import SimulationConfig
from npc_sim.core.sim_vector3 import SimVector3
from npc_sim.simulation.simulation_manager import SimulationManager
from npc_sim.npc.npc_factory import NPCFactory
from npc_sim.npc.inventory import ItemIds
from npc_sim.events.stimulus import Stimulus, StimulusType
from npc_sim.decisions.actions.builtin import (
    EatAction, SleepAction, FleeAction, GatherAction, HealAction,
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
sim_speed: float = 1.0
sim_paused = False


def create_simulation(seed: int = 42) -> SimulationManager:
    config = SimulationConfig(
        seed=seed,
        tick_rate=10.0,
        day_length_seconds=1440.0,
        initial_time_scale=60.0,
        max_npc_count=50,
    )
    mgr = SimulationManager(config)

    # Register all built-in actions
    for action_cls in [EatAction, SleepAction, FleeAction, GatherAction, HealAction,
                       AttackAction, SocializeAction, TradeAction, WorkAction, PrayAction, WalkToAction]:
        mgr.action_library.register(action_cls())

    # Spawn diverse NPCs at spread positions
    rng = mgr.rng
    npcs = [
        NPCFactory.create_guard(rng, "Aldric", "City Watch"),
        NPCFactory.create_merchant(rng, "Yusuf", "Merchant Guild"),
        NPCFactory.create_civilian(rng, "Linh"),
        NPCFactory.create_scholar(rng, "Elena", "Academy"),
        NPCFactory.create_farmer(rng, "Tomás", "Farmers Guild"),
        NPCFactory.create_priest(rng, "Sister Miriam", "Temple"),
        NPCFactory.create_guard(rng, "Bjorn", "City Watch"),
        NPCFactory.create_merchant(rng, "Fatima", "Merchant Guild"),
        NPCFactory.create_civilian(rng, "Kenji"),
        NPCFactory.create_farmer(rng, "Amara", "Farmers Guild"),
    ]

    for i, npc in enumerate(npcs):
        angle = (i / len(npcs)) * 6.283185
        import math
        radius = 20.0 + rng.next_float(0.0, 15.0)
        x = 50.0 + math.cos(angle) * radius
        z = 50.0 + math.sin(angle) * radius
        npc.position = SimVector3(x, 0, z)
        npc.inventory.add(ItemIds.FOOD, rng.next_int(1, 4))
        npc.inventory.add(ItemIds.GOLD, rng.next_int(0, 3))
        npc.vitals.set_hunger(rng.next_float(0.1, 0.5))
        mgr.add_npc(npc)

    return mgr


def simulation_loop():
    global manager, sim_running, sim_paused, sim_speed
    tick_interval_base = 0.1  # 100ms base interval

    while sim_running:
        if sim_paused or manager is None:
            time.sleep(0.1)
            continue

        real_delta = tick_interval_base / max(0.1, sim_speed)
        state = manager.tick(1.0 / manager.config.tick_rate)

        if state:
            socketio.emit("tick", state)

        time.sleep(max(0.016, real_delta))


# ── Routes ──

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/state")
def get_state():
    if manager:
        return jsonify(manager.get_state_snapshot())
    return jsonify({})


@app.route("/api/control", methods=["POST"])
def control():
    global sim_paused, sim_speed, manager, sim_running, sim_thread
    data = request.json or {}

    if "paused" in data:
        sim_paused = data["paused"]
    if "speed" in data:
        sim_speed = max(0.1, min(float(data["speed"]), 100.0))
    if "reset" in data and data["reset"]:
        seed = data.get("seed", 42)
        sim_running = False
        if sim_thread:
            sim_thread.join(timeout=2)
        manager = create_simulation(seed)
        sim_paused = False
        sim_running = True
        sim_thread = threading.Thread(target=simulation_loop, daemon=True)
        sim_thread.start()

    return jsonify({"paused": sim_paused, "speed": sim_speed})


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
    manager = create_simulation(seed=42)
    sim_running = True
    sim_thread = threading.Thread(target=simulation_loop, daemon=True)
    sim_thread.start()
    print("\n  ╔══════════════════════════════════════════════╗")
    print("  ║     NPC-Sim  •  http://localhost:5000        ║")
    print("  ║     by Sadık Abdusselam Albayrak             ║")
    print("  ╚══════════════════════════════════════════════╝\n")
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)
