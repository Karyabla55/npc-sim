# 🎭 NPC-Sim Training Dataset — Stateful Decision Agent (Dual-LLM)

*NPC-Sim projesinin LLM eğitim veri seti. Llama-3 tabanlı asimetrik çift model mimarisi için.*

**Author:** Sadık Abdusselam Albayrak · **License:** Apache 2.0

---

## 📂 Versiyon Karşılaştırması

| Özellik | v1 (Orijinal) | v2 (NPC-Sim Entegre) | v4 (Dual-LLM Pipeline) |
|---------|--------------|---------------------|------------------------|
| Sistem Mimarisi | Tek Model | Tek Model | Asimetrik Çift Model (Reasoner + Formatter) |
| Durum değişkenleri | Stress + Trust (2 değer) | Big Five + Vitals + Emotions | Big Five + Vitals + Emotions (13 değer) |
| Eylem uzayı | 9 eylem | 11 eylem | 12 eylem (`drink` dahil) |
| Konum | Ham koordinat yok | Semantik zone + landmark | Semantik zone + landmark |
| Kesme Mekanizması | Yok | `interrupt: true` (H2) | `interrupt: true` (H2) + Deviation D5-D8 |
| Çıktı formatı | `{thought, speech, action, emotion}` | `{npc_id, reasoning, selected_action, emotion}` | Reasoner: Serbest Metin / Formatter: JSON |
| Eğitim örnekleri | 20k + 2k | 20k + 2k | Reasoner: 10k + 2k / Formatter: ~12k |

---

## 📁 Dosya Yapısı

```
Stateful_NPC/
├── generator/
│   ├── npc_sim_generator_v2.py   ← Yeni Dual-LLM generator v4
│   ├── config.py                 ← v1 konfigürasyon (roller, diyaloglar)
│   └── npc_state_machine.py      ← v1 state machine
├── newgen-rpg.ipynb              ← Llama 3 SFTTraining Dual-Phase Notebook
└── data/
    ├── train_reasoner.jsonl      ← Reasoner corpus (10k)
    ├── test_reasoner.jsonl       ← Reasoner test corpus (2k)
    ├── train_formatter.jsonl     ← Formatter corpus (~12k, paraphrase dâhil)
```

---

## 🧠 v4 Veri Yapısı (Dual-LLM)

Mimari iki bağımsız modelden oluşur. Reasoner mantık kurar, Formatter bunu JSON'a dönüştürür.

### A. Reasoner (Component A) - 3B Model
**Girdi:** NPC state minified JSON.
**Çıktı:** 3-5 cümlelik birinci şahıs Türkçe iç monolog. *(KESİNLİKLE JSON DEĞİL)*

### B. Formatter (Component B) - 1B Model
**Girdi:** Reasoner'ın ürettiği Türkçe iç monolog.
**Çıktı:** Strict JSON formatında eylem.

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

---

## ⚡ Dataset Üretimi

```bash
cd Stateful_NPC/generator

# v4 Dual-LLM datasetlerini üret
python npc_sim_generator_v2.py
# → data/train_reasoner.jsonl
# → data/test_reasoner.jsonl
# → data/train_formatter.jsonl
```

---

## 🏋️ Model Eğitim Önerisi

`newgen-rpg.ipynb` üzerinden `SFTTrainer` kullanılarak iki fazlı eğitim gerçekleştirilir.
- **Phase A**: Reasoner (Llama 3.2 3B) `train_reasoner.jsonl` kullanılarak eğitilir. 
- **Phase B**: Formatter (Llama 3.2 1B) `train_formatter.jsonl` kullanılarak eğitilir.

---

## 📜 Lisans

Apache License 2.0 — Ticari ve akademik kullanım serbesttir.
