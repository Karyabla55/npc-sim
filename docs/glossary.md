# Terim Sözlüğü — NPC-Sim

Kod okunurken karşılaşılan tüm kısaltmalar, mimari kodlar ve teknik terimler için Türkçe referans.

---

## 1. Kısaltmalar ve Kısa Değişken Adları

### 1.1 Tek ve Çift Harfli Değişkenler

| Kısaltma | Açılımı | Türkçe Açıklama | Nerede Geçer |
|----------|---------|-----------------|--------------|
| `a` | agreeableness | Big Five: uyumluluk skoru [0,1] | `psychology.py`, serializer yükü |
| `c` | conscientiousness | Big Five: sorumluluk skoru [0,1] | `psychology.py`, serializer yükü |
| `d` | delta / dict | Bağlama göre: fark değeri ya da sözlük nesnesi | `vitals.py`, `memory.py` |
| `dt` | delta time | Son tick'ten bu yana geçen simülasyon süresi (saniye) | `vitals.py`, `psychology.py`, `sim_clock.py` |
| `e` | extraversion | Big Five: dışadönüklük skoru [0,1] | `psychology.py`, serializer yükü |
| `en` | energy (normalized) | Normalleştirilmiş enerji [0,1] (`vitals.energy / 100`) | `vitals.py`, serializer yükü |
| `ew` | emotional weight | Duygusal ağırlık [-1,1]; bellek kayıtlarının önem skoru | `memory.py`, serializer yükü |
| `h` | hunger | Açlık değeri (yükseldikçe tehlike artar) | `vitals.py` |
| `i`, `j` | loop index | Döngü sayacı | Genel |
| `k` | key | Sözlük anahtarı | Genel |
| `m` | memory / magnitude | Bellek nesnesi ya da vektör büyüklüğü | `memory.py`, `social.py` |
| `n` | neuroticism / amount | Big Five: nevrotiklik [0,1] ya da miktar (envanterde) | `psychology.py`, serializer yükü |
| `o` | openness | Big Five: açıklık skoru [0,1] | `psychology.py`, serializer yükü |
| `p` | psychology | NPC psikoloji nesnesi referansı | `npc.py` |
| `q` | queue | Kuyruk nesnesi | `llm_request_queue.py` |
| `t` | thirst | Susuzluk değeri | `vitals.py` |
| `v` | vitals | NPC yaşamsal göstergeler nesnesi referansı | `npc.py` |
| `x`, `z` | coordinates | Oyun dünyası konumu (2D: x yatay, z dikey) | `world_map.py`, serializer yükü |

### 1.2 Üç ve Daha Fazla Harfli Kısaltmalar

| Kısaltma | Açılımı | Türkçe Açıklama | Nerede Geçer |
|----------|---------|-----------------|--------------|
| `ang` | anger | Öfke duygu değeri [0,1] | `psychology.py`, serializer yükü |
| `cfg` | config / SimulationConfig | Simülasyon konfigürasyonu nesnesi | `simulation_manager.py`, `run_diagnostic.py` |
| `cot` | chain-of-thought | Reasoner modelinin ürettiği Türkçe düşünce zinciri | `bootstrap_cot.py`, `llm_backend.py` |
| `ctx` | ActionContext | Her tick'e özgü değişmez anlık görüntü; tüm aksiyonlara geçilir | `action_context.py`, `builtin.py` |
| `dp` | duty_pull | Görev çekimi [0,1]; NPC'nin sosyal yükümlülük hissi | `decision_factors.py` |
| `emo` | emotions | Duygular sözlüğü (`{hap, fear, ang}`) | `psychology.py`, serializer yükü |
| `evt` | event type | Olay türü string'i (percept/bellek kayıtlarında) | `memory.py`, `sim_logger.py` |
| `hap` | happiness | Mutluluk duygu değeri [0,1] | `psychology.py`, serializer yükü |
| `hun` | hunger | Açlık (serializer yükünde kullanılan kısa form) | `npc_serializer.py` |
| `inv` | inventory | Envanter nesnesi ya da serializer'daki envanter listesi | `inventory.py`, serializer yükü |
| `llm` | large language model | Büyük dil modeli | `llm_backend.py`, `llm_decision_system.py` |
| `mem` | memory | NPCMemory nesnesi referansı | `npc.py`, `memory.py` |
| `mgr` | manager | SimulationManager nesnesi referansı | `run_diagnostic.py`, `server.py` |
| `mod` | modifier | Skor çarpanı ya da düzenleyici | `builtin.py`, `decision_factors.py` |
| `npc` | non-player character | Oyuncu olmayan karakter (tüm sistemin ana varlığı) | Her yer |
| `occ` | occupation | Meslek (farmer, merchant, guard, healer, scholar) | `npc_factory.py`, serializer yükü |
| `pos` | position | 2D koordinat `(x, z)` tuple'ı | `spatial_grid.py`, serializer yükü |
| `pt` | perceived_threat | Algılanan tehdit skoru [0,1] | `decision_factors.py` |
| `rng` | random number generator | Deterministik rassal sayı üreteci (`SimRng`) | `sim_rng.py`, tüm rastgele işlemler |
| `sal` | salience | Dikkat ağırlığı [0,1]; bir percept'in ne kadar önemli olduğu | `perception_filter.py`, serializer yükü |
| `sim` | simulation | Simülasyon nesnesi ya da öneki | `simulation_manager.py`, `sim_*.py` dosyaları |
| `sp` | self_power | Öz güç skoru [0,1]; NPC'nin savaşa hazırlık düzeyi | `decision_factors.py` |
| `str` | stress | Stres değeri [0,1] (Python `str` türüyle karışmaz — bağlama bak) | `vitals.py`, serializer yükü |
| `thi` | thirst | Susuzluk (serializer yükünde kullanılan kısa form) | `npc_serializer.py` |
| `tid` | threat_id | Tehdit kaynağının NPC kimliği | `decision_factors.py` |

