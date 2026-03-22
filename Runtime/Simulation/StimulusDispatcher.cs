using System;
using System.Collections.Generic;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Routes stimuli to NPCs in range without requiring each NPC to poll the world.
    /// Push-based: called once per stimulus by <see cref="SimulationManager"/>,
    /// which then buffers received stimuli per NPC for that tick.
    ///
    /// Relies on <see cref="ISimWorld.GetNPCsInRadius"/> backed by <see cref="ISpatialGrid"/>
    /// — no O(N²) scanning.
    /// </summary>
    public sealed class StimulusDispatcher
    {
        // Each NPC accumulates stimuli here until PerceptionSystem.Tick is called.
        // Key = NpcId.
        private readonly Dictionary<string, List<Stimulus>> _npcQueues = new();

        // Re-usable empty list to avoid allocations on drain misses
        private static readonly IReadOnlyList<Stimulus> _empty = Array.Empty<Stimulus>();

        // ─── Dispatch ─────────────────────────────────────────────────────────────

        /// <summary>
        /// Finds all NPCs within the stimulus range and queues the stimulus for them.
        /// Intensity is attenuated by distance² so nearby NPCs feel it more strongly.
        /// </summary>
        public void Dispatch(Stimulus stimulus, ISimWorld world, float maxRadius)
        {
            if (stimulus == null || world == null) return;

            var nearby = world.GetNPCsInRadius(stimulus.SourcePosition, maxRadius);
            foreach (var npc in nearby)
            {
                if (!npc.IsActive) continue;

                // Intensity falls off with distance² for a physically plausible model
                float sqrDist    = SimVector3.SqrDistance(stimulus.SourcePosition, npc.Position);
                float attenuated = stimulus.Intensity / (1f + sqrDist * 0.01f);
                attenuated = Math.Clamp(attenuated, 0f, 1f);

                var attStimulus = new Stimulus(
                    stimulus.Type, stimulus.SourceId, stimulus.SourcePosition,
                    attenuated, stimulus.Timestamp, stimulus.Tag, stimulus.Payload);

                Enqueue(npc.Identity.NpcId, attStimulus);
            }
        }

        // ─── Per-NPC stimulus collection ──────────────────────────────────────────

        private void Enqueue(string npcId, Stimulus s)
        {
            if (!_npcQueues.TryGetValue(npcId, out var queue))
                _npcQueues[npcId] = queue = new List<Stimulus>();
            queue.Add(s);
        }

        /// <summary>
        /// Returns the buffered stimuli for a specific NPC and clears its queue.
        /// Returns the existing List directly (no allocation) — callers must NOT modify it.
        /// Called once per NPC per tick by <see cref="SimulationManager"/>.
        /// </summary>
        public IReadOnlyList<Stimulus> DrainFor(string npcId)
        {
            if (!_npcQueues.TryGetValue(npcId, out var queue) || queue.Count == 0)
                return _empty;

            // Swap to a new list and return the filled one — avoids ToArray() copy
            var result = queue;
            _npcQueues[npcId] = new List<Stimulus>(result.Capacity);
            return result;
        }

        /// <summary>Clears all queued stimuli (e.g. on pause/reset).</summary>
        public void ClearAll() => _npcQueues.Clear();

        public override string ToString() =>
            $"[StimulusDispatcher] {_npcQueues.Count} active NPC queue(s)";
    }
}
