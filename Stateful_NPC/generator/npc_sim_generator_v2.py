# Copyright 2025-2026 Sadık Abdusselam Albayrak
# Licensed under the Apache License, Version 2.0
"""
Upgraded NPC-Sim dataset generator v3.

Changes vs v2:
  - Added "drink" action (mirrors eat, consumes water)
  - Added water to NPC inventory generation
  - ~15% intent deviation examples: biologically optimal action overridden
    by social context, curiosity, low mood, or active conversation
  - "sched" field in NPC state payload (P3 Option B: schedule as soft suggestion)
  - Corrected dataset counts: 20k train / 2k test

Output format: Llama-3 / custom model instruct chat format (JSONL)
Each line: {"text": "<|begin_of_text|><|start_header_id|>system<|end_header_id|>..."}
"""

from __future__ import annotations
import json
import os
import random
import sys
import uuid

# ─────────────────────────────────────────────────────────────────────────────
# Roles and Personalities
# ─────────────────────────────────────────────────────────────────────────────

ROLES = [
    "Guard", "Merchant", "Priest", "Farmer", "Scholar",
    "Blacksmith", "Thief", "Knight", "Wizard", "Innkeeper",
    "Goblin", "Bandit", "King", "Herbalist", "Bard",
]

ARCHETYPES = {
    "Brave": {
        "b5": {"e": 0.7, "a": 0.5, "c": 0.8, "n": 0.2, "o": 0.4},
        "traits": ["Brave", "Loyal"],
    },
    "Cunning": {
        "b5": {"e": 0.5, "a": 0.3, "c": 0.6, "n": 0.3, "o": 0.7},
        "traits": ["Cunning", "Greedy"],
    },
    "Fearful": {
        "b5": {"e": 0.2, "a": 0.6, "c": 0.5, "n": 0.8, "o": 0.3},
        "traits": ["Cautious", "Anxious"],
    },
    "Honorable": {
        "b5": {"e": 0.6, "a": 0.8, "c": 0.9, "n": 0.1, "o": 0.5},
        "traits": ["Honorable", "Devout"],
    },
    "Aggressive": {
        "b5": {"e": 0.8, "a": 0.2, "c": 0.4, "n": 0.6, "o": 0.3},
        "traits": ["Aggressive", "Wrathful"],
    },
}

ZONES = [
    {"zone": "MarketSquare", "landmark": "CentralFountain"},
    {"zone": "Tavern",        "landmark": "OldOakSign"},
    {"zone": "Temple",        "landmark": "StoneShrineGate"},
    {"zone": "Barracks",      "landmark": "ArmoryDoor"},
    {"zone": "WildernessEdge","landmark": "BrokenMilestone"},
    {"zone": "FarmLands",     "landmark": "MillWheel"},
    {"zone": "MarketDistrict","landmark": "CityGates"},
]

NPC_SIM_ACTIONS = [
    "eat", "drink", "sleep", "flee", "gather", "heal",
    "attack", "socialize", "trade", "work", "pray", "walk_to",
]

# ── Schedule presets per occupation (work_start, work_end, sleep_start, wake, social_hour)
SCHEDULE_PRESETS = {
    "Guard":      (6, 14, 21, 5, 16),
    "Merchant":   (9, 19, 23, 8, 20),
    "Scholar":    (8, 20, 24, 7, 18),
    "Farmer":     (5, 17, 20, 4, 18),
    "Priest":     (7, 13, 21, 5, 14),
    "Blacksmith": (7, 17, 22, 6, 19),
    "Knight":     (6, 16, 22, 5, 17),
    "Innkeeper":  (10, 23, 2, 9, 20),
    "Bard":       (14, 24, 3, 10, 21),
    "Thief":      (20, 3,  8, 16, 22),
}
_DEFAULT_SCHED = (9, 17, 22, 7, 19)