### 1.3 JSON Yük Anahtarları (NPCSerializer → Ollama)

Serializer, token sayısını azaltmak için tüm anahtarları kısaltır.

| Anahtar | Tam Form | Türkçe |
|---------|----------|--------|
| `act` | activity | Aktif eylem (schedule içinde) |
| `arch` | archetype | NPC kişilik arketipi (Brave, Fearful, …) |
| `b5` | Big Five | Beş faktör kişilik nesne anahtarı |
| `conf` | confidence | Bir inancın kesinlik derecesi [0,1] |
| `day` | day number | Simülasyon gün sayısı |
| `desc` | description | Metin açıklaması (percept veya bellek) |
| `hr` | hour | Simülasyon saati |
| `id` | npc_id | NPC benzersiz kimlik string'i |
| `sal` | salience | Dikkat ağırlığı |
| `sched` | schedule | Günlük program nesnesi |
| `subj` | subject | Bir inancın konusu (NPC id, bölge adı, …) |
| `tag` | object tag | Percept türü etiketi ("Threat", "Food", "NPC", …) |
| `val` | valence | Duygusal yük [-1,1] (inanç veya bellek için) |
| `wk_end` | work end hour | Mesai bitiş saati |
| `wk_start` | work start hour | Mesai başlangıç saati |

### 1.4 CSV Kolon Önekleri (SimLogger — 44 sütun)

| Önek | Türkçe Kategori | Örnek Sütunlar |
|------|-----------------|----------------|
| `action_*` | Aksiyon bilgisi | `action_selected`, `action_valid`, `action_target_id`, `action_dialogue` |
| `emotion_*` | Duygu değerleri | `emotion_happiness`, `emotion_fear`, `emotion_anger` |
| `inv_*` | Envanter miktarları | `inv_food`, `inv_water`, `inv_medicine`, `inv_gold`, `inv_grain`, `inv_tools` |
| `llm_*` | LLM metrikleri | `llm_called`, `llm_trigger`, `llm_latency_ms`, `llm_fallback` |
| `percept_*` | Algı bilgisi | `percept_count`, `top_percept_tag`, `top_percept_threat` |
| `pos_*` | Konum | `pos_x`, `pos_z` |
| `memory_*` | Bellek özeti | `memory_count`, `top_memory_desc` |

---

## 2. Mimari Kodlar

### 2.1 LLM Sertleştirme Mekanizmaları (H1–H6)

