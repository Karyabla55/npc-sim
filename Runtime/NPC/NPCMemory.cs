using System;
using System.Collections.Generic;

namespace ForgeProject.Sim
{
    /// <summary>
    /// NPC's episodic memory — stores <see cref="MemoryEntry"/> references.
    ///
    /// Implemented as a circular ring buffer for O(1) insert and bounded memory.
    /// Iteration is most-recent-first.
    /// </summary>
    [Serializable]
    public class NPCMemory
    {
        // ─── Ring Buffer ──────────────────────────────────────────────────────────
        private readonly MemoryEntry[] _ring;
        private int  _head;   // points to the slot NEXT entry will be written to
        private int  _count;  // entries in ring (≤ Capacity)

        /// <summary>Maximum number of memories retained simultaneously.</summary>
        public int Capacity { get; }

        /// <summary>Current number of stored memories.</summary>
        public int Count => _count;

        // ─── Constructor ──────────────────────────────────────────────────────────
        public NPCMemory(int capacity = 50)
        {
            Capacity = Math.Max(1, capacity);
            _ring    = new MemoryEntry[Capacity];
        }

        // ─── Write ────────────────────────────────────────────────────────────────

        /// <summary>
        /// Records an event. O(1). Overwrites oldest entry when ring is full.
        /// </summary>
        public void Remember(SimEvent simEvent, float emotionalWeight, float currentTime)
        {
            if (simEvent == null) return;
            _ring[_head] = new MemoryEntry(simEvent, emotionalWeight, currentTime);
            _head        = (_head + 1) % Capacity;
            if (_count < Capacity) _count++;
        }

        // ─── Query ────────────────────────────────────────────────────────────────

        /// <summary>
        /// Iterates memories in most-recent-first order, passing each to <paramref name="visitor"/>.
        /// </summary>
        public void ForEachRecent(Action<MemoryEntry> visitor)
        {
            for (int i = 0; i < _count; i++)
            {
                int idx = (_head - 1 - i + Capacity) % Capacity;
                visitor(_ring[idx]);
            }
        }

        /// <summary>Returns entries matching <paramref name="eventType"/>.</summary>
        public List<MemoryEntry> GetByEventType(string eventType)
        {
            var result = new List<MemoryEntry>();
            ForEachRecent(e => { if (e.Event.EventType == eventType) result.Add(e); });
            return result;
        }

        /// <summary>Returns entries related to a specific NPC id.</summary>
        public List<MemoryEntry> GetRelatedTo(string npcId)
        {
            var result = new List<MemoryEntry>();
            ForEachRecent(e =>
            {
                if (e.Event.InitiatorId == npcId || e.Event.TargetId == npcId)
                    result.Add(e);
            });
            return result;
        }

        /// <summary>Returns entries recorded within the last <paramref name="windowSeconds"/> sim-seconds.</summary>
        public List<MemoryEntry> GetRecent(float currentTime, float windowSeconds)
        {
            var result = new List<MemoryEntry>();
            ForEachRecent(e =>
            {
                if (currentTime - e.RecordedAt <= windowSeconds) result.Add(e);
            });
            return result;
        }

        /// <summary>Returns the single most emotionally significant memory, or null.</summary>
        public MemoryEntry GetMostSalient()
        {
            MemoryEntry best = null;
            float       peak = 0f;
            ForEachRecent(e =>
            {
                float abs = MathF.Abs(e.EmotionalWeight);
                if (abs > peak) { peak = abs; best = e; }
            });
            return best;
        }

        // ─── Decay ────────────────────────────────────────────────────────────────

        /// <summary>Decays all emotional weights — simulates forgetting.</summary>
        public void DecayAll(float decayRate = 0.005f)
        {
            for (int i = 0; i < _count; i++)
                _ring[i]?.Decay(decayRate);
        }

        // ─── Read-only snapshot ───────────────────────────────────────────────────

        /// <summary>Copies current entries into a new list (most-recent first). Allocates — use sparingly.</summary>
        public List<MemoryEntry> ToList()
        {
            var result = new List<MemoryEntry>(_count);
            ForEachRecent(result.Add);
            return result;
        }

        public override string ToString() => $"[Memory] {_count}/{Capacity} entries";
    }

    // ─── Supporting type ──────────────────────────────────────────────────────────

    /// <summary>A single episodic memory entry.</summary>
    [Serializable]
    public class MemoryEntry
    {
        public SimEvent Event           { get; private set; }
        public float    EmotionalWeight { get; private set; }
        public float    RecordedAt      { get; private set; }

        public MemoryEntry(SimEvent simEvent, float emotionalWeight, float recordedAt)
        {
            Event           = simEvent;
            EmotionalWeight = Math.Clamp(emotionalWeight, -1f, 1f);
            RecordedAt      = recordedAt;
        }

        public void Decay(float rate) =>
            EmotionalWeight = Math.Sign(EmotionalWeight)
                              * Math.Clamp(MathF.Abs(EmotionalWeight) - rate, 0f, 1f);

        public override string ToString() =>
            $"[Mem] {Event.EventType} EW:{EmotionalWeight:+0.00;-0.00} @t={RecordedAt:F1}";
    }
}
