# NPC-Sim — Yol Haritası & Sonraki Adımlar

**Oluşturulma:** 2026-05-02  
**Durum:** Canlı belge — her sürümde güncellenir  
**Amaç:** Simülasyonun nerede olduğunu, nereye gitmesi gerektiğini ve nasıl oraya ulaşılacağını kayıt altında tutmak.

---

## 1. Projenin Temel Amacı

NPC-Sim bir **medeniyet ölçekli yaşayan dünya simülatörü**dür. Hedef:

- NPCler **gerçekten yaşıyor** olmalı: yer, yer, uyur, çalışır, acıkır, korkar.
- NPCler **iletişim kurar**: konuşur, dedikodu yayar, bilgi taşır, ilişki geliştirir.
- NPCler **ticaret yapar**: piyasa fiyatı oluşturur, müzakere eder, aldatır veya güvenir.
- Sistem **deterministik** ama **sürpriz dolu**: aynı seed → aynı tarih, ama emergent davranış zengin.
- **Utility AI** rutini yönetir; **LLM** sosyal, ahlaki ve anlatısal kararları verir.

Şu anki durum: altyapı güçlü, entegrasyon eksik. Veri yapıları var ama birbirleriyle konuşmuyor.

---

## 2. Mevcut Durum — Ne Çalışıyor

| Bileşen | Durum | Notlar |
|---------|-------|--------|
| Utility AI (12 action) | ✅ Tam işlevsel | EatAction, DrinkAction, Sleep, Flee, Gather, Heal, Attack, Socialize, Trade, Work, Pray, WalkTo |
| Vitals sistemi | ✅ Çalışıyor | HP, hunger, thirst, energy, stress — tick başına decay |
| Psychology (Big Five + duygular) | ✅ Çalışıyor | Extraversion, fear, anger, happiness, mood label |
| Hafıza (ring buffer) | ✅ Çalışıyor | O(1), 50 kapasite, duygusal ağırlık, salient seçimi |
| Sosyal ilişkiler | ✅ Veri mevcut | Trust/affinity/respect — SocializeAction'ın gossip yayılımı için trust kullanılıyor (v1.4.0) |
| İnançlar (BeliefSystem) | ✅ Kısmen entegre (v1.4.0) | WalkTo zone bias + Attack target valence + Socialize gossip yayılımı kullanıyor. Diğer action'lar hâlâ kullanmıyor. |
| Hedefler (GoalSystem) | ✅ Entegre (v1.4.0) | `ActionContext.goal_bonus()` ile Eat/Drink/Sleep/Heal/Socialize/Trade/Work/Pray/Gather/Flee evaluate skorlarına eklendi |
| Trait'ler | ✅ Kısmen entegre | 4 action tipini etkiliyor (flee/attack/trade/explore) |
| Envanter | ✅ Çalışıyor | Slot tabanlı, 10 item tipi |
| Schedule | ✅ Çalışıyor | Meslek bazlı, tercih eğrileri |
| Faction sistemi | ✅ Veri mevcut | Disposition matrix, decay — ama NPC kararlarını ETKİLEMİYOR |
| World Map | ✅ Çalışıyor | 10 sabit zone, koordinat tabanlı |
| SimLogger | ✅ Tam işlevsel | 44 sütun CSV, zero-overhead toggle |
| LLM pipeline (interrupt) | ✅ Çalışıyor | Async, priority queue, 5 hardening mekanizması |
| LLM payload (NPCSerializer) | ✅ Çalışıyor | Token-verimli JSON, tüm state dahil |
| DualLLMBackend | ✅ Tamamlandı (v1.6.0) | `DualLLMBackend` + H6 gate + npc_id injection |
| Web dashboard | ⚠️ Temel | State görüntüleme var, LLM kontrol eksik |

---

## 3. Temel Eksikler — Yaşayan Dünya İçin

### 3.1 NPC-NPC İletişimi Gerçek Değil ✅ Kısmen çözüldü (v1.4.0)

**Önceki sorun:** `SocializeAction.execute()` iki NPC'nin `.interact()` metodunu çağırır. Bu trust/affinity günceller ama:
- LLM'in ürettiği `dialogue` karşı NPC'ye ulaşmıyor
- Konuşulan şey hafızaya yazılmıyor
- Bilgi (dedikodu, uyarı, haber) karşıya geçmiyor
- Karşı NPC'nin durumu (ne hissediyor, ne biliyor) LLM'e verilmiyor

**v1.4.0'da çözülen (G4 + G5):**
- LLM dialogue artık `NPC.pending_dialogue` üzerinden `SocializeAction.execute()`'a iletiliyor ve target NPC'nin episodic memory'sine `Dialogue` event olarak yazılıyor.
- Konuşan NPC'nin en yüksek confidence'lı belief'i hedef NPC'ye sönümlü olarak (`valence × 0.7`, `confidence × 0.6`) aktarılıyor (gossip retelling fidelity).
- Trust kontrolü: `relation.trust < 0.3` ise belief paylaşılmıyor.