| Kod | Bileşen | Ne Yapar |
|-----|---------|----------|
| **H1** | `WorldRegistry` + `NPCSerializer` | Ham (x, z) koordinatlarını anlamlı bölge isimlerine (`MarketSquare`, `Tavern`, …) dönüştürür; LLM konumu anlayabilsin diye. |
| **H2** | `LLMDecisionSystem._check_interrupt()` | LLM'i yalnızca tehdit ≥ 0.8 veya HP düşüşü ≥ 15 olduğunda tetikler; gereksiz çağrıları önler. |
| **H3** | `LLMRequestQueue` | Öncelik tabanlı asenkron kuyruk (interrupt=0, normal=5, bg=10); Ollama çağrıları sıralı işlenir, VRAM dolmaz. Gelen INTERRUPT mevcut düşük öncelikli isteği iptal eder. |
| **H4** | `_guided_retry()` | Formatter geçersiz `action_id` döndürürse yalnızca Formatter'a tek düzeltici prompt gönderir (pahalı Reasoner tekrar çalıştırılmaz). |
| **H5** | `_enforce_trait_coherence()` | Çıkarım sonrası kural: Brave+düşük korku+yüksek tehdit → `attack`; Pacifist → hiçbir zaman `attack`; Coward+tehdit≥0.5 → `flee`; Greedy+altın+ticaret → `trade`; Devout+stres≥0.6 → `pray`. |
| **H6** | `DualLLMBackend` — CoT doğrulama kapısı | Reasoner çıktısının geçerliliğini denetler (boş değil, 50–600 karakter, JSON şeklinde değil) — Formatter'a geçmeden önce. |

### 2.2 Entegrasyon Noktaları (G Kodları)

| Kod | Ne Anlama Gelir |
|-----|-----------------|
| **G1** | `WalkToAction`: bellek tehdit sapması (`get_memory_threat_bias()`) bölge seçimini etkiler |
| **G2** | `AttackAction`: hedefin inanç valansı saldırı skorunu biçimlendirir |
| **G3** | `TradeAction`: hedefin inanç valansı ticaret kararını etkiler; başarılı ticaret inancı güçlendirir (B1) |
| **G4** | `SocializeAction.execute()`: LLM dialogue çıktısını dinleyicinin `NPCMemory`'sine yazar |
| **G5** | Dedikodu yayılımı: güven ≥ 0.3 ise inançlar zayıflatılmış (val×0.7, conf×0.6) şekilde aktarılır |
| **G6** | Her aksiyon: ilgili hedef aktifse `goal_bonus()` +0.25 ekler |
| **G9** | Reasoner → CoT → H6 kapısı → Formatter boru hattı |

### 2.3 İnanç / İtibar Entegrasyon Noktaları (B Kodları)

| Kod | Kural |
|-----|-------|
| **B1** | `TradeAction`: başarılı ticaret sonrası hedef hakkındaki inanç güçlendirilir |
| **B2** | `WorkAction`: ev bölgesi hakkında olumsuz inanç varsa çalışma skoru −0.25 alır |
| **B3** | `SocializeAction`: itibar +0.20 × (itibar − 0.5) etkisi; `TradeAction`: itibar < 0.3 ise −0.30 |
| **B4** | `AttackAction` / `SocializeAction`: düşman fraksiyon +0.30 / −0.20; müttefik ters yönde |

---

## 3. Teknik Terimler

### 3.1 AI / Makine Öğrenmesi Terimleri

| Terim | Türkçe Açıklama | İlgili Dosya |
|-------|-----------------|--------------|
| **LLM** (Large Language Model) | Büyük dil modeli; NPC kararları için Ollama üzerinden çalışan yerel model | `llm_backend.py` |
| **CoT** (Chain-of-Thought) | Düşünce zinciri; Reasoner'ın Türkçe 3-5 cümlelik iç muhakemesi | `bootstrap_cot.py`, `llm_backend.py` |
| **LoRA** (Low-Rank Adaptation) | Düşük ranklı uyarlama; modeli az parametreyle ince ayar yapma tekniği (Reasoner r=16, Formatter r=8) | `docs/llm_pipeline.md` |
| **Inference** | Çıkarım; modelin bir girdi alıp çıktı üretme adımı (token/saniye ile ölçülür) | `llm_backend.py` |
| **Backend** | Arka uç bağlantı katmanı; `OllamaBackend`, `MockBackend`, `DualLLMBackend` alternatifleri | `llm_backend.py` |
| **Reasoner** | Düşünen model (Hermes-3-Llama-3.2-3B + LoRA); NPC durumu alır, Türkçe CoT üretir | `llm_backend.py`, `docs/llm_pipeline.md` |
| **Formatter** | Biçimleyici model (Llama-3.2-1B-Instruct + LoRA); CoT alır, katı JSON `LLMResponse` üretir | `llm_backend.py` |
| **DualLLMBackend** | Çift model boru hattı: Reasoner → H6 doğrulama → Formatter | `llm_backend.py` |
| **Packing** | Eğitim tekniği: birden fazla örneği birleştirip tek dizi haline getirme; bu projede kapalı (`packing=False`) — EOS tokenı gizleme sorununu önler | `docs/llm_pipeline.md` |
| **Persona card** | Kimlik kartı; Reasoner'ın kullanıcı turuna eklenen 2-3 Türkçe cümlelik NPC kimlik ön metni | `persona_card.py` |
| **Bootstrap** | Önyükleme; Gemma 3 4B ile disk önbellekli CoT üretimi — eğitim verisi hazırlama aşaması | `bootstrap_cot.py` |
| **Response curve** | Yanıt eğrisi; normalleştirilmiş aksyon skorlarına uygulanan matematiksel dönüşüm (Linear, Quadratic, Sigmoid) | `utility_evaluator.py` |
| **System prompt** | Sistem mesajı; modelin davranışını tanımlayan sabit talimat metni (Reasoner ve Formatter için ayrı) | `llm_backend.py` |