def _get_sched(role: str, hour: float) -> dict:
    ws, we, ss, wk, sh = SCHEDULE_PRESETS.get(role, _DEFAULT_SCHED)
    # Determine suggested activity for this hour
    in_work = (ws <= hour < we) if we <= 24 else (hour >= ws or hour < we - 24)
    in_sleep = (ss <= hour < 24) or (hour < wk)
    near_social = abs(hour - sh) <= 1.5
    if in_sleep:
        suggested = "sleep"
    elif in_work:
        suggested = "work"
    elif near_social:
        suggested = "social"
    else:
        suggested = "idle"
    return {
        "act": suggested,
        "wk_start": ws,
        "wk_end": we,
        "sleep": ss,
        "wake": wk,
    }


ROLE_MEMORIES = {
    "Guard":      ["Nöbette uyuyakaldım, komutan kızdı.", "Bir hırsızı yakaladım, ödül verdiler.",
                   "Şüpheli birini takip ettim, kaçtı.", "Kapıları kapattık, kimse giremez."],
    "Merchant":   ["Yeni bir iksir partisi aldım, kâr ederim.", "Tüccar beni dolandırdı.",
                   "Pazar iyi geçti, kese doldu.", "Mallarım çalındı, mahvoldum."],
    "Priest":     ["Ritüel sırasında meşale söndü, kötü şans.", "Bir hasta iyileşti, tanrıya şükür.",
                   "Kilise hazinesinden para çalındı.", "Bir inanç bunalımı yaşıyorum."],
    "Farmer":     ["Hasat mevsimine yetişemedim.", "Kurt sürüsü koyunlarıma saldırdı.",
                   "Yağmur duası tuttu, tarlalar yeşerdi.", "Köylülerle iyi geçindim."],
    "Scholar":    ["Kadim bir yazıt çevirdim, büyüleyiciydi.", "Kütüphane yangını çıktı, kitaplar yandı.",
                   "Yeni bir formül buldum, sabaha kadar çalıştım."],
    "Blacksmith": ["Çekiç parmağıma düştü, tırnağım morardı.", "Kral'ın kılıcını onardım.",
                   "Kömür bitti, ocağı yakamıyorum."],
    "Thief":      ["Muhafızlardan kıl payı kaçtım.", "Lonca payını veremezsem biterdi.",
                   "Kilitli sandığı açamadım."],
    "Knight":     ["Turnuvayı kazandım.", "Yeminimi bozdum, vicdan azabı çekiyorum.",
                   "Atım sakatlandı."],
    "Wizard":     ["Yeni bir büyü öğrendim.", "İksir deneyi patladı.",
                   "Bir iblis çağırdım, zor gönderdim."],
    "Innkeeper":  ["Sarhoş müşteri ortalığı dağıttı.", "Bu gece oda doldu, kasa şişti."],
    "Goblin":     ["Ateş başında uyuyakaldım, yanarken uyandım.", "Mağaramız işgal edildi."],
    "Bandit":     ["Pususu iyi kurdum, mallar elimde.", "Bir şövalye grubu bizi dağıttı."],
    "King":       ["Vergileri artırdım, halk isyan edebilir.", "Suikast girişimi oldu, kıl payı kurtuldum."],
    "Herbalist":  ["Nadir bir ot buldum, ilaç yapacağım.", "Yanlış doz verdim, hasta kötüleşti."],
    "Bard":       ["Şarkım alkış topladı.", "Bir lord beni sarayına davet etti."],
}
DEFAULT_MEMORIES = [
    "Bugün hava güzel, kuşlar ötüyor.", "Dün gece fırtına çıktı, çatı aktı.",
    "Pazarda fiyatlar çok arttı.", "Karnım aç, günlerdir sıcak yemek yemedim.",
    "Komşumla kavga ettim, moralim bozuk.",
]

THREAT_ENTITIES  = ["wolf", "bandit_01", "soldier_enemy", "ghost", "wild_boar"]
NEUTRAL_ENTITIES = ["merchant_npc", "villager_01", "guard_npc", "priest_npc"]
FOOD_ENTITIES    = ["food_stall", "bread_crate", "apple_tree", "herb_patch"]


