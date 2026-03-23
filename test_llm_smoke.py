"""Quick smoke test for all LLM modules."""
import sys
sys.path.insert(0, '.')

errors = []

def check(label, fn):
    try:
        fn()
        print(f"[OK] {label}")
    except Exception as e:
        print(f"[FAIL] {label}: {e}")
        errors.append(label)

# Test 1: imports
def t1():
    from npc_sim.llm.world_registry import WorldRegistry, get_default_registry
    from npc_sim.llm.llm_backend import OllamaBackend, MockBackend, LLMResponse
    from npc_sim.llm.llm_request_queue import LLMRequestQueue, Priority
check("LLM module imports", t1)

# Test 2: WorldRegistry
def t2():
    from npc_sim.llm.world_registry import WorldRegistry
    wr = WorldRegistry(100)
    r = wr.resolve(54.2, 48.7)
    assert "zone" in r and "landmark" in r, f"Bad resolve: {r}"
    print(f"    resolve(54.2,48.7) → {r}")
check("WorldRegistry", t2)

# Test 3: MockBackend
def t3():
    from npc_sim.llm.llm_backend import MockBackend
    backend = MockBackend("gather")
    assert backend.is_available()
    resp = backend.call("npc_test", '{"valid_actions":["gather"]}')
    assert resp.action_id == "gather", f"Expected gather, got {resp.action_id}"
check("MockBackend", t3)

# Test 3b: OllamaBackend — gerçek API çağrısı
def t3b():
    from npc_sim.llm.llm_backend import OllamaBackend

    backend = OllamaBackend(
        model="hermes-lora",                 # ollama create ile verdiğin model adı
        base_url="http://localhost:11434",   # /v1 olmadan
    )

    # Ollama servisi ayakta mı?
    assert backend.is_available(), (
        "Ollama servisi bulunamadı! 'ollama serve' komutunu çalıştır."
    )

    # NPC karar payload'ı
    payload = {
        "npc_id": "npc_smoke_01",
        "hunger": 0.75,
        "energy": 0.4,
        "social_need": 0.2,
        "location": {"zone": "forest", "landmark": "old_mill"},
        "nearby_npcs": ["npc_02"],
        "valid_actions": ["gather", "eat", "sleep", "socialize", "walk_to"],
    }

    import json
    resp = backend.call("npc_smoke_01", json.dumps(payload, ensure_ascii=False), timeout=10.0)

    # Temel doğrulamalar
    assert resp.npc_id,    "npc_id boş döndü"
    assert resp.action_id, "action_id boş döndü"
    assert resp.action_id in payload["valid_actions"], (
        f"Geçersiz action_id: '{resp.action_id}' — valid_actions: {payload['valid_actions']}"
    )

    print(f"    npc={resp.npc_id}")
    print(f"    action={resp.action_id}  target={resp.target_id}")
    print(f"    emotion={resp.emotion}")
    print(f"    reasoning={resp.reasoning[:80]}...")
    print(f"    latency={resp.latency_ms:.0f}ms")

check("OllamaBackend (gerçek API)", t3b)

# Test 4: SimConfig LLM fields
def t4():
    from npc_sim.core.sim_config import SimulationConfig
    cfg = SimulationConfig()
    assert not cfg.llm_enabled
    assert cfg.llm_backend == "ollama"
    assert cfg.llm_tick_every == 5
    print(f"    backend={cfg.llm_backend} model={cfg.llm_model}")
check("SimConfig LLM fields", t4)

# Test 5: SimulationManager LLM api
def t5():
    from npc_sim.simulation.simulation_manager import SimulationManager, _LLM_AVAILABLE
    mgr = SimulationManager()
    stats = mgr.get_llm_stats_full()
    assert "queue" in stats and "per_npc" in stats
    print(f"    _LLM_AVAILABLE={_LLM_AVAILABLE}")
check("SimulationManager LLM api", t5)

# Test 6: generator produces valid JSON
def t6():
    import json, random, os
    random.seed(42)
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "Stateful_NPC", "generator"))
    from npc_sim_generator_v2 import build_example, NPC_SIM_ACTIONS
    ex = build_example()
    assert "text" in ex
    # extract assistant block
    parts = ex["text"].split("<|start_header_id|>assistant<|end_header_id|>")
    assert len(parts) == 2
    asst = parts[1].replace("<|eot_id|>", "").strip()
    data = json.loads(asst)
    assert data["selected_action"]["action_id"] in NPC_SIM_ACTIONS
    print(f"    action={data['selected_action']['action_id']} emotion={data['emotion']}")
check("Dataset generator v2", t6)

print()
if errors:
    print(f"FAILED: {errors}")
    sys.exit(1)
else:
    print("All checks passed!")