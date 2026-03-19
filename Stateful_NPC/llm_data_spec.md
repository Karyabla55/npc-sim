# NPC-Sim LLM Data Specification

**Version:** 1.0 | **Author:** Sadık Abdusselam Albayrak | **License:** Apache 2.0

Bu belge NPC-Sim'in LLM entegrasyon katmanının veri tiplerini, şemasını ve beklenen model davranışlarını tanımlar. Kendi modelini eğitecek araştırmacılar için birincil referans kaynağıdır.

---

## 1. Genel Mimari

```
SimulationManager.tick()
    └─ LLMDecisionSystem.tick(ctx)
         ├─ [H2] Interrupt kontrol → anında tetikle
         ├─ NPCSerializer.build_payload() → JSON string
         ├─ LLMRequestQueue.submit(priority) → [H3]
         │       └─ OllamaBackend.call() → LLMResponse
         │               └─ schema doğrulama
         │                       ├─ [H4] guided retry (geçersiz action_id)
         │                       └─ fallback → UtilityEvaluator
         └─ action.execute(ctx)
```

---

## 2. Model Girdi Payload (Input Schema)

Her karar tiki için NPC'nin tam durumu **minified JSON** olarak model user mesajına eklenir.

### 2.1 Alan Açıklamaları

| Kısa Key | Tip | Açıklama |
|----------|-----|----------|
| [id](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#53-62) | `string` | Deterministik NPC kimliği (`npc_xxxxxxxx`) |
| [arch](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/perception/sensor_range.py#60-66) | `string` | Kişilik arketip etiketi: `"Brave"`, `"Cunning"`, `"Fearful"`, `"Honorable"`, `"Aggressive"` |
| [occ](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/npc/schedule.py#29-41) | `string` | Meslek: `"Guard"`, `"Merchant"`, `"Priest"`, ... (15 değer) |
| [faction](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/simulation/faction_registry.py#16-18) | `string` | Bağlı faksiyon: `"CityWatch"`, `"Bandits"`, `"Church"`, ... |
| `b5` | [object](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/perception/perception_system.py#101-112) | Big Five kişilik değerleri (0.0-1.0 float) |
| `b5.e` | [float](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#34-40) | Extraversion (Dışadönüklük) |
| `b5.a` | [float](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#34-40) | Agreeableness (Uyumluluk) |
| `b5.c` | [float](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#34-40) | Conscientiousness (Sorumluluk) |
| `b5.n` | [float](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#34-40) | Neuroticism (Nevrotiklik) |
| `b5.o` | [float](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#34-40) | Openness (Açıklık) |
| `traits` | `string[]` | Aktif kişilik etiketleri: `["Brave","Devout"]` |
| `vitals` | [object](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/perception/perception_system.py#101-112) | Fizyolojik durum |
| `vitals.hp` | [float](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#34-40) | Mevcut can (0–hp_max) |
| `vitals.hp_max` | [float](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#34-40) | Maksimum can (tipik: 120.0) |
| `vitals.en` | [float](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#34-40) | Enerji oranı (0.0–1.0) |
| `vitals.hun` | [float](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#34-40) | Açlık oranı (0.0=tok, 1.0=ölüm açlığı) |
| `vitals.thi` | [float](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#34-40) | Susuzluk oranı (0.0=tok, 1.0=kritik) |
| `vitals.str` | [float](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#34-40) | Stres oranı (0.0–1.0) |
| [emo](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/simulation/spatial_grid.py#41-53) | [object](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/perception/perception_system.py#101-112) | Duygusal durum |
| `emo.hap` | [float](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#34-40) | Mutluluk (0.0–1.0) |
| `emo.fear` | [float](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#34-40) | Korku (0.0–1.0) |
| `emo.ang` | [float](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#34-40) | Öfke (0.0–1.0) |
| `emo.mood` | `string` | Baskın ruh hali: `"Calm"`, `"Happy"`, `"Fearful"`, `"Angry"`, `"Distressed"` |
| [inv](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/llm/npc_serializer.py#96-101) | `object[]` | Envanter slotları |
| `inv[].id` | `string` | Eşya kimliği: `"food"`, `"gold"`, `"medicine"`, `"tool"` |
| `inv[].n` | [int](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/Stateful_NPC/generator/npc_state_machine.py#55-118) | Miktar |
| [time](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_clock.py#39-41) | [object](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/perception/perception_system.py#101-112) | Simülasyon zamanı |
| `time.day` | [int](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/Stateful_NPC/generator/npc_state_machine.py#55-118) | Simülasyon günü |
| `time.hr` | [float](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#34-40) | Saati (0.0–24.0) |
| [pos](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/simulation/faction_registry.py#24-26) | [object](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/perception/perception_system.py#101-112) | Konum (H1 semantik etiketli) |
| `pos.x` | [float](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#34-40) | Dünya X koordinatı |
| `pos.z` | [float](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#34-40) | Dünya Z koordinatı |
| `pos.zone` | `string` | **[H1]** Semantik bölge adı: `"MarketSquare"`, `"Tavern"`, `"Temple"`, ... |
| `pos.landmark` | `string` | **[H1]** En yakın referans noktası: `"CityGates"`, `"CentralFountain"`, ... |
| [percepts](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/perception/perception_system.py#27-30) | `object[]` | Algılanan varlıklar (saliency'e göre sıralı, max 5) |
| `percepts[].id` | `string` | Varlık kimliği |
| `percepts[].tag` | `string` | Kategori: `"Threat"`, `"Food"`, `"Social"`, `"Resource"` |
| `percepts[].sal` | [float](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#34-40) | Saliency / önem skoru (0.0–1.0) |
| `percepts[].threat` | [float](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#34-40) | Tehdit seviyesi (yalnızca `"Threat"` tag'inde) |
| [memories](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/llm/npc_serializer.py#116-131) | `object[]` | En yüksek duygusal ağırlıklı top-3 anı |
| `memories[].evt` | `string` | Olay tipi: `"Combat"`, `"Eat"`, `"Social"`, ... |
| `memories[].desc` | `string` | Kısa açıklama (max 80 karakter) |
| `memories[].ew` | [float](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#34-40) | Duygusal ağırlık (-1.0 negatif, +1.0 pozitif) |
| `memories[].dt` | [int](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/Stateful_NPC/generator/npc_state_machine.py#55-118) | Geçen simülasyon süresi (saniye) |
| [beliefs](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/llm/npc_serializer.py#132-141) | `object[]` | Öne çıkan inanç düğümleri (max 5) |
| `beliefs[].subj` | `string` | İnanç konusu |
| `beliefs[].conf` | [float](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#34-40) | Güven skoru (0.0–1.0) |
| `beliefs[].val` | [float](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#34-40) | Değer/duygu (-1.0 düşmanlık, +1.0 sevgi) |
| [factions](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/llm/npc_serializer.py#142-150) | [object](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/perception/perception_system.py#101-112) | Faksiyon ilişkileri (`{faksiyon: trust_score}`) |
| `goals_top` | `string\|null` | En yüksek öncelikli hedef: `"FindFood"`, `"FindWater"`, `"Rest"`, `null` |
| [interrupt](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/llm/llm_decision_system.py#120-130) | `bool` | **[H2]** `true` = acil durum tetikleyici (Threat≥0.8 veya ani HP düşüşü) |
| [valid_actions](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/llm/npc_serializer.py#151-162) | `string[]` | Bu tick'te geçerli action_id listesi — **model MUTLAKA bu listeden seçmeli** |

### 2.2 Örnek Payload (minified)

```json
{"id":"npc_a3b8f70a","arch":"Brave","occ":"Guard","faction":"CityWatch","b5":{"e":0.68,"a":0.52,"c":0.77,"n":0.14,"o":0.38},"traits":["Brave","Loyal"],"vitals":{"hp":65.0,"hp_max":120.0,"en":0.72,"hun":0.67,"thi":0.45,"str":0.88},"emo":{"hap":0.0,"fear":0.0,"ang":0.39,"mood":"Calm"},"inv":[{"id":"food","n":2},{"id":"gold","n":12}],"time":{"day":2,"hr":14.9},"pos":{"x":54.2,"z":48.7,"zone":"MarketSquare","landmark":"CityGates"},"percepts":[{"id":"wolf_01","tag":"Threat","sal":0.91,"threat":0.82},{"id":"food_stall","tag":"Food","sal":0.65}],"memories":[{"evt":"Combat","desc":"Aldric attacks wolf_01 for 12 damage","ew":0.6,"dt":45}],"beliefs":[{"subj":"wolf_01","conf":0.72,"val":-0.85}],"factions":{"CityWatch":0.0,"Bandits":-0.6},"goals_top":"FindFood","interrupt":false,"valid_actions":["eat","sleep","flee","gather","heal","attack","socialize","trade","work","pray","walk_to"]}
```

---

## 3. Model Çıktı Şeması (Output Schema)

Model YALNIZCA aşağıdaki JSON objesini döndürmelidir. Markdown, kod bloğu veya ek açıklama yasaktır.

```json
{
  "npc_id": "string",
  "reasoning": "string",
  "selected_action": {
    "action_id": "string",
    "target_id": "string | null",
    "dialogue": "string | null"
  },
  "emotion": "string"
}
```

### 3.1 Alan Açıklamaları (Çıktı)

| Alan | Gerekli | Açıklama |
|------|---------|----------|
| `npc_id` | ✅ | Giriş payload'undaki [id](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/core/sim_rng.py#53-62) değerinin aynısı |
| `reasoning` | ✅ | Birinci şahıs iç monolog (1-3 cümle). NPC'nin neden bu eylemi seçtiğini açıklar. |
| `selected_action.action_id` | ✅ | [valid_actions](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/llm/npc_serializer.py#151-162) listesindeki değerlerden **biri**. Başka değer geçersizdir. |
| `selected_action.target_id` | ❌ | Hedef varlık kimliği (sosialleşme/ticaret için, diğerlerinde null) |
| `selected_action.dialogue` | ❌ | Yalnızca `socialize` veya `trade` eyleminde konuşma metni. Diğerlerinde `null`. |
| [emotion](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/npc/psychology.py#55-78) | ✅ | Anlık baskın duygu (tek kelime): `"Calm"`, `"Happy"`, `"Fearful"`, `"Angry"`, `"Focused"`, `"Tired"`, `"Aggressive"`, `"Devout"` |

### 3.2 Örnek Yanıt

```json
{
  "npc_id": "npc_a3b8f70a",
  "reasoning": "Kurt 0.82 tehdit seviyesiyle çok yakın. Açım ama saldırıya geçmek akıllıca değil. Önce yiyecek toplayıp enerji kazanacağım, kurdu gözetlemeye devam edeceğim.",
  "selected_action": {
    "action_id": "gather",
    "target_id": "food_stall",
    "dialogue": null
  },
  "emotion": "Calm"
}
```

---

## 4. Eylem Uzayı (Action Space)

Model [valid_actions](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/llm/npc_serializer.py#151-162) listesindeki 11 eylemden birini seçmelidir.

| [action_id](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/decisions/action.py#19-23) | Kategori | Ne zaman uygun? |
|-------------|---------|----------------|
| [eat](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/npc/npc_factory.py#18-31) | Hayatta Kalma | `vitals.hun > 0.65` VE [inv](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/llm/npc_serializer.py#96-101)'de food var |
| `sleep` | Hayatta Kalma | `vitals.en < 0.3` — enerji kritik |
| `flee` | Tehdit | Threat percept var VE NPC savaşçı değil / HP düşük |
| `gather` | Kaynak | Yiyecek/kaynak percept var, stoklar düşük |
| [heal](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/npc/vitals.py#37-39) | Hayatta Kalma | `vitals.hp < 30` VE [inv](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/llm/npc_serializer.py#96-101)'de medicine var |
| `attack` | Çatışma | Threat var VE NPC savaşçı (Guard/Knight/Bandit) |
| `socialize` | Sosyal | Social percept var, ruh hali iyi, `dialogue` doldur |
| `trade` | Ekonomik | Merchant veya [inv](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/llm/npc_serializer.py#96-101)'de trade malı var, `dialogue` doldur |
| `work` | Meslek | Acil ihtiyaç yok, meslek uygun (Blacksmith/Farmer/Scholar) |
| `pray` | Dinsel | Priest veya `"Devout"` trait'i var |
| `walk_to` | Nötral | Hiçbir acil durum yok, dolaşma |

---

## 5. Hardening Mekanizmaları (H1-H4)

### H1 — Semantik Konum

[pos](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/simulation/faction_registry.py#24-26) alanında [zone](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/llm/world_registry.py#53-56) ve `landmark` ekleniyor.
- LLM ham koordinatları okuyamaz; semantik etiketler `walk_to` kararlarını çok tutarlı kılar.
- [WorldRegistry](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/llm/world_registry.py#26-66) AABB tabanlı zone lookup yapar.

### H2 — Olay Güdümlü Kesme (Interrupt)

- `interrupt: true` → LLM tick sayacı sıfırlanır, **anında** çağrılır.
- Koşullar: `percept.threat ≥ 0.8` veya son tick'ten `hp_drop ≥ 15.0`
- Payload'daki `interrupt: true` değeri modelin acil karar moduna geçmesini sağlar.

### H3 — Öncelik Kuyruğu

| Durum | Priority |
|-------|----------|
| `interrupt=true` | 0 (anında) |
| UI'da seçili NPC | 1 |
| HP < %30 | 2 |
| Normal LLM tiki | 5 |
| Hiç percept yok | 10 (arka plan) |

- Ollama için `max_concurrent=1` (VRAM güvenli)
- Dolup taşan istekler sessizce [UtilityEvaluator](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/decisions/utility_evaluator.py#43-60)'a düşer.

### H4 — Guided Retry

1. Model geçersiz [action_id](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/decisions/action.py#19-23) döndürürse (`"run_away"` → listede yok)
2. Düzeltici prompt: `"Geçersiz eylem: 'run_away'. Yalnızca şunlardan seç: [flee, gather, ...]"`
3. Bir kez daha denenir; hala hatalıysa [UtilityEvaluator](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/decisions/utility_evaluator.py#43-60) fallback.
4. Başarı oranını ~%70 artırır, inner monolog korunur.

---

## 6. Eğitim Veri Formatı

### 6.1 Dosya Formatı

Her satır bağımsız bir eğitim örneği (JSONL):
```json
{"text": "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n..."}
```

### 6.2 Llama-3 Instruct Şablonu

```
<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{SYSTEM_PROMPT}<|eot_id|><|start_header_id|>user<|end_header_id|>

{NPC_JSON_PAYLOAD}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

{OUTPUT_JSON}<|eot_id|>
```

### 6.3 Veri Dağılımı (v2 Jeneratör)

| Dosya | Örnek | Boyut |
|-------|-------|-------|
| `train_v2.jsonl` | 20,000 | ~18 MB |
| `test_v2.jsonl` | 2,000 | ~1.8 MB |

Dağılım:
- 5 arketip × 15 rol = 75 temel kombinasyon
- %35 threat percept (interrupt %10)
- Vitals kritik: hunger %20, energy %15, hp_low %10
- Sosyal etkileşim: %30
- Role-spesifik eylemler: %50 olasılık

### 6.4 Dataset Üretimi

```bash
cd d:\DeepLearning\Projects\NLP_ABM_Sim\Stateful_NPC\generator
python npc_sim_generator_v2.py
```

---

## 7. Model Eğitim Önerileri

### 7.1 LoRA Fine-tuning Parametreleri

```python
# Önerilen HuggingFace PEFT konfigürasyonu
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)
training_args = TrainingArguments(
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    num_train_epochs=3,
    learning_rate=2e-4,
    fp16=True,
    logging_steps=100,
)
```

### 7.2 Değerlendirme Metrikleri

| Metrik | Hedef |
|--------|-------|
| [action_id](file:///d:/DeepLearning/Projects/NLP_ABM_Sim/npc_sim/decisions/action.py#19-23) geçerlilik oranı | ≥ %98 |
| JSON parse başarısı | ≥ %99 |
| `reasoning` ortalama uzunluk | 30-100 token |
| Interrupted tick doğru flee/attack oranı | ≥ %85 |
| Fallback oranı (canlı sim'de) | ≤ %5 |

### 7.3 Ollama Model Yükleme

```bash
# Quantize edilmiş modeli Ollama'ya yükle
ollama create npc-sim-decision -f Modelfile
ollama run npc-sim-decision
```

```dockerfile
# Modelfile örneği
FROM ./npc_decision_q4_k_m.gguf
SYSTEM "Sen bir medeniyet simülasyonundaki NPC karar motorusun..."
PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER num_predict 256
```

---

## 8. Fallback Davranış Garantisi

LLM başarısız olursa simülasyon **hiç durmaz**:

```
LLM çağrısı başarısız
  → UtilityEvaluator her tick'i doldurur
  → NPC vitals bozunmaya devam eder
  → Sonraki LLM tick'inde tekrar denenir
  → Sunucu /api/llm/status üzerinden fallback sayısını raporlar
```

---

## 9. API Endpoints (Sunucu Tarafı)

| Method | Endpoint | Body / Params | Açıklama |
|--------|----------|---------------|----------|
| `POST` | `/api/llm` | `{enable, npc_id?, backend, model}` | LLM'i aç/kapat |
| `GET` | `/api/llm/status` | — | `{calls, fallbacks, retries, queue_depth, per_npc}` |
| `POST` | `/api/llm/focus` | `{npc_id}` | Seçili NPC'ye priority=1 ver |
