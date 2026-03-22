using System;
using System.Collections.Generic;

namespace ForgeProject.Sim
{
    /// <summary>
    /// NPC'nin inanç sistemini merkezi olarak yönetir.
    /// Yeni olayları alarak uygun <see cref="BeliefNode"/> düğümlerini günceller.
    /// </summary>
    public class BeliefSystem
    {
        // ─── Veri ─────────────────────────────────────────────────────────────────
        private readonly Dictionary<string, BeliefNode> _nodes = new();

        public IReadOnlyDictionary<string, BeliefNode> Nodes => _nodes;

        // ─── İşlemler ─────────────────────────────────────────────────────────────
        /// <summary>
        /// Belirli bir konuya ait inancı döner; yoksa yeni oluşturur.
        /// </summary>
        public BeliefNode GetOrCreate(string subject)
        {
            if (!_nodes.TryGetValue(subject, out var node))
            {
                node = new BeliefNode(subject);
                _nodes[subject] = node;
            }
            return node;
        }

        /// <summary>
        /// Bir <see cref="SimEvent"/> ile ilgili tüm inançları günceller.
        /// </summary>
        /// <param name="simEvent">Tetikleyici olay.</param>
        /// <param name="subjectKeys">Güncellenmesi gereken inanç anahtarları.</param>
        /// <param name="currentTime">Güncel simülasyon zamanı.</param>
        /// <param name="learningRate">Öğrenme hızı.</param>
        public void ProcessEvent(SimEvent simEvent, IEnumerable<string> subjectKeys,
            float currentTime, float learningRate = 0.1f)
        {
            if (simEvent == null) return;
            foreach (var key in subjectKeys)
                GetOrCreate(key).Reinforce(simEvent, currentTime, learningRate);
        }

        /// <summary>Tüm inanç düğümlerini zamanla zayıflatır.</summary>
        public void DecayAll(float decayRate = 0.01f)
        {
            foreach (var node in _nodes.Values)
                node.Decay(decayRate);
        }

        public override string ToString() => $"[BeliefSystem] {_nodes.Count} belief node(s)";
    }
}