**Hâlâ açık (v1.5 hedefleri):**
- Karşı NPC'nin durumu (mood, known_facts) LLM payload'una eklenmedi (G8 — v1.5'e ertelendi).
- `information_shared` semantic etiketi (`bandit_sighting`, `market_price` gibi) yapısal değil — şimdilik subject string'i kullanılıyor.

---

### 3.2 Ekonomi Taslak Seviyede

**Sorun:** `TradeAction.execute()` hardcoded GOLD ↔ FOOD takas yapıyor. Fiyat yok, müzakere yok, piyasa dinamiği yok. `WorkAction` mesleğe göre item üretiyor (Farmer→GRAIN) ama bu üretimin taleple bağlantısı yok.

**Etki:** Ticaret tek tip, anlamsız. Ekonomi simüle edilemiyor.

**Gerekli:** Item değer sistemi, arz/talep mekanizması, müzakere dialouğu.

---

### 3.3 Goals / Beliefs / Memory Karar Almayı Etkilemiyor ✅ Kısmen çözüldü (v1.4.0)

**Önceki sorun:** Bu üç sistem veriyi _depolar_ ama `UtilityEvaluator` ya da action'lar bunları _okumaz_.

**v1.4.0'da çözülen (G1 + G2 + G3 + G6):**
- `ActionContext.belief_score(subject)` ve `goal_bonus(goal_type)` helper'ları eklendi.
- `WalkToAction.evaluate()` artık hedef zone için `get_memory_threat_bias` × 0.6 + `belief_score` × 0.4 bias hesaplıyor ve survival walk'larda ±0.15, exploration walk'larda ±0.40 modülasyon yapıyor.
- `AttackAction.evaluate()` hedef NPC'nin belief valence'ını okur; `≤ -0.3` valence saldırı skoruna `+0.25`, `≥ +0.3` valence ise `-0.40` ekler.
- Aktif goal'lar (`FindFood`, `FindWater`, `Rest`, `Socialize`, `Trade`, `Work`, `Pray`, `Heal`, `Survive`, `Attack`) ilgili action skoruna `+0.25` katkı sağlıyor.

**Hâlâ açık (v1.5 hedefleri):**
- LLM reasoning çıktısı kendi hafızasına yazılmıyor (G7 — v1.5).
- Diğer action'lar (TradeAction, WorkAction) belief sorgusu yapmıyor — sadece WalkTo ve Attack.

---

### 3.4 Algı Sistemi Zayıf

**Sorun:** NPCler "NPC percept" alabiliyorlar ama hangi NPC'nin kim olduğunu, nasıl hissettğini, ne taşıdığını bilmiyorlar. Social percept çok sığ.

**Etki:** LLM sosyalleşme kararı alırken karşısındakinin identity'sini bilmiyor.

**Gerekli:** NPC-NPC algısında identity, ilişki durumu, görünür duygular.

---

### 3.5 Dünya Statik

**Sorun:** 10 zone sabit koordinat. Kaynak üretimi/tükenmesi yok. Dinamik olaylar yok (savaş, festival, hastalık salgını, kıtlık). Gece/gündüz sadece schedule tercihini etkiliyor.

**Etki:** Dünya dekor. NPC'lerin tepki verecekleri emergent durumlar oluşmuyor.

**Gerekli:** Zone resource state, event injection sistemi, dünya olayı propagasyonu.

---

## 4. LLM: Şu An vs Hedef

### 4.1 LLM Şu An Ne Yapıyor

LLM **yalnızca interrupt'ta** devreye giriyor (tehdit ≥ 0.8 veya HP düşüşü ≥ 15). Normal zamanlarda Utility AI her şeyi yönetiyor.

**Giriş** (NPCSerializer → minified JSON):
```
id, arch, occ, faction, b5, traits, vitals, emo, inv, time, pos(zone+landmark),
percepts(max 5), memories(top 3 duygusal), beliefs(max 5), factions(trust), 
goals_top, sched, interrupt, valid_actions
```

**Şu anki çıktı:**
```json
{
  "npc_id": "npc_a3b8f70a",
  "reasoning": "Kurt çok yakın. Açım ama önce tehlikeden uzaklaşacağım.",
  "selected_action": {
    "action_id": "flee",
    "target_id": null,
    "dialogue": null
  },
  "emotion": "Fearful"
}
```

**Sorunlar:**
1. `dialogue` üretilince bir yere gitmiyor — karşı NPC duymaz
2. `emotion` kaydediliyor ama `psychology.set_fear()` gibi bir etki üretmiyor
3. `reasoning` log'a düşüyor ama NPC'nin kendi hafızasına eklenmiyor
4. Sosyal kararlar (socialize/trade) için karşı NPC'nin state'i LLM'e hiç verilmiyor
5. Uzun vadeli karakter tutarlılığı yok — her interrupt bağımsız bir "an"

---

### 4.2 LLM Ne Yapmalı (Hedef Mimari)

#### Tetiklenme Koşulları Genişletilmeli

| Mevcut | Hedef |
|--------|-------|
| Tehdit ≥ 0.8 | Tehdit ≥ 0.8 |
| HP düşüşü ≥ 15 | HP düşüşü ≥ 15 |
| — | NPC ile yakın mesafeye girildi (Social percept) |
| — | Kritik karar anı: ticaret teklifi alındı |
| — | Uzun süre (N tick) önemli bir şey yaşanmadı (reflection) |

#### Sosyal Kararlar İçin Çift Taraflı Payload

Socialize/Trade için LLM, **hem konuşan hem dinleyen** NPC'nin özetini almalı:

```json
{
  "self": { "...mevcut NPC state..." },
  "target": {
    "id": "npc_02",
    "name": "Elena",
    "occ": "Merchant",
    "relation": { "trust": 0.65, "affinity": 0.4, "type": "Friend" },
    "mood": "Happy",
    "known_facts": ["Banditlerin baskını duyumu", "Market fiyatları"]
  }
}
```

#### Hedef Çıktı Şeması (v2.0)

```json
{
  "npc_id": "npc_a3b8f70a",
  "reasoning": "Elena'ya güveniyorum. Banditleri duymuşum, uyarmalıyım.",
  "selected_action": {
    "action_id": "socialize",
    "target_id": "npc_02",
    "dialogue": "Elena, dikkat et — orman yolunda banditler varmış, üç köylü yaralandı.",
    "tone": "urgent",
    "information_shared": "bandit_sighting",
    "gift_item": null
  },
  "emotion": "Concerned",
  "state_effects": {
    "self_belief_update": { "subject": "forest_road", "valence": -0.6 },
    "memory_note": "Warned Elena about bandits at market"
  }
}
```

**Yenilikler:**
- `tone` → ses tonu (`friendly`, `hostile`, `urgent`, `playful`, `formal`)
- `information_shared` → hangi bilginin transfer edildiği (gossip chain için)
- `state_effects` → LLM'in önermesi, sistem uygulamak zorunda değil ama rehber
- `memory_note` → kendi hafızasına ne kaydedilmeli

---

### 4.3 LLM Eğitimi — Mevcut vs Gerekli

#### Mevcut Dataset (v4 Generator)

| Dosya | Adet | İçerik |
|-------|------|--------|
| `train_reasoner.jsonl` | 10,000 | Durum → Türkçe CoT iç monolog |
| `train_formatter.jsonl` | ~12,000 | CoT → JSON dönüşümü |

Dağılım: %35 tehdit, %20 açlık/susuzluk, %15 enerji kritik, %30 sosyal.

#### Eksik Dataset Kategorileri

**A. Diyalog Çiftleri (Öncelik: Kritik)**  
NPC A bir şey söyler → NPC B state'i güncellenir → NPC B cevap verir.

```jsonl
// Örnek: gossip transferi
{
  "input": { "self_state": "...", "target_state": "...", "context": "Elena'ya rastladım" },
  "reasoner_output": "Elena'ya banditleri anlatmalıyım, güveniyorum.",
  "formatter_output": {
    "dialogue": "Elena, dikkat et — orman yolunda banditler var.",
    "tone": "urgent",
    "information_shared": "bandit_sighting"
  }
}
```

**B. Hafıza-Güdümlü Kararlar**  
Geçmiş deneyim → şimdiki karar değişikliği.

```jsonl
// Örnek: kötü anı → güvensizlik
{
  "memories": [{"evt": "Betrayal", "desc": "Kira beni soydu", "ew": -0.9}],
  "percepts": [{"id": "npc_kira", "tag": "NPC"}],
  "reasoning": "Kira beni soymuştu. Trade değil, uzak duracağım.",
  "action_id": "walk_to"  // socialize yerine
}
```

**C. İnanç-Güdümlü Kararlar**  
Yüksek güvenli inanç → action seçimini etkiler.

**D. Ticaret Müzakeresi (Öncelik: Yüksek)**  
Fiyat teklifi — karşı teklif — anlaşma/anlaşamama döngüsü.

**E. Ahlaki Çatışmalar**  
`Devout` trait + açlık → çal mı, dua mı? `Greedy` + ittifak baskısı → hain mi, sadık mı?

**F. Uzun Vadeli Karakter Tutarlılığı**  
Aynı NPC'nin birden fazla gün boyunca tutarlı kişilik sergilemesi.

#### Önerilen Dataset Dağılımı (v5 Generator Hedefi)

| Kategori | Oran | Açıklama |
|----------|------|----------|
| Hayatta kalma kararları | %20 | Açlık, susuzluk, tehdit — mevcut |
| Sosyal etkileşim (basit) | %20 | Selamlama, hava durumu, gündelik |
| Bilgi transferi (gossip) | %15 | Duyumu aktarma, uyarı |
| Ticaret müzakeresi | %15 | Fiyat, takas, red |
| Ahlaki çatışma | %10 | İki değer çatışması |
| Hafıza-güdümlü | %10 | Geçmiş deneyim etkisi |
| Acil durum (interrupt) | %10 | Tehdit, saldırı, ani HP düşüşü |

---

## 5. Geliştirme Yol Haritası

### v1.4 — Entegrasyon ✅ Tamamlandı (2026-05-11)

**Hedef:** Mevcut veri yapılarını karar almaya bağla. Yeni sistem yazmadan, var olanı konuştur.

| Görev | Dosya | Durum |
|-------|-------|-------|
| G1 ✅ | `npc_sim/decisions/action_context.py` | `belief_score(subject)` + `goal_bonus(goal_type)` helper'ları eklendi |
| G2 ✅ | `npc_sim/decisions/actions/builtin.py` | `WalkToAction.evaluate()` hedef zone için memory_bias + belief_score modülasyonu uyguluyor |
| G3 ✅ | `npc_sim/decisions/actions/builtin.py` | `AttackAction.evaluate()` hedef belief valence'ına göre +0.25 / -0.40 boost/penalty |
| G4 ✅ | `npc_sim/decisions/actions/builtin.py` | `SocializeAction.execute()` → LLM dialogue (veya placeholder) target memory'sine `Dialogue` event olarak yazılıyor |
| G5 ✅ | `npc_sim/decisions/actions/builtin.py` | `SocializeAction.execute()` → en yüksek confidence belief'i target'a sönümlü olarak aktarıyor, trust ≥ 0.3 koşullu |
| G6 ✅ | `npc_sim/decisions/action_context.py` + `builtin.py` | Tüm survival ve davranış action'larına active goal bonus (+0.25) eklendi |
| G7 → v1.5 | `npc_sim/llm/llm_decision_system.py` | `reasoning` çıktısı NPC hafızasına yazılmadı — sonraki tura |
| G8 → v1.5 | `npc_sim/llm/npc_serializer.py` | Sosyal kararlarda hedef NPC `target_context` payload'a eklenmedi — sonraki tura |

**Doğrulama (gerçekleşen):** Diagnostic koşu (6 sim-hours, seed=42, 5 archetypes) sonrası `logs/sim_full.csv` analizi:
- Stress mean: 0.745 → 0.532 (-29 %)
- `anger ≥ 0.7 AND happiness ≥ 0.7`: 0 satır
- Sosyalleşme sonrası `top_memory_desc` "Dialogue" event'ini içeriyor (gözlemsel)

---

### v1.5.0 — Tamamlandı (2026-05-12)

Risk-first triage: uzun-vade stabilite (Phase A) → entegrasyon boşlukları
(Phase B) → tracker polish (Phase C). 17 atomik commit, 68 pytest case,
3 × 30 sim-day `--strict` milestone.

**Phase A — uzun-vade stabilite (audit'ten gelen, tracker dışı):**

| Görev | Dosya | Açıklama |
|-------|-------|----------|
| A1 ✅ | `npc_sim/npc/inventory.py` | `NPCInventory.add()` `stack_cap=100` parametresi — WorkAction sınırsız üretim engellendi |
| A2 ✅ | `npc_sim/npc/beliefs.py` | `BeliefSystem` LRU cap 200 + `<0.05` confidence prune |
| A3 ✅ | `npc_sim/npc/social.py` | `NPCSocial.relations` aynı politika (LRU 200 + prune) |
| A4 ✅ | `npc_sim/simulation/faction_registry.py` | Cleanup eşiği `1e-6` → `0.01` (fp drift'e takılan dispositions temizlenir) |
| A5 ✅ | `npc_sim/npc/memory.py` | `MemoryEntry.decay()` additive → multiplicative — eski salient anılar göreceli ayırt edilebilir kalır |
| A6 ✅ | `npc_sim/diagnostics/sim_logger.py` | `rotate_every_rows=1_000_000` — `sim_full.NNNN.csv` arşivleri |
| A7 ✅ | `npc_sim/diagnostics/invariants.py` (YENİ) + `run_diagnostic.py --strict` | Vital range / NaN / dict cap / inventory cap / memory overflow safety net |

**Phase B — entegrasyon boşlukları (`integration_map.md`):**

| Görev | Dosya | Açıklama |
|-------|-------|----------|
| B1 ✅ | `npc_sim/decisions/actions/builtin.py` (TradeAction) | `evaluate()` `ctx.belief_score(target_id)` okur; başarılı trade çift yönlü belief reinforce eder |
| B2 ✅ | `npc_sim/decisions/actions/builtin.py` (WorkAction) + `world_map.py` | Workplace-safety belief okur; yeni `WorldMap.get_home_zone_name()` |
| B3 ✅ | `npc_sim/decisions/actions/builtin.py` (Socialize, Trade) | `target.social.reputation` Utility AI'a bağlandı |
| B4 ✅ | `npc_sim/decisions/action_context.py` + `simulation_manager.py` + `builtin.py` (Attack, Socialize) | Yeni `ctx.faction_disposition(target_id)` helper'ı |

**Phase C — tracker polish (5 pending bug):**

| Görev | Bug | Dosya | Açıklama |
|-------|-----|-------|----------|
| C1 ✅ | #15 | `builtin.py` (WorkAction) | `yield_amount = max(1, int(efficiency * 2))` — efficiency artık miktarı etkiliyor |
| C2 ✅ | #20 | `llm_decision_system.py` | Trait coherence Coward / Greedy / Devout için genişledi |
| C3 ✅ | #17 | `sim_config.py` + 4 ek dosya | Kullanılmayan `llm_tick_every` field'ı kaldırıldı |
| C4 ✅ | #18 | `llm_request_queue.py` | INTERRUPT in-flight lower-priority isteği `_cancelled` işaretler, callback short-circuit |
| C5 ✅ | #16 | `docs/architecture.md` + `docs/llm_data_spec.md` | DualLLM "planned, not implemented" callout'ları eklendi |

**Doğrulama (Phase A/B/C sonu, 30 sim-day `--strict` milestone, seed=42, 5 archetypes):**
- 432 001 tick / 109 s real-time, 5/5 NPC sağ, 0 invariant violation
- Mean stress ≈ 0.10 (v1.4.0'da 0.532 idi — multiplicative memory decay etkisi)
- Action distribution deterministik replay (Phase A/B/C arasında bit-identical)
- Inventory cap çalıştığı doğrulandı (Merchant gold doymuş, exact 100)

---

### v1.6+ — LLM Genişletme (Öneri: 2-3 hafta)

| Görev | Dosya | Açıklama |
|-------|-------|----------|
| G7 | `npc_sim/llm/llm_decision_system.py` | `reasoning` sonucu NPC'nin kendi hafızasına `MemoryEntry` olarak ekle |
| G8 | `npc_sim/llm/npc_serializer.py` | Sosyal kararlar için hedef NPC'nin özetini payload'a ekle (`target_context`) |
| G9 ✅ | `npc_sim/llm/llm_backend.py` | `DualLLMBackend` implement edildi (v1.6.0); H6 CoT gate + npc_id injection |

---

### v2.0 — Dinamik Dünya (Öneri: 1-2 ay)

**Hedef:** Emergent olayların oluşabileceği dinamik bir dünya ortamı.

| Görev | Bileşen | Açıklama |
|-------|---------|----------|
| D1 | `npc_sim/simulation/zone_state.py` (YENİ) | Zone başına resource miktarı, güvenlik seviyesi, NPC yoğunluğu |
| D2 | `npc_sim/decisions/actions/builtin.py` | `GatherAction` Zone resource'unu tüketsin; resource sıfırda `is_valid()` False dönsün |
| D3 | `npc_sim/simulation/world_event_system.py` (YENİ) | Periyodik dünya olayları: pazar günü, salgın, bandit baskını, festival |
| D4 | `npc_sim/simulation/faction_registry.py` | Faction olayları: savaş ilanı, barış, ittifak — NPC kararlarını tetiklesin |
| D5 ✅ | `npc_sim/llm/llm_backend.py` | `DualLLMBackend` implement edildi (v1.6.0) — bkz. G9 |
| D6 | `npc_sim/npc/inventory.py` | Item fiyat tablosu, arz/talep sinyali |
| D7 | `npc_sim/decisions/actions/builtin.py` | `TradeAction` müzakere döngüsü: teklif → karşı teklif → kabul/red |
| D8 | `npc_sim/simulation/gossip_system.py` (YENİ) | Bilgi yayılımı: NPC sosyalleşince belief'ler yayılır (gossiping chain) |
| D9 | `server.py` + `static/` | Dashboard: zone resource haritası, faction durumu, aktif olaylar |

---

### v3.0 — Yaşayan Medeniyet (Öneri: 3-6 ay)

**Hedef:** Uzun vadeli anlatı ve NPC yaşam döngüsü.

| Görev | Açıklama |
|-------|----------|
| V1 | NPC yaşam döngüsü: doğum, büyüme, yaşlanma, ölüm — yeni NPC'ler organik olarak eklensin |
| V2 | Uyku sırasında hafıza konsolidasyonu — güçlü anılar pekişir, zayıflar silinir |
| V3 | Kültürel inanç sistemi: Faction üyelerinin ortak inançları olsun |
| V4 | Çoklu ekonomik ajan: piyasa fiyatı emergent olarak oluşsun |
| V5 | Kalıcı sim durumu: save/load, run aralarında NPC ilişkileri korunsun |
| V6 | Dataset'i canlı simülasyondan otomatik oluştur (self-play veri üretimi) |

---

## 6. DualLLMBackend — Implementasyon Taslağı

Dokümanda tanımlı, kodda yok. İşte yapılması gerekenler:

```python
# npc_sim/llm/llm_backend.py içine eklenecek

class DualLLMBackend(ILLMBackend):
    """
    Component A (Reasoner, ~3B) → Türkçe CoT metni
    Component B (Formatter, ~1B) → Strict JSON LLMResponse
    
    İki ayrı Ollama instance'ı gerektirir:
    - Reasoner: OLLAMA_HOST=127.0.0.1:11434
    - Formatter: OLLAMA_HOST=127.0.0.1:11435
    """

    def __init__(self,
                 reasoner_model: str = "npc-sim-reasoner",
                 formatter_model: str = "npc-sim-formatter",
                 reasoner_url: str = "http://localhost:11434",
                 formatter_url: str = "http://localhost:11435"):
        self._reasoner = OllamaBackend(reasoner_model, reasoner_url)
        self._formatter = OllamaBackend(formatter_model, formatter_url)

    def call(self, npc_id: str, payload_json: str, timeout: float = 5.0) -> LLMResponse:
        # Adım 1: Reasoner → Türkçe iç monolog
        cot_text = self._reasoner.call_raw(npc_id, payload_json, timeout / 2)
        # Adım 2: Formatter → JSON (CoT'u input olarak alır)
        return self._formatter.call(npc_id, cot_text, timeout / 2)

    def is_available(self) -> bool:
        return self._reasoner.is_available() and self._formatter.is_available()
```

**SimulationConfig'e eklenecek:**
```python
llm_reasoner_url: str = "http://localhost:11434"
llm_formatter_url: str = "http://localhost:11435"
llm_backend: str = "ollama"  # "ollama" | "dual" | "mock"
```

---

## 7. Dataset Üretimi — v5 Generator Gereksinimleri

Mevcut `npc_sim_generator_v2.py` şunları üretiyor:
- Tek NPC durumu → iç monolog + action JSON
- 5 arketip × senaryo varyasyonları

**v5 Generator'ın üretmesi gerekenler:**

### 7.1 Gossip Chain Veri Formatı

```python
# NPC A → B'ye bilgi aktarır, B → C'ye aktarır
chain = [
    {"from": "npc_01", "to": "npc_02", "info": "bandit_sighting", "accuracy": 1.0},
    {"from": "npc_02", "to": "npc_03", "info": "bandit_sighting", "accuracy": 0.7},  # bozulma
]
```

### 7.2 Ticaret Müzakere Dizisi

```python
# Çok turlu diyalog örneği
turns = [
    {"speaker": "merchant", "dialogue": "Bu baltayı 5 altına alır mısın?", "action": "trade_offer", "price": 5},
    {"speaker": "guard",    "dialogue": "3 altın, daha yeni dövülmüş değil.", "action": "counter_offer", "price": 3},
    {"speaker": "merchant", "dialogue": "Tamam, 4 altın — son fiyat.", "action": "accept"},
]
```

### 7.3 Hafıza Önyargılı Senaryo

```python
# Aynı durum, farklı hafıza → farklı karar
scenario_base = {"percepts": [{"id": "npc_kira", "tag": "NPC"}], ...}

scenario_positive_memory = {**scenario_base, "memories": [{"evt": "Gift", "desc": "Kira helped me", "ew": 0.8}]}
# Beklenen çıktı: action_id="socialize"

scenario_negative_memory = {**scenario_base, "memories": [{"evt": "Betrayal", "desc": "Kira stole from me", "ew": -0.9}]}
# Beklenen çıktı: action_id="walk_to" (kaçınma)
```

---

## 8. LLM Eğitim Metrikleri — Hedefler

| Metrik | Mevcut Hedef | v2.0 Hedef |
|--------|-------------|------------|
| `action_id` geçerlilik oranı | ≥ %98 | ≥ %99 |
| JSON parse başarısı | ≥ %99 | ≥ %99.5 |
| `reasoning` token uzunluğu | 30-100 | 40-120 |
| Interrupt doğru flee/attack | ≥ %85 | ≥ %90 |
| Sosyal kararда doğru `tone` | — | ≥ %80 |
| Gossip bilgi doğruluğu | — | ≥ %70 |
| Hafıza önyargısı tutarlılığı | — | ≥ %75 |
| Trait coherence violation | ≤ %2 | ≤ %1 |
| Fallback oranı (canlı sim) | ≤ %5 | ≤ %3 |

---

## 9. Teknik Borç — Kapatılması Gerekenler

| # | Dosya | Sorun | Öncelik |
|---|-------|-------|---------|
| T1 | `npc_sim/llm/npc_serializer.py:162` | `_valid_actions()` world adapter'dan action library alıyor — kırılgan fallback | Yüksek |
| T2 | `npc_sim/decisions/decision_system.py:86` | Action lock execute'dan sonra oluşturuluyor — ilk tick korumasız | Orta |
| T3 | `npc_sim/npc/npc_factory.py` | Tüm NPC'ler erkek veya "Unknown" cinsiyette başlıyor | Düşük |
| T4 | `npc_sim/simulation/world_map.py` | Zone'lar hardcoded — config dosyasından yüklenebilir olmalı | Orta |
| T5 ✅ | `npc_sim/llm/llm_backend.py` | DualLLMBackend implement edildi (v1.6.0) | — |
| T6 | `docs/bugs_and_issues.md:#13` | Action lock execute'dan sonra oluşuyor | Orta |
| T7 | `npc_sim/npc/social.py` | Faction'lar yerine bireysel trust serializer'da gösteriliyor — karışıklık | Düşük |
| T8 | Genel | `test_llm_smoke.py` çok dar — unit testler yok | Yüksek |

---

## 10. Öncelik Sırası (Şimdi Ne Yapılmalı)

```
✅ Tamamlandı (v1.4.0 — 2026-05-11):
  1. G1 + G2 + G3: ActionContext belief/memory helper'ları, WalkTo + Attack bias
  2. G4 + G5: SocializeAction dialogue transferi + belief yayılımı
  3. G6: Active goal → action skor bonusu
  4. Psikoloji stabilizasyon: stres ölçeklemesi + anger/happiness cross-inhibition

✅ Tamamlandı (v1.5.0 — 2026-05-12):
  1. A1–A7: uzun-vade stabilite (inventory cap, dict eviction, faction cleanup,
            multiplicative memory decay, log rotation, invariant framework)
  2. B1–B4: TradeAction beliefs + WorkAction zone safety + reputation reads +
            faction disposition Utility AI
  3. C1–C5: tracker polish (#15 work efficiency, #20 trait coherence, #17
            llm_tick_every kaldırıldı, #18 queue preemption, #16 doc sync)
  4. Test altyapısı: tests/ dizini (68 case) + run_diagnostic.py --strict

✅ Tamamlandı (v1.6.0 — 2026-05-17):
  1. G9: DualLLMBackend implement edildi (H6 gate + npc_id injection)
  2. Generator redesign: multi-factor decision model (R5, R6, R7, R9, R12, R14)
  3. Training fixes: packing=False, response masking, Formatter base swap (R1–R4)
  4. Persona card + Gemma 3 4B bootstrap CoT pipeline
  5. docs/llm_pipeline.md (canonical pipeline doc)

Hemen (v1.7):
  1. G10: LLM reasoning'i NPC hafızasına yaz (SelfThought event)
  2. G11: LLM emotion → NPC psychology 0.3 ağırlıklı harmanlama
  3. G12: CoT → BeliefSystem (implicit beliefs, 0.3 confidence)
  4. G13: CoT future-intent → NPCGoals.enqueue (soft goals)
  5. G14: Multi-turn dialogue state (dialogue_context ring buffer)
  6. G15: LLM-gözleminden trait kazanımı (N-tutarlı emotion → trait list)
  7. G16: Runtime UtilityEvaluator ← multi-factor model hizalaması

Kısa vadeli (v2.0 - 1. adım):
  6. D1: ZoneState sistemi (resource miktarı)
  7. D3: WorldEventSystem (periyodik olaylar)
  8. D8: GossipSystem (G5'in genişletilmiş hali)

Uzun vade (v3.0):
  9. V1: NPC yaşam döngüsü (birth/aging/death)
 10. V6: Self-play dataset üretimi
```

---

## 11. LLM Çıktısının Derin Kullanımı (v1.7+ Yol Haritası)

**Bağlam:** v1.6.0 sonrası `LLMResponse` derin bir biliş sinyali taşıyor (`reasoning` CoT, `emotion`, `dialogue`, `target_id`, `selected_action`). Ancak çalışma zamanı bu zenginliğin yalnızca `action_id` ve `dialogue`-for-socialize/trade kısmını tüketiyor. Aşağıdaki görevler, LLM beyninin ürettiği derinliği NPC'nin uzun süreli durumuna geri besleyerek "düşünen NPC" hissini kazandırır.

| Görev | Dosya | Açıklama |
|-------|-------|----------|
| **G10** | `npc_sim/llm/llm_decision_system.py` `_apply_pending()` | LLM `reasoning` (tam CoT) bir `SelfThought` event'i olarak `npc.memory.add()`'e yazılsın. `emotional_weight` = (happiness − fear) baz alınsın. Diyalog dışı tüm action'lar için bu yapılmalı. (G7'nin tamamlanması.) |
| **G11** | `npc_sim/llm/llm_decision_system.py` `_apply_pending()` | LLM `emotion` alanı NPC'nin baskın duygusuna 0.3 ağırlıkla harmanlansın (`set_happiness/fear/anger` üzerinden, mood label yeniden hesaplansın). Şu an emotion runtime'da kullanılmıyor. |
| **G12** | `npc_sim/llm/cot_parser.py` (yeni) | CoT içindeki entity referansları + sentiment kelimeleri regex/keyword ile yakalansın → `BeliefSystem.add_belief()` düşük confidence (0.3) ile yazsın. İlk versiyon kelime listesi tabanlı; v1.8'de Formatter'a "implicit_beliefs" alanı ekleme seçeneği. |
| **G13** | `npc_sim/npc/goals.py` + parser | CoT'ta gelecek-niyet ifadeleri ("sonra tapınağa gideceğim", "yarın pazara") → `NPCGoals.enqueue()` düşük öncelikli soft-goal olarak. Saturation guard: tek seferde max 2 enqueue. |
| **G14** | `npc_sim/social/dialogue_state.py` (yeni) + `SocializeAction.execute()` | Diyalog tek-atış değil; konuşma durumu (last_speaker, last_topic, turn_count, target_id) per-NPC ring buffer'da tutulsun. LLM bir sonraki socialize için bu bağlamı görsün (`npc_serializer.py` payload'a `dialogue_context` alanı ekle). Çok-turn konuşmalar mümkün olur. |
| **G15** | `npc_sim/npc/traits.py` + `_apply_pending()` | LLM N tik üst üste aynı emergent trait sergilerse (örn. `emotion="Devout"` 10× / 50 tik) NPC'nin `traits` listesine eklensin (cap = 6). LLM gözleminden trait kazanım/kayıp loop. Kalıcı kişilik evrimi. |
| **G16** | `npc_sim/decisions/utility_evaluator.py` + tüm 12 action `evaluate()` | Generator'da kullanılan multi-factor karar modelini (`self_power`, `perceived_threat`, `duty_pull`) `UtilityEvaluator`'a entegre et. Şu an LLM ile Utility AI farklı puanlama yapıyor → LLM Brain devre dışıyken NPC davranışı farklı görünüyor. |

**Bağımlılıklar:** G10→G11→G12 sıralı. G13 bağımsız. G14 G10'a bağlı. G15 G10+G11 üzerine kurulur. G16 bağımsız ama büyük refactor.

**Kabul kriteri (v1.7 release-gate):**
- 24-saatlik diagnostic run sonunda her NPC'nin memory'sinde ≥ 1 `SelfThought` entry (G10)
- LLM-driven emotion shift CSV'de gözlemlenebilir; mood label değişimi LLM call'lar etrafında lokalize (G11)
- En az %30 NPC'de LLM-kaynaklı belief entry mevcut (G12)
- Çok-turn diyalog: aynı çiftin 2+ sıralı socialize'ı CSV'de görülüyor (G14)
- LLM kapalı vs açık run'da action distribution farkı < %15 (G16 hizalama testi)

---

## 11. Başarı Kriterleri — "Yaşayan Dünya" Testleri

Aşağıdaki senaryolar gerçekçi çalıştığında v2.0 hazır sayılır:

1. **Gossip Testi:** Bandit saldırısı NPC A'nın yakınında gerçekleşir. 10 sim-dakika içinde en az 3 NPC bu bilgiye sahip olur (beliefs'te `bandits: conf > 0.5`).

2. **Güven Testi:** NPC A, NPC B tarafından soyulur (TradeAction: aldatma). Sonraki encounter'da NPC A, NPC B ile ticareti reddeder (SocializeAction yerine WalkToAction seçer).

3. **Ekonomi Testi:** Market zone'da 5 Farmer yoğun GRAIN üretirse GRAIN fiyatı düşer. Bir Merchant bu fiyatla GRAIN satın alıp başka zone'da yüksek fiyata satar (arbitraj davranışı).

4. **Kriz Testi:** Kıtlık olayı (food zone'da resource=0). NPCler alternatif kaynak arar; bazıları çalmaya yönelir (`Greedy` trait), bazıları paylaşır (`Generous` trait).

5. **Anlatı Testi:** Aynı seed ile 24 sim-saati koşulunca, her NPC için anlamlı bir hikaye özetlenebilir (kim kimle konuştu, ne öğrendi, ne hissetti, ne değişti).

---

*Bu belge canlıdır. Her sürüm güncellemesinde ilgili görevler tamamlandı/değiştirildi olarak işaretlenmelidir.*
