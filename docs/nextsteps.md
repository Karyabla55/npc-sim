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
| Sosyal ilişkiler | ✅ Veri mevcut | Trust/affinity/respect — ama karar almayı ETKİLEMİYOR |
| İnançlar (BeliefSystem) | ✅ Veri mevcut | Event tabanlı güncellenme — ama karar almayı ETKİLEMİYOR |
| Hedefler (GoalSystem) | ✅ Veri mevcut | Priority sorted — ama action'lar bağımsız is_valid() kullanıyor |
| Trait'ler | ✅ Kısmen entegre | 4 action tipini etkiliyor (flee/attack/trade/explore) |
| Envanter | ✅ Çalışıyor | Slot tabanlı, 10 item tipi |
| Schedule | ✅ Çalışıyor | Meslek bazlı, tercih eğrileri |
| Faction sistemi | ✅ Veri mevcut | Disposition matrix, decay — ama NPC kararlarını ETKİLEMİYOR |
| World Map | ✅ Çalışıyor | 10 sabit zone, koordinat tabanlı |
| SimLogger | ✅ Tam işlevsel | 44 sütun CSV, zero-overhead toggle |
| LLM pipeline (interrupt) | ✅ Çalışıyor | Async, priority queue, 5 hardening mekanizması |
| LLM payload (NPCSerializer) | ✅ Çalışıyor | Token-verimli JSON, tüm state dahil |
| DualLLMBackend | ❌ Yok | Dokümanda var, kodda yok |
| Web dashboard | ⚠️ Temel | State görüntüleme var, LLM kontrol eksik |

---

## 3. Temel Eksikler — Yaşayan Dünya İçin

### 3.1 NPC-NPC İletişimi Gerçek Değil

**Sorun:** `SocializeAction.execute()` iki NPC'nin `.interact()` metodunu çağırır. Bu trust/affinity günceller ama:
- LLM'in ürettiği `dialogue` karşı NPC'ye ulaşmıyor
- Konuşulan şey hafızaya yazılmıyor
- Bilgi (dedikodu, uyarı, haber) karşıya geçmiyor
- Karşı NPC'nin durumu (ne hissediyor, ne biliyor) LLM'e verilmiyor

**Etki:** NPCler fiziksel olarak sosyalleşiyor ama entelektüel olarak sessiz bir dünya.

**Gerekli:** Diyalog içerik transferi, bilgi yayılımı (gossip chain), hafıza güncelleme.

---

### 3.2 Ekonomi Taslak Seviyede

**Sorun:** `TradeAction.execute()` hardcoded GOLD ↔ FOOD takas yapıyor. Fiyat yok, müzakere yok, piyasa dinamiği yok. `WorkAction` mesleğe göre item üretiyor (Farmer→GRAIN) ama bu üretimin taleple bağlantısı yok.

**Etki:** Ticaret tek tip, anlamsız. Ekonomi simüle edilemiyor.

**Gerekli:** Item değer sistemi, arz/talep mekanizması, müzakere dialouğu.

---

### 3.3 Goals / Beliefs / Memory Karar Almayı Etkilemiyor

**Sorun:** Bu üç sistem veriyi _depolar_ ama `UtilityEvaluator` ya da action'lar bunları _okumaz_.

```
NPC hafızasında "Market'te dövüldüm" kaydı var
→ WalkToAction hâlâ Market'e gitmeyi öneriyor
→ Çünkü WalkToAction hafızaya bakmıyor
```

**Etki:** NPCler yaşadıklarından ders çıkarmıyor. Deneyim boşa gidiyor.

**Gerekli:** Hafıza-bilgi-hedef üçgenini action evaluation'a bağlayan boru hattı.

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

### v1.3 — Entegrasyon (Öneri: 2-3 hafta)

**Hedef:** Mevcut veri yapılarını karar almaya bağla. Yeni sistem yazmadan, var olanı konuştur.

| Görev | Dosya | Açıklama |
|-------|-------|----------|
| G1 | `npc_sim/decisions/action_context.py` | `ActionContext`'e `memory_bias(event_type)` ve `belief_score(subject)` helper ekle |
| G2 | `npc_sim/decisions/actions/builtin.py` | `WalkToAction.evaluate()` hafıza önyargısına göre zone skoru düşür/artır |
| G3 | `npc_sim/decisions/actions/builtin.py` | `AttackAction.evaluate()` hedef NPC'ye dair inanç valence'ını skora ekle |
| G4 | `npc_sim/decisions/actions/builtin.py` | `SocializeAction.execute()` → dialogue string'i karşı NPC'ye `witness_event()` ile ilet |
| G5 | `npc_sim/decisions/actions/builtin.py` | `SocializeAction.execute()` → paylaşılan bilgi (`information_shared`) karşı NPC'nin `beliefs`'ine ekle |
| G6 | `npc_sim/npc/goals.py` + `builtin.py` | Active goal türü action score'larını etkilesin (`GoalType.FindFood` aktifse EatAction +0.25 bonus) |
| G7 | `npc_sim/llm/llm_decision_system.py` | `reasoning` sonucu NPC'nin kendi hafızasına `MemoryEntry` olarak ekle |
| G8 | `npc_sim/llm/npc_serializer.py` | Sosyal kararlar için hedef NPC'nin özetini payload'a ekle (`target_context`) |

**Doğrulama:** `run_diagnostic.py`'a yeni check'ler ekle:
- Sosyalleşme sonrası karşı NPC'nin belief/memory güncellendiği
- Hafıza önyargısının WalkTo zone seçimini etkilediği

---

### v2.0 — Dinamik Dünya (Öneri: 1-2 ay)

**Hedef:** Emergent olayların oluşabileceği dinamik bir dünya ortamı.

| Görev | Bileşen | Açıklama |
|-------|---------|----------|
| D1 | `npc_sim/simulation/zone_state.py` (YENİ) | Zone başına resource miktarı, güvenlik seviyesi, NPC yoğunluğu |
| D2 | `npc_sim/decisions/actions/builtin.py` | `GatherAction` Zone resource'unu tüketsin; resource sıfırda `is_valid()` False dönsün |
| D3 | `npc_sim/simulation/world_event_system.py` (YENİ) | Periyodik dünya olayları: pazar günü, salgın, bandit baskını, festival |
| D4 | `npc_sim/simulation/faction_registry.py` | Faction olayları: savaş ilanı, barış, ittifak — NPC kararlarını tetiklesin |
| D5 | `npc_sim/llm/llm_backend.py` | `DualLLMBackend` implement et (Reasoner port:11434, Formatter port:11435) |
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
| T5 | `docs/bugs_and_issues.md:#16` | DualLLMBackend dokümanda var, kodda yok | Kritik |
| T6 | `docs/bugs_and_issues.md:#13` | Action lock execute'dan sonra oluşuyor | Orta |
| T7 | `npc_sim/npc/social.py` | Faction'lar yerine bireysel trust serializer'da gösteriliyor — karışıklık | Düşük |
| T8 | Genel | `test_llm_smoke.py` çok dar — unit testler yok | Yüksek |

---

## 10. Öncelik Sırası (Şimdi Ne Yapılmalı)

```
Hemen (v1.3):
  1. G4 + G5: SocializeAction diyalog transferi + belief yayılımı  ← En yüksek etki
  2. G1 + G2: ActionContext'e memory_bias, WalkTo'ya hafıza etkisi
  3. G7: LLM reasoning'i NPC hafızasına yaz
  4. T1: _valid_actions() sağlamlaştır

Kısa vadeli (v2.0 - 1. adım):
  5. T5: DualLLMBackend implement et
  6. D1: ZoneState sistemi (resource miktarı)
  7. D3: WorldEventSystem (periyodik olaylar)
  8. D8: GossipSystem

Uzun vade (v3.0):
  9. V1: NPC yaşam döngüsü
  10. V6: Self-play dataset üretimi
```

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