### 3.2 Karar Sistemi Terimleri

| Terim | Türkçe Açıklama | İlgili Dosya |
|-------|-----------------|--------------|
| **Utility AI** | Fayda yapay zekası; tüm 12 aksiyonu matematiksel skorlarla kıyaslayan ve en yükseği seçen saf hesaplama katmanı | `decisions/`, `utility_evaluator.py` |
| **evaluate()** | Bir aksiyonun istenilebilirlik skorunu [0,1] döndüren yan etkisiz hesaplama metodu | `builtin.py` |
| **execute()** | Aksiyonu gerçekleştiren; NPC durumunu değiştiren, olay yayımlayan metod | `builtin.py` |
| **is_valid()** | Aksiyonun bu tick'te yapılabilir olup olmadığını kontrol eden yan etkisiz koşul metodu | `builtin.py` |
| **ActionContext** | Aksiyon bağlamı; her tick için oluşturulan değişmez anlık görüntü — percepts, vitals, hedefler, dünya referansları içerir | `action_context.py` |
| **ActionLibrary** | Aksiyon kitaplığı; `action_id` string → `IAction` nesnesi eşleme kaydı | `action_library.py` |
| **UtilityEvaluator** | Fayda değerlendirici; tüm geçerli aksiyonları puanlar, trait çarpanlarını uygular, en yükseği seçer | `utility_evaluator.py` |
| **Trait modifier** | Özellik çarpanı; kişilik özelliğine göre aksyon skorunu çarpan ağırlık (örn. Brave kaçmayı baskılar) | `utility_evaluator.py`, `builtin.py` |
| **Action lock** | Aksyon kilidi; minimum süre dolmadan başka aksiyona geçişi engeller; mantık salınımını önler | `action_lock.py` |
| **Interrupt predicate** | Kesinti koşulu; bir olayın aksyon kilidini kırıp kıramayacağını belirleyen kural | `builtin.py` |
| **Multi-factor decision model** | Çok faktörlü karar modeli; `self_power` vs `perceived_threat` ve `duty_pull` → 3 bölgeli aksiyon etiketi | `decision_factors.py` |
| **Utility fallback** | Fayda geri dönüşü; LLM yanıt beklerken Utility AI'ın devreye girmesi | `llm_decision_system.py` |

### 3.3 Oyun / Simülasyon Terimleri