def _mood(happiness, fear, anger) -> str:
    if happiness > 0.5: return "Happy"
    if fear      > 0.5: return "Fearful"
    if anger     > 0.5: return "Angry"
    return "Calm"


# ─────────────────────────────────────────────────────────────────────────────
# NPC state generator
# ─────────────────────────────────────────────────────────────────────────────

def _rjitter(base: float, sigma: float = 0.1) -> float:
    return max(0.0, min(1.0, base + random.gauss(0, sigma)))


def generate_npc_state() -> dict:
    arch_name = random.choice(list(ARCHETYPES.keys()))
    arch      = ARCHETYPES[arch_name]
    role      = random.choice(ROLES)
    npc_id    = "npc_" + uuid.uuid4().hex[:8]

    b5     = {k: round(_rjitter(v, 0.12), 2) for k, v in arch["b5"].items()}
    traits = list(arch["traits"])

    # Vitals
    hp      = round(random.uniform(20, 120), 1)
    hp_max  = 120.0
    energy  = round(random.uniform(0.1, 1.0), 2)
    hunger  = round(random.uniform(0.0, 1.0), 2)
    thirst  = round(random.uniform(0.0, 1.0), 2)
    stress  = round(random.uniform(0.0, 0.9), 2)

    # Emotions
    fear      = round(random.uniform(0.0, b5["n"]), 2)
    happiness = round(max(0.0, 0.7 - stress - fear * 0.5), 2)
    anger     = round(random.uniform(0.0, 0.5 + b5["n"] * 0.5), 2)
    mood      = _mood(happiness, fear, anger)

    # Location
    zone_info = random.choice(ZONES)
    pos_x = round(random.uniform(5, 95), 1)
    pos_z = round(random.uniform(5, 95), 1)
    hour  = round(random.uniform(0, 24), 1)

    # Percepts
    percepts  = []
    interrupt = False
    if random.random() < 0.35:   # 35% threat
        threat_id    = random.choice(THREAT_ENTITIES)
        threat_level = round(random.uniform(0.5, 1.0), 2)
        sal          = round(random.uniform(0.6, 1.0), 2)
        percepts.append({"id": threat_id, "tag": "Threat", "sal": sal, "threat": threat_level})
        if threat_level >= 0.8:
            interrupt = True
    if random.random() < 0.4:   # 40% social NPC nearby
        neu_id = random.choice(NEUTRAL_ENTITIES)
        percepts.append({"id": neu_id, "tag": "Social",
                         "sal": round(random.uniform(0.2, 0.7), 2)})
    if random.random() < 0.3:   # 30% food visible
        food_id = random.choice(FOOD_ENTITIES)
        percepts.append({"id": food_id, "tag": "Food",
                         "sal": round(random.uniform(0.3, 0.8), 2)})

    # Memories (1-3)
    pool         = ROLE_MEMORIES.get(role, DEFAULT_MEMORIES) + DEFAULT_MEMORIES
    num_mems     = random.randint(1, 3)
    selected_mems = random.sample(pool, min(len(pool), num_mems))
    memories = []
    for mem in selected_mems:
        ew  = round(random.uniform(-0.8, 0.8), 2)
        dt  = random.randint(30, 3600)
        if any(w in mem.lower() for w in ["çalındı", "saldırdı", "kötü", "kızdı", "yanar"]):
            ew = -abs(ew)
        memories.append({"evt": "Memory", "desc": mem[:80], "ew": ew, "dt": dt})

    # Beliefs
    beliefs = []
    if percepts and random.random() < 0.5:
        subj = percepts[0]["id"]
        conf = round(random.uniform(0.4, 0.9), 2)
        val  = -0.8 if "Threat" in percepts[0]["tag"] else round(random.uniform(-0.4, 0.4), 2)
        beliefs.append({"subj": subj, "conf": conf, "val": val})

    # Inventory — food AND water
    inv = []
    if random.random() < 0.6:
        inv.append({"id": "food",  "n": random.randint(1, 5)})
    if random.random() < 0.55:
        inv.append({"id": "water", "n": random.randint(1, 4)})
    if random.random() < 0.4:
        inv.append({"id": "gold",  "n": random.randint(1, 50)})
    if random.random() < 0.2:
        inv.append({"id": "medicine", "n": random.randint(1, 3)})

    # Top goal
    goals = []
    if hunger > 0.65:  goals.append("FindFood")
    if thirst > 0.70:  goals.append("FindWater")
    if energy < 0.3:   goals.append("Rest")
    goals_top = goals[0] if goals else None

    return {
        "id":      npc_id,
        "arch":    arch_name,
        "occ":     role,
        "faction": random.choice(["CityWatch", "MerchantGuild", "Bandits", "Church", "Farmers"]),
        "b5":      b5,
        "traits":  traits,
        "vitals":  {"hp": hp, "hp_max": hp_max, "en": energy,
                    "hun": hunger, "thi": thirst, "str": stress},
        "emo":     {"hap": happiness, "fear": fear, "ang": anger, "mood": mood},
        "inv":     inv,
        "time":    {"day": random.randint(1, 10), "hr": hour},
        "pos":     {"x": pos_x, "z": pos_z, **zone_info},
        "sched":   _get_sched(role, hour),       # P3: soft schedule suggestion
        "percepts":  percepts,
        "memories":  memories,
        "beliefs":   beliefs,
        "factions":  {"CityWatch":  round(random.uniform(-0.5, 0.5), 2),
                      "Bandits":    round(random.uniform(-0.8, 0.2), 2)},
        "goals_top": goals_top,
        "interrupt": interrupt,
        "valid_actions": NPC_SIM_ACTIONS,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Standard (biologically-optimal) action selector
# ─────────────────────────────────────────────────────────────────────────────

def _select_action_standard(state: dict) -> tuple[str, str, str | None, str]:
    """Return (action_id, reasoning, dialogue, emotion) — biologically optimal path."""
    v        = state["vitals"]
    emo      = state["emo"]
    percepts = state["percepts"]
    arch     = state["arch"]
    traits   = state["traits"]
    inv_ids  = [i["id"] for i in state["inv"]]
    interrupt = state["interrupt"]
    role      = state["occ"]

    threats    = [p for p in percepts if p.get("tag") == "Threat"]
    top_threat = max(threats, key=lambda p: p["threat"], default=None)

    # ── Interrupt: high threat ────────────────────────────────────────────────
    if interrupt and top_threat:
        thr = top_threat["threat"]
        if arch == "Brave" or "Brave" in traits:
            return ("attack",
                    f"Tehdit yüksek ({thr:.2f}), ama korkuyu yeneceğim. Saldırıyorum — bu benim görevim.",
                    None, "Aggressive")
        return ("flee",
                f"Tehdit {thr:.2f} seviyesinde. Kalbim hızlı çarpıyor. Kaçmak zorundayım.",
                None, "Fearful")

    # ── Critical HP ──────────────────────────────────────────────────────────
    if v["hp"] < 25 and "medicine" in inv_ids:
        return ("heal", "Canım kritik seviyede. İlk önce kendimi iyileştirmeliyim.", None, "Fearful")

    # ── Hunger ───────────────────────────────────────────────────────────────
    if v["hun"] > 0.75:
        if "food" in inv_ids:
            return ("eat",
                    f"Açlık dayanılmaz oldu ({v['hun']:.2f}). Çantamdaki yiyeceği yiyeceğim.",
                    None, "Calm")
        food_p = next((p for p in percepts if p.get("tag") == "Food"), None)
        if food_p:
            return ("gather",
                    f"Açım ama yiyeceğim yok. Yakınlardaki {food_p['id']}'den toplayacağım.",
                    None, "Calm")
        return ("gather", "Yiyecek bulmam lazım, etrafı tarıyorum.", None, "Calm")

    # ── Thirst ───────────────────────────────────────────────────────────────
    if v["thi"] > 0.75:
        if "water" in inv_ids:
            return ("drink",
                    f"Susuzluğum dayanılmaz oldu ({v['thi']:.2f}). Su içiyorum.",
                    None, "Calm")
        return ("gather", "Su bulmam lazım, kaynak arıyorum.", None, "Calm")

    # ── Low energy ───────────────────────────────────────────────────────────
    if v["en"] < 0.25:
        return ("sleep", f"Enerjim bitti ({v['en']:.2f}). Dinlenmem şart.", None, "Tired")

    # ── Role-preferred actions ────────────────────────────────────────────────
    role_map = {
        "Priest":     ("pray",  "Günlük duamı yapmak istiyorum. Ruhum huzur buluyor.",   None, "Devout"),
        "Blacksmith": ("work",  "Ocak hazır, işe devam.",                                None, "Focused"),
        "Farmer":     ("work",  "Tarla bekliyor, çalışmam lazım.",                       None, "Focused"),
        "Scholar":    ("work",  "Araştırmama devam edeceğim.",                           None, "Focused"),
    }
    if role in role_map and random.random() < 0.5:
        return role_map[role]

    # ── Social ───────────────────────────────────────────────────────────────
    social_p = next((p for p in percepts if p.get("tag") == "Social"), None)
    if social_p and emo["hap"] > 0.3 and random.random() < 0.3:
        return ("socialize",
                f"{social_p['id']} yakında. Biraz sohbet etmek istiyorum.",
                random.choice(["Merhaba! Nasılsın?", "Ne haber?", "Güzel bir gün, değil mi?"]),
                "Happy")

    # ── Default wander ────────────────────────────────────────────────────────
    return ("walk_to",
            f"Belirli bir acilim yok. {state['pos']['zone']} civarında dolaşacağım.",
            None, "Calm")


# ─────────────────────────────────────────────────────────────────────────────
# Intent deviation selector (~15% of examples)
# ─────────────────────────────────────────────────────────────────────────────

def _select_action_with_deviation(state: dict) -> tuple[str, str, str | None, str] | None:
    """
    Return an intentional override of the biologically optimal action,
    or None if no deviation case applies for this state.

    Four deviation cases:
      D1 – hun>0.65 + social percept → socialize (eating deferred)
      D2 – en<0.35 + non-threat nearby percept → walk_to (curiosity)
      D3 – work conditions met + low mood/anger → pray or socialize instead
      D4 – gather condition met + social percept → stay in conversation
    """
    v        = state["vitals"]
    emo      = state["emo"]
    percepts = state["percepts"]
    inv_ids  = [i["id"] for i in state["inv"]]
    role     = state["occ"]

    social_p  = next((p for p in percepts if p.get("tag") == "Social"), None)
    non_threat = next((p for p in percepts if p.get("tag") != "Threat"), None)
    sched_act = state["sched"]["act"]

    cases = []

    # D1: Hungry but social is active → consciously defer eating
    if v["hun"] > 0.65 and social_p:
        cases.append((
            "socialize",
            f"Gerçi açım ({v['hun']:.2f}) ama {social_p['id']} burada. Yemek biraz bekleyebilir, "
            f"bu konuşma şu an daha önemli.",
            random.choice(["Merhaba! Ne var ne yok?", "Seni görmek iyi oldu.", "Anlat bakalım!"]),
            "Happy",
        ))

    # D2: Tired but something interesting nearby → curiosity wins
    if v["en"] < 0.35 and non_threat and non_threat.get("tag") != "Threat":
        cases.append((
            "walk_to",
            f"Yorgunum aslında ama {non_threat['id']}'yi merak ettim. "
            f"Uyku biraz bekleyebilir, gidip bir bakayım.",
            None,
            "Calm",
        ))

    # D3: Should be working (schedule says work, energy ok) but mood is low → pray/socialize
    if sched_act == "work" and v["en"] > 0.4 and (emo["hap"] < 0.15 or emo["ang"] > 0.55):
        alt = "pray" if ("Devout" in state["traits"] or role == "Priest") else "socialize"
        if alt == "pray":
            cases.append((
                "pray",
                f"Çalışma saatim ama ruh halim yerinde değil (mutluluk:{emo['hap']:.2f}). "
                f"Çalışmadan önce dua edip kendimi toparlayayım.",
                None, "Calm",
            ))
        elif social_p:
            cases.append((
                "socialize",
                f"Çalışmam gerekirdi ama moralim çok bozuk (öfke:{emo['ang']:.2f}). "
                f"{social_p['id']} ile biraz konuşmak bana iyi gelir.",
                random.choice(["Zor bir gün...", "Seninle konuşmam lazımdı."]),
                "Calm",
            ))

    # D4: Gather conditions met but mid-conversation → stay and talk
    if (v["hun"] > 0.3 or v["thi"] > 0.3) and "food" not in inv_ids and social_p:
        cases.append((
            "socialize",
            f"Kaynak toplamam lazım ama {social_p['id']} ile konuşmanın ortasındayım. "
            f"Önce bunu bitireyim, sonra gidip toplarım.",
            random.choice(["Devam edelim...", "Biraz daha var."]),
            "Calm",
        ))

    if not cases:
        return None
    return random.choice(cases)


# ─────────────────────────────────────────────────────────────────────────────
# Training example builder (Llama-3 instruct format)
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "Sen bir medeniyet simülasyonundaki NPC'nin bilişsel karar motorusun.\n"
    "Sana NPC'nin anlık durumunu JSON formatında göndereceğim.\n"
    "Görevin: Yalnızca tek bir eylem kararı üret, JSON formatında döndür.\n"
    "Kurallar:\n"
    "- action_id MUTLAKA valid_actions listesindeki değerlerden biri olmalıdır\n"
    "- reasoning: birinci şahıs iç monolog, 1-3 cümle\n"
    "- dialogue: yalnızca socialize/trade eylemlerinde doldur, diğerlerinde null\n"
    "- emotion: NPC'nin şu anki baskın duygu durumu (tek kelime)\n"
    "- Yanıtın SADECE JSON olsun — kod bloğu, açıklama yok"
)

