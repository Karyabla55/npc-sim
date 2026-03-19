# 🎭 NPC-Sim Training Dataset — Stateful Decision Agent

*NPC-Sim projesinin LLM eğitim veri seti. Llama-3 tabanlı veya özel modeller için.*

**Author:** Sadık Abdusselam Albayrak · **License:** Apache 2.0

---

## 📂 Versiyon Karşılaştırması

| Özellik | v1 (Orijinal) | v2 (NPC-Sim Entegre) |
|---------|--------------|---------------------|
| Durum değişkenleri | Stress + Trust (2 değer) | Big Five + Vitals + Emotions (13 değer) |
| Eylem uzayı | 9 eylem (Trade/Combat) | 11 eylem (tüm NPC-Sim aksiyonları) |
| Konum | Ham koordinat yok | Semantik zone + landmark (H1) |
| Bellek | Tek satır metin | Episodik hafıza ring buffer (top-3 salient) |
| Algı sistemi | Yok | Percepts (Threat/Food/Social, threat_level) |
| İnanç sistemi | Yok | BeliefSystem nodes (conf + val) |
| Kesme mekanizması | Yok | `interrupt: true` (H2, threat≥0.8) |
| Çıktı formatı | `{thought, speech, action, emotion}` | `{npc_id, reasoning, selected_action, emotion}` |
| Eğitim örnekleri | 20k + 2k | 20k + 2k |

---

## 📁 Dosya Yapısı

```
Stateful_NPC/
├── generator/
│   ├── npc_sim_generator_v2.py   ← Yeni NPC-Sim entegre generator
│   ├── config.py                 ← v1 konfigürasyon (roller, diyaloglar)
│   └── npc_state_machine.py      ← v1 state machine
└── data/
    ├── train_v2.jsonl            ← Yeni v2 (20k örnek, ~14 MB)
    ├── test_v2.jsonl             ← Yeni v2 (2k örnek, ~4 MB)
    ├── train.jsonl               ← Orijinal v1 (20k örnek)
    └── test.jsonl                ← Orijinal v1 (2k örnek)
```

---

## 🧠 v2 Veri Yapısı

### Girdi (User Mesajı)

Her örnek NPC'nin tam anlık durumunu içeren **minified JSON**:

```json
{
  "id": "npc_a3b8f70a",
  "arch": "Brave", "occ": "Guard", "faction": "CityWatch",
  "b5": {"e":0.68,"a":0.52,"c":0.77,"n":0.14,"o":0.38},
  "traits": ["Brave","Loyal"],
  "vitals": {"hp":65.0,"hp_max":120.0,"en":0.72,"hun":0.67,"thi":0.45,"str":0.88},
  "emo": {"hap":0.0,"fear":0.0,"ang":0.39,"mood":"Calm"},
  "inv": [{"id":"food","n":2}],
  "time": {"day":2,"hr":14.9},
  "pos": {"x":54.2,"z":48.7,"zone":"MarketSquare","landmark":"CityGates"},
  "percepts": [{"id":"wolf_01","tag":"Threat","sal":0.91,"threat":0.82}],
  "memories": [{"evt":"Combat","desc":"Aldric attacks wolf_01","ew":0.6,"dt":45}],
  "beliefs": [{"subj":"wolf_01","conf":0.72,"val":-0.85}],
  "factions": {"CityWatch":0.0,"Bandits":-0.6},
  "goals_top": "FindFood",
  "interrupt": false,
  "valid_actions": ["eat","sleep","flee","gather","heal","attack","socialize","trade","work","pray","walk_to"]
}
```

### Çıktı (Assistant Yanıtı)

```json
{
  "npc_id": "npc_a3b8f70a",
  "reasoning": "Kurt bana yaklaştı ama canım düşük. Yiyecek almak daha öncelikli, savaşa girmeyeceğim.",
  "selected_action": {
    "action_id": "gather",
    "target_id": "food_stall",
    "dialogue": null
  },
  "emotion": "Calm"
}
```

**Kurallar:**
- `action_id` → MUTLAKA `valid_actions` listesinden
- `reasoning` → birinci şahıs iç monolog, 1-3 cümle
- `dialogue` → yalnızca `socialize` / `trade` eylemlerinde; diğerlerinde `null`
- `emotion` → tek kelime: `Calm`, `Fearful`, `Angry`, `Happy`, `Tired`, `Aggressive`, `Focused`, `Devout`

---

## 🛠️ Eylem Uzayı (11 Eylem)

| `action_id` | Ne zaman seçilmeli? |
|-------------|---------------------|
| `eat` | `vitals.hun > 0.65` VE envanterde food var |
| `sleep` | `vitals.en < 0.3` |
| `flee` | Threat ≥ 0.8 VE NPC savaşçı değil |
| `gather` | Açlık var ama envanterde yiyecek yok; food percept var |
| `heal` | `vitals.hp < 30` VE envanterde medicine var |
| `attack` | Threat var VE arch=Brave veya Guard/Knight/Bandit |
| `socialize` | Social percept var, ruh hali iyi |
| `trade` | Merchant rolü veya ticaret malı var |
| `work` | Blacksmith/Farmer/Scholar, acil ihtiyaç yok |
| `pray` | Priest veya trait Devout |
| `walk_to` | Hiçbir acil durum yok |

---

## ⚡ Dataset Üretimi

```bash
cd Stateful_NPC/generator

# v2 üret (NPC-Sim tam state)
python npc_sim_generator_v2.py
# → data/train_v2.jsonl (20k, ~14 MB, seed=42)
# → data/test_v2.jsonl  (2k,  ~4 MB,  seed=99)

# v1 üret (orijinal stress/trust)
python npc_state_machine.py
```

---

## 🏋️ Model Eğitim Önerisi

```python
# HuggingFace PEFT ile LoRA fine-tuning
from peft import LoraConfig

lora_config = LoraConfig(
    r=16, lora_alpha=32,
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    task_type="CAUSAL_LM",
)
# Önerilen base model: Llama-3.2-3B-Instruct
# num_train_epochs=3, lr=2e-4, batch_size=4
```

Eğitilen modeli Ollama ile deploy et:
```bash
ollama create npc-sim-decision -f Modelfile
ollama run npc-sim-decision
```

---

## 📊 Beklenen Model Metrikleri

| Metrik | Hedef |
|--------|-------|
| `action_id` geçerlilik oranı | ≥ %98 |
| JSON parse başarısı | ≥ %99 |
| Interrupt doğru tepki (flee/attack) | ≥ %85 |
| Canlı sim fallback oranı | ≤ %5 |

---

## 📜 Lisans

Apache License 2.0 — Ticari ve akademik kullanım serbesttir.