| Terim | Türkçe Açıklama | İlgili Dosya |
|-------|-----------------|--------------|
| **NPC** (Non-Player Character) | Oyuncu olmayan karakter; 10 alt sistemi (vitals, psikoloji, bellek, inançlar, hedefler, özellikler, envanter, program, sosyal, algı) bünyesinde barındıran ana varlık | `npc.py` |
| **Tick** | Simülasyon kare (frame); tüm NPC'ler deterministik sırayla güncellenir | `simulation_manager.py` |
| **Vitals** | Yaşamsal göstergeler; HP, enerji, açlık, susuzluk, stres | `vitals.py` |
| **Percept** | Algı nesnesi; bir sensörün tespit ettiği tek bir varlık — tehdit seviyesi, tür etiketi, sona erme sayacı içerir | `perceived_object.py` |
| **Perception** | Algı sistemi; çok kanallı sensörler (Görsel, İşitsel, Sosyal) ile çevreden bilgi toplama | `perception_system.py` |
| **Salience** | Dikkat ağırlığı [0,1]; bir percept'in ne kadar önemli olduğu — stresli NPC'ler tehditleri önceliklendirir | `perception_filter.py` |
| **Stimulus** | Uyaran; yayımlanan olay (`StimulusType.VISUAL/AUDIO/SOCIAL/OLFACTORY`), kaynak ve yoğunluk içerir | `stimulus.py` |
| **Field-of-View** | Görüş alanı; görsel uyaranları yön konisine göre filtreler | `perception_filter.py` |
| **Archetype** | Arketip; önceden tanımlı kişilik profili (Brave, Cunning, Fearful, Honorable, Aggressive) | `npc_factory.py` |
| **Faction** | Hizip/grup; NPC'nin üyesi olduğu topluluk — diğer hiziplerle eğilim matrisi vardır | `faction_registry.py` |
| **Disposition** | Eğilim; iki hizip arasındaki güven/düşmanlık skoru [-1, +1]; çarpımsal azalır | `faction_registry.py` |
| **Trait** | Kişilik özelliği; adlandırılmış davranış belirleyici (Brave, Coward, Greedy, Devout, Pacifist, …) | `traits.py` |
| **Inventory** | Envanter; yuvaya dayalı eşya sistemi (food, water, medicine, gold, grain, tools, weapon); yığın üst sınırı 100 | `inventory.py` |
| **Schedule** | Program; mesleğe göre belirlenmiş günlük ritim (uyku/çalışma döngüleri) | `schedule.py` |
| **Circadian** | Sirkadiyen; gün/gece döngüsü tercihlerini tanımlayan meslek güdümlü ritim | `schedule.py` |
| **Goal** | Hedef; ihtiyaç tabanlı boru hattı çıktısı — türleri: Survive, FindFood, FindWater, Rest, Socialize, Work, Explore, Trade, Attack, Pray, Heal, GoHome | `goals.py` |
| **Belief** | İnanç; bir özne hakkında valans ve güven düzeyi içeren bilgi kaydı | `beliefs.py` |
| **Episodic memory** | Epizodik bellek; `MemoryEntry` nesnelerini tutan O(1) halka arabelleği (kapasite 50) | `memory.py` |
| **Reputation** | İtibar; NPC başına tek sayısal değer [0,1]; SocializeAction ve TradeAction tarafından kullanılır | `social.py` |
| **Social relations** | Sosyal ilişkiler; NPC çiftleri arası (güven, sempati, saygı) üçlüsü; LRU ile 200'de sınırlanmış | `social.py` |
| **Zone** | Bölge; anlamlı konum adı (MarketSquare, Tavern, Temple, …); H1 semantiğinin temeli | `world_map.py` |
| **Landmark** | Dönüm noktası; referans nokta (CityGates, CentralFountain, …); en yakını serializer'a eklenir | `world_map.py` |

### 3.4 Psikoloji Modeli Terimleri

| Terim | Türkçe Açıklama | İlgili Dosya |
|-------|-----------------|--------------|
| **Big Five** | Beş büyük kişilik faktörü (OCEAN modeli); her boyut [0,1] — duygu azalma hızlarını etkiler | `psychology.py` |
| **Mood** | Ruh hali; mutluluk/öfke/korku/nevrotiklik kombinasyonundan türetilen kategorik durum | `psychology.py` |
| **Cross-inhibition** | Çapraz baskılama; öfke ile mutluluk birbirini baskılar (0.5 çarpanla) — aynı anda iki yüksek duygu oluşmaz | `psychology.py` |
| **Emotional weight** | Duygusal ağırlık [-1,1]; bellek kaydının önem skoru — `get_most_salient()` en yüksek mutlak değeri döndürür | `memory.py` |
| **Memory decay** | Bellek solması; çarpımsal azalma (`weight *= 1 - rate`) — eski yoğun anılar göreceli sıralamayı korur | `memory.py` |
| **Stress spillover** | Stres taşması; `anger += stress × 0.02 × dt × neuroticism` — tek yönlü ilişki | `psychology.py`, `docs/psychology_model.md` |
| **Neuroticism factor** | Nevrotiklik çarpanı; korku toparlanmasını yavaşlatır, stres birikimini artırır, korku tepkisini yükseltir | `psychology.py` |
| **Agreeableness factor** | Uyumluluk çarpanı; öfke azalmasını hızlandırır, öfke süresi etkilerini azaltır | `psychology.py` |
| **Extraversion factor** | Dışadönüklük çarpanı; SocializeAction'dan elde edilen mutluluk kazancını ölçekler | `psychology.py` |

