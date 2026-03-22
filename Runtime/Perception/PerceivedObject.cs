using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Represents a single entity that the NPC is currently aware of.
    /// Created by <see cref="PerceptionSystem"/> after a <see cref="Stimulus"/>
    /// passes <see cref="SensorRange"/> and <see cref="PerceptionFilter"/>.
    /// </summary>
    [Serializable]
    public sealed class PerceivedObject
    {
        // ─── Identity ─────────────────────────────────────────────────────────────

        /// <summary>ID of the perceived entity (NPC, item, location…).</summary>
        public string     ObjectId              { get; }

        /// <summary>Category label: "NPC", "Item", "Location", "Hazard", "Ally"…</summary>
        public string     ObjectType            { get; }

        // ─── Spatial ──────────────────────────────────────────────────────────────

        /// <summary>Last known world position of this entity.</summary>
        public SimVector3 LastKnownPosition     { get; private set; }

        // ─── State ────────────────────────────────────────────────────────────────

        /// <summary>Simulation time when this percept was last updated.</summary>
        public float      LastSeenTime          { get; private set; }

        /// <summary>
        /// Threat level from the originating stimulus [0, 1].
        /// 0 = safe, 1 = maximum threat.
        /// </summary>
        public float      ThreatLevel           { get; private set; }

        /// <summary>
        /// Salience score as returned by <see cref="PerceptionFilter"/> [0, 1].
        /// Higher = more attention-worthy.
        /// </summary>
        public float      Salience              { get; private set; }

        /// <summary>Whether the entity was visible on the most recent tick.</summary>
        public bool       IsCurrentlyVisible    { get; private set; }

        /// <summary>The semantic tag of the originating stimulus (e.g. "Threat", "Food").</summary>
        public string     Tag                   { get; private set; }

        // ─── Constructor ──────────────────────────────────────────────────────────

        public PerceivedObject(
            string     objectId,
            string     objectType,
            SimVector3 position,
            float      seenAt,
            float      threatLevel,
            float      salience,
            string     tag = "")
        {
            ObjectId           = objectId   ?? string.Empty;
            ObjectType         = objectType ?? "Unknown";
            LastKnownPosition  = position;
            LastSeenTime       = seenAt;
            ThreatLevel        = Math.Clamp(threatLevel, 0f, 1f);
            Salience           = Math.Clamp(salience, 0f, 1f);
            IsCurrentlyVisible = true;
            Tag                = tag        ?? string.Empty;
        }

        // ─── Updates ──────────────────────────────────────────────────────────────

        /// <summary>
        /// Refreshes this percept with fresh stimulus data.
        /// Called when the same source emits another stimulus this tick.
        /// </summary>
        public void Refresh(SimVector3 newPosition, float seenAt, float newThreatLevel, float newSalience)
        {
            LastKnownPosition  = newPosition;
            LastSeenTime       = seenAt;
            ThreatLevel        = Math.Clamp(newThreatLevel, 0f, 1f);
            Salience           = Math.Clamp(newSalience,    0f, 1f);
            IsCurrentlyVisible = true;
        }

        /// <summary>Marks the percept as no longer currently visible.</summary>
        public void MarkNotVisible() => IsCurrentlyVisible = false;

        // ─── Expiry ───────────────────────────────────────────────────────────────

        /// <summary>
        /// Returns true when this percept is stale and should be pruned.
        /// </summary>
        /// <param name="currentTime">Current simulation time.</param>
        /// <param name="timeout">How many sim-seconds before the percept expires.</param>
        public bool IsExpired(float currentTime, float timeout)
            => currentTime - LastSeenTime > timeout;

        public override string ToString() =>
            $"[Percept] {ObjectType}:{ObjectId} '{Tag}' Threat:{ThreatLevel:F2} Sal:{Salience:F2} " +
            $"@ {LastKnownPosition} t={LastSeenTime:F1} vis={IsCurrentlyVisible}";
    }
}
