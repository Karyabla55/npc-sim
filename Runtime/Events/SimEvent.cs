using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Represents a meaningful occurrence in the simulation world.
    /// NPCs can witness events, which update their memory and belief systems.
    ///
    /// IDs are deterministic when a <see cref="SimRng"/> is supplied;
    /// otherwise they fall back to an atomic counter (non-deterministic, only
    /// used for editor tools and unit-test convenience outside the sim loop).
    /// </summary>
    [Serializable]
    public class SimEvent
    {
        // ─── Non-deterministic fallback counter (used ONLY when rng == null) ──────
        // Placed as a proper static field — not inside the constructor.
        private static int _globalCounter;

        // ─── Identity ─────────────────────────────────────────────────────────────

        /// <summary>Unique event identifier (deterministic when rng is provided).</summary>
        public string     EventId       { get; private set; }

        /// <summary>
        /// Semantic category of the event, e.g. "Combat", "Trade", "Speech", "Eat", "Flee",
        /// "Gather", "Work", "Pray", "Heal".
        /// </summary>
        public string     EventType     { get; private set; }

        // ─── Time and Position ────────────────────────────────────────────────────

        /// <summary>Simulation timestamp when this event occurred.</summary>
        public float      Timestamp     { get; private set; }

        /// <summary>World position where the event occurred.</summary>
        public SimVector3 WorldPosition { get; private set; }

        // ─── Content ──────────────────────────────────────────────────────────────

        /// <summary>ID of the entity that triggered the event (NPC or object).</summary>
        public string     InitiatorId   { get; private set; }

        /// <summary>ID of the target entity (null if no specific target).</summary>
        public string     TargetId      { get; private set; }

        /// <summary>Short human-readable description / message.</summary>
        public string     Description   { get; private set; }

        /// <summary>Impact magnitude [-1, 1]. Negative = harmful, positive = beneficial.</summary>
        public float      Impact        { get; private set; }

        // ─── Optional metadata ────────────────────────────────────────────────────
        /// <summary>Arbitrary tag for filtering (e.g. "combat", "social", "resource").</summary>
        public string     Category      { get; private set; }

        // ─── Constructor ──────────────────────────────────────────────────────────

        /// <summary>Creates a new SimEvent.</summary>
        /// <param name="eventType">Semantic category label.</param>
        /// <param name="initiatorId">Source entity ID.</param>
        /// <param name="targetId">Target entity ID (or null).</param>
        /// <param name="description">Readable description.</param>
        /// <param name="impact">Effect magnitude [-1, 1].</param>
        /// <param name="timestamp">Simulation time of occurrence.</param>
        /// <param name="position">World position (defaults to Zero).</param>
        /// <param name="rng">Optional deterministic RNG for reproducible event IDs.</param>
        /// <param name="category">Optional broad category tag for filtering.</param>
        public SimEvent(
            string     eventType,
            string     initiatorId,
            string     targetId,
            string     description,
            float      impact,
            float      timestamp,
            SimVector3 position = default,
            SimRng     rng      = null,
            string     category = "")
        {
            EventId       = rng != null
                                ? rng.NextId("ev")
                                : $"ev_{System.Threading.Interlocked.Increment(ref _globalCounter):x6}";
            EventType     = eventType    ?? string.Empty;
            InitiatorId   = initiatorId  ?? string.Empty;
            TargetId      = targetId     ?? string.Empty;
            Description   = description  ?? string.Empty;
            Impact        = Math.Clamp(impact, -1f, 1f);
            Timestamp     = timestamp;
            WorldPosition = position;
            Category      = category     ?? string.Empty;
        }

        public override string ToString() =>
            $"[SimEvent:{EventType}] {InitiatorId}→{TargetId} Impact:{Impact:+0.00;-0.00} @t={Timestamp:F1} pos={WorldPosition}";
    }
}