TEMPLATE = ("<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
            "{system}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n"
            "{user}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
            "{assistant}<|eot_id|>")

_DEVIATION_RATE = 0.15   # 15% of examples use intent deviation


def build_example() -> dict:
    state = generate_npc_state()

    # Choose path: deviation (~15%) or standard (~85%)
    action_id, reasoning, dialogue, emotion = _select_action_standard(state)

    if random.random() < _DEVIATION_RATE:
        deviation = _select_action_with_deviation(state)
        if deviation is not None:
            action_id, reasoning, dialogue, emotion = deviation

    assert action_id in NPC_SIM_ACTIONS, f"Invalid action: {action_id}"

    user_payload = json.dumps(state, ensure_ascii=False, separators=(",", ":"))
    output = {
        "npc_id": state["id"],
        "reasoning": reasoning,
        "selected_action": {
            "action_id": action_id,
            "target_id": None,
            "dialogue": dialogue,
        },
        "emotion": emotion,
    }
    assistant_json = json.dumps(output, ensure_ascii=False, separators=(",", ":"))

    text = TEMPLATE.format(
        system=SYSTEM_PROMPT,
        user=user_payload,
        assistant=assistant_json,
    )
    return {"text": text}


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def generate_dataset(path: str, count: int, seed: int = 42) -> None:
    random.seed(seed)
    print(f"Generating {count} examples → {path}")
    with open(path, "w", encoding="utf-8") as f:
        for i in range(count):
            example = build_example()
            json.dump(example, f, ensure_ascii=False)
            f.write("\n")
            if (i + 1) % 2000 == 0:
                print(f"  {i + 1}/{count}...")
    print(f"  Done → {os.path.getsize(path) // 1024} KB")


if __name__ == "__main__":
    base     = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base, "..", "data")
    os.makedirs(data_dir, exist_ok=True)

    generate_dataset(os.path.join(data_dir, "train_v2.jsonl"), count=10000, seed=456234)
    generate_dataset(os.path.join(data_dir, "test_v2.jsonl"),  count=2000,  seed=984756)
    print("\nAll done. v3 datasets ready (drink action + intent deviation + schedule field)!")
