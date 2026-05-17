# 🎭 NPC-Sim Training Dataset — Stateful Decision Agent (Dual-LLM)

*NPC-Sim projesinin LLM eğitim veri seti. Llama-3 tabanlı asimetrik çift model mimarisi için.*

**Author:** Sadık Abdusselam Albayrak · **License:** Apache 2.0

> **Implementation status (v1.6.0):** Dual-LLM eğitim hattı **tamamen aktif**.
> `DualLLMBackend` kodda mevcuttur; `SimulationConfig(llm_backend="dual")` ile
> etkinleştirilir. Canonical referans: `docs/llm_pipeline.md`.

---

## 📂 Versiyon Karşılaştırması

| Özellik | v1 (Orijinal) | v2 (NPC-Sim Entegre) | v4 (Dual-LLM Pipeline) | v5 (v1.6.0) |
|---------|--------------|---------------------|------------------------|-------------|
| Sistem Mimarisi | Tek Model | Tek Model | Asimetrik Çift Model | Asimetrik Çift Model (uygulandı) |
| Durum değişkenleri | Stress + Trust (2) | Big Five + Vitals + Emotions | Big Five + Vitals + Emotions | + persona card |
| Eylem uzayı | 9 eylem | 11 eylem | 12 eylem | 12 eylem |
| Konum | Ham koordinat yok | Semantik zone + landmark | Semantik zone + landmark | Semantik zone + landmark |
| Eylem etiketi | Heuristic | Heuristic | Heuristic + D5-D8 | Multi-factor (self_power vs threat + duty) |
| Çıktı formatı | `{thought, speech, action, emotion}` | `{npc_id, reasoning, ...}` | Reasoner: Metin / Formatter: JSON | Formatter: JSON **(npc_id yok)** |
| Eğitim örnekleri | 20k + 2k | 20k + 2k | Reasoner: 10k + 2k / Formatter: ~12k | Aynı + gemma4:e4b CoT |

---

## 📁 Dosya Yapısı

```
Stateful_NPC/
├── generator/
│   ├── npc_sim_generator_v2.py   ← Ana generator (decision_factors + persona_card + bootstrap_cot bağlar)
│   ├── decision_factors.py       ← self_power / perceived_threat / duty_pull → 3-zone eylem etiketi
│   ├── persona_card.py           ← Türkçe NPC kimlik preamble (2-3 cümle, R14 fix)
│   ├── bootstrap_cot.py          ← Gemma 3 4B CoT üretimi (Ollama) + SHA disk cache
│   ├── config.py                 ← v1 konfigürasyon (roller, diyaloglar)
│   └── npc_state_machine.py      ← v1 state machine
└── data/
    ├── train_reasoner.jsonl      ← Reasoner corpus (10k, persona + state → CoT)
    ├── test_reasoner.jsonl       ← Reasoner test corpus (2k)
    ├── train_formatter.jsonl     ← Formatter corpus (~12k, paraphrase dâhil, npc_id yok)

notebooks/
└── newgen-rpg.ipynb              ← Kaggle v5: packing=False + collator + 1B-Instruct + stress test
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
  "reasoning": "Kurt bana yaklaştı ama canım düşük. Yiyecek almak daha öncelikli, savaşa girmeyeceğim.",
  "selected_action": {
    "action_id": "gather",
    "target_id": "food_stall",
    "dialogue": null
  },
  "emotion": "Calm"
}
```

> **v1.6.0:** `npc_id` Formatter çıktısından kaldırıldı. Runtime'da `DualLLMBackend` enjekte eder.

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