### 3.5 Veri Yapıları ve Performans Terimleri

| Terim | Türkçe Açıklama | İlgili Dosya |
|-------|-----------------|--------------|
| **Ring buffer** | Halka arabelleği; O(1) döngüsel dizi — `_head` işaretçisi ve modülo kapasite ile çalışır | `memory.py` |
| **LRU** (Least Recently Used) | En az son kullanılan; kapasite dolunca en eski/en az güvenilir kaydı tasfiye eden eviction politikası | `beliefs.py`, `social.py` |
| **Eviction** | Tasfiye; koleksiyon sınıra ulaşınca en düşük güven + en eski kaydın çıkarılması | `beliefs.py`, `social.py` |
| **Dictionary grid** | Sözlük ızgarası; koordinat (x, z) → hücre → NPC listesi eşlemesi; O(1) ekle/çıkar, O(k) yarıçap sorgusu | `spatial_grid.py` |
| **Spatial grid** | Uzamsal ızgara; `DictionaryGrid`'in genel adı; varsayılan hücre boyutu 50.0 birim | `spatial_grid.py` |
| **Priority queue** | Öncelik kuyruğu; min-heap yapısı (`heapq`) — en düşük öncelik sayısı en önce işlenir | `llm_request_queue.py` |
| **Preemption** | Öncelik kesintisi; gelen INTERRUPT, uçuştaki düşük öncelikli isteği `_cancelled` olarak işaretler | `llm_request_queue.py` |

### 3.6 Sayısal ve İstatistiksel Terimler

| Terim | Türkçe Açıklama | İlgili Dosya |
|-------|-----------------|--------------|
| **Decay** | Azalma/solma; çarpımsal küçülme (`değer *= 1 - oran`) — her tick'te uygulanan | `vitals.py`, `memory.py`, `psychology.py` |
| **Bias** | Sapma; aksyon skoruna eklenen düzenleyici terim (bellek tehdit sapması, bölge sapması, inanç skoru) | `action_context.py`, `builtin.py` |
| **Valence** | Valans; bir inancın ya da anının duygusal yükü [-1,1] — eksi düşman, artı müttefik | `beliefs.py`, `memory.py` |
| **Confidence** | Güven/kesinlik; bir inancın ne kadar doğru kabul edildiği [0,1]; yavaşça azalır, 0.05 altı budanır | `beliefs.py` |
| **Attenuation** | Zayıflama; dedikodu aktarımında inanç değerlerinin düşürülmesi (val×0.7, conf×0.6) | `social.py`, `docs/integration_map.md` |
| **Magnitude** | Büyüklük; `max(|güven|, |sempati|, |saygı|)` — eviction kurbanı belirleme ölçütü | `social.py` |
| **Urgency multiplier** | Aciliyet çarpanı; ihtiyaç kritik olduğunda aksyon skorunu yükselten çarpan (örn. açlık²×aciliyet) | `builtin.py` |
| **Efficiency factor** | Verimlilik çarpanı; enerjiye göre normalleştirilmiş çalışma verimi | `builtin.py` |
| **Prune threshold** | Budama eşiği; bu değerin altındaki güven/büyüklük kayıtları `decay_all()` sırasında silinir (varsayılan 0.05) | `beliefs.py`, `social.py` |

### 3.7 Mimari Bileşenler

