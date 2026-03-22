using System;
using System.Collections.Generic;

namespace ForgeProject.Sim
{
    /// <summary>
    /// NPC'nin belirli bir olgu veya varlık hakkındaki tek bir inancını temsil eder.
    /// İnanç bir <see cref="SimEvent"/> ile güçlendirilebilir veya zayıflatılabilir.
    /// </summary>
    [Serializable]
    public class BeliefNode
    {
        // ─── Kimlik ───────────────────────────────────────────────────────────────
        /// <summary>İnancın konusu (ör. "Player_Is_Hostile", "World_Is_Safe").</summary>
        public string Subject { get; private set; }

        // ─── Değerler ─────────────────────────────────────────────────────────────
        /// <summary>İnancın doğruluk gücü [0, 1]. 0 = kesinlikle yanlış, 1 = kesinlikle doğru.</summary>
        public float Confidence { get; private set; }

        /// <summary>Bu inancın NPC için taşıdığı duygusal değer [-1, 1].</summary>
        public float Valence { get; private set; }

        // ─── Geçmiş ───────────────────────────────────────────────────────────────
        /// <summary>Bu inancı besleyen olayların listesi.</summary>
        public IReadOnlyList<SimEvent> SupportingEvents => _supportingEvents;
        private readonly List<SimEvent> _supportingEvents = new();

        /// <summary>İnancın son güncellendiği simülasyon zamanı.</summary>
        public float LastUpdated { get; private set; }

        // ─── Oluşturucu ───────────────────────────────────────────────────────────
        public BeliefNode(string subject, float initialConfidence = 0.5f, float initialValence = 0f)
        {
            Subject    = subject;
            Confidence = Math.Clamp(initialConfidence, 0f, 1f);
            Valence    = Math.Clamp(initialValence, -1f, 1f);
        }

        // ─── Güncelleme ───────────────────────────────────────────────────────────
        /// <summary>
        /// Bir <see cref="SimEvent"/> ile inancı günceller.
        /// Confidence ve Valence, olayın Impact değeriyle ağırlıklı olarak hareket eder.
        /// </summary>
        /// <param name="simEvent">Tetikleyici olay.</param>
        /// <param name="currentTime">Güncel simülasyon zamanı.</param>
        /// <param name="learningRate">Güncelleme hızı [0, 1].</param>
        public void Reinforce(SimEvent simEvent, float currentTime, float learningRate = 0.1f)
        {
            if (simEvent == null) return;

            float delta = simEvent.Impact * learningRate;
            Confidence   = Math.Clamp(Confidence + Math.Abs(delta), 0f, 1f);
            Valence      = Math.Clamp(Valence + delta, -1f, 1f);
            LastUpdated  = currentTime;
            _supportingEvents.Add(simEvent);
        }

        /// <summary>Zamanla inancın güvenini azaltır (bellekten silinme simülasyonu).</summary>
        /// <param name="decayRate">Her çağrıda azalma miktarı [0, 1].</param>
        public void Decay(float decayRate = 0.01f)
        {
            Confidence = Math.Clamp(Confidence - decayRate, 0f, 1f);
        }

        public override string ToString() =>
            $"[Belief] {Subject} | Confidence: {Confidence:P0} | Valence: {Valence:+0.00;-0.00}";
    }
}