| Terim | Türkçe Açıklama | İlgili Dosya |
|-------|-----------------|--------------|
| **SimulationManager** | Simülasyon yöneticisi; her tick'i yöneten üst düzey orkestratör | `simulation_manager.py` |
| **StimulusDispatcher** | Uyaran yayıcı; her tick başında bekleyen olayları tüm NPC'lere yayımlar | `stimulus_dispatcher.py` |
| **FactionRegistry** | Hizip kaydı; global eğilim matrisi; `tick_decay()` her frame çalışır; temizleme eşiği 0.01 | `faction_registry.py` |
| **PerceptionSystem** | Algı sistemi; NPC başına sensör orkestratörü; uyaranları menzil + önem filtresiyle geçirir | `perception_system.py` |
| **LLMDecisionSystem** | LLM karar sistemi; her tick'te çalışır; asenkron LLM + Utility AI yedeklemesi + 5 sertleştirme mekanizması | `llm_decision_system.py` |
| **DecisionSystem** | Saf Utility AI karar sistemi (LLM olmadan); aksyon kilit yönetimi | `decision_system.py` |
| **WorldRegistry** | Dünya kaydı; H1: AABB bölge arama — (x, z) → bölge adı + dönüm noktası | `world_registry.py` |
| **NPCFactory** | NPC fabrikası; 5 arketipsel NPC'yi önceden ayarlanmış Big Five, özellikler, envanter ve programlarla oluşturur | `npc_factory.py` |
| **SimRng** | Simülasyon RNG'si; tohumlanmış `random.Random` sarmalayıcısı — aynı tohum = özdeş tekrar | `sim_rng.py` |
| **SimLogger** | Simülasyon kaydedici; 44 sütunlu tick başı CSV kaydı; her 1M satırda `sim_full.NNNN.csv`'ye döner | `sim_logger.py` |
| **SimulationClock** | Simülasyon saati; simülasyon zamanını izler, azalma hesaplamaları için `delta_time` üretir | `sim_clock.py` |
| **Invariants** | Değişmezler; uzun çalışmalarda güvenlik ağı — vital aralığı, dict üst sınırları, envanter taşması denetler | `invariants.py` |
| **Tick flow** | Tick akışı; her tick'te çalışma sırası: StimulusDispatcher → FactionRegistry.tick_decay → NPC döngüsü → SimLogger | `simulation_manager.py`, `docs/architecture.md` |

### 3.8 Konfigürasyon ve Şema Terimleri

| Terim | Türkçe Açıklama | İlgili Dosya |
|-------|-----------------|--------------|
| **SimulationConfig** | Simülasyon yapılandırması; 20+ alan: tohum, tick_rate, gün uzunluğu, LLM ayarları | `sim_config.py` |
| **tick_rate** | Tick hızı; gerçek saniyedeki tick sayısı (varsayılan 10.0) | `sim_config.py` |
| **day_length_seconds** | Gün uzunluğu (saniye); bir simülasyon günü (varsayılan 1440.0) | `sim_config.py` |
| **death_by_neglect** | İhmalden ölüm; maksimum açlık/susuzlukta hasar etkinleştirici bayrak (1.0 hasar/dt) | `sim_config.py`, `vitals.py` |
| **stack_cap** | Yığın üst sınırı; envanterde her eşya türü için maksimum miktar (varsayılan 100) | `inventory.py` |
| **max_nodes** | Düğüm üst sınırı; `BeliefSystem` ve `NPCSocial.relations` için LRU kapasitesi (varsayılan 200) | `beliefs.py`, `social.py` |
| **LLMResponse** | LLM yanıtı; model çıktı nesnesi — alanlar: `action_id`, `target_id`, `dialogue`, `emotion`; `npc_id` çalışma zamanında enjekte edilir | `llm_backend.py` |
| **Minified JSON** | Küçültülmüş JSON; token sayısını azaltmak için kısa anahtarlar kullanan serializer yükü | `npc_serializer.py`, `docs/llm_data_spec.md` |
| **response_format** | Yanıt biçimi; Formatter için `"json"`, Reasoner CoT için `None` | `llm_backend.py` |

---

## 4. Hızlı Başvuru — En Sık Karşılaşılan Kısaltmalar

```
hp    → health points (sağlık puanı)
en    → energy normalized (normalleştirilmiş enerji)
hun   → hunger (açlık)
thi   → thirst (susuzluk)
str   → stress (stres)  ← Python str() ile karıştırma
hap   → happiness (mutluluk)
ang   → anger (öfke)
ew    → emotional weight (duygusal ağırlık)
sal   → salience (dikkat ağırlığı)
sp    → self_power (öz güç)
pt    → perceived_threat (algılanan tehdit)
dp    → duty_pull (görev çekimi)
cot   → chain-of-thought (düşünce zinciri)
llm   → large language model (büyük dil modeli)
ctx   → ActionContext (aksiyon bağlamı)
cfg   → SimulationConfig (yapılandırma)
rng   → random number generator (RNG)
mgr   → SimulationManager (yönetici)
npc   → non-player character (oyuncu olmayan karakter)
inv   → inventory (envanter)
occ   → occupation (meslek)
b5    → Big Five (beş faktör kişilik)
val   → valence (valans / duygusal yük)
conf  → confidence (güven/kesinlik)
```
