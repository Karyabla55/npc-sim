using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Models the social relationship between two NPCs across three dimensions:
    /// Trust, Affinity, and Respect. Automatically re-classifies its type after
    /// each interaction. Decays toward neutral over time if NPCs don't interact.
    /// </summary>
    [Serializable]
    public class Relation
    {
        // ─── Identity ─────────────────────────────────────────────────────────────
        public string OwnerId  { get; private set; }
        public string TargetId { get; private set; }

        // ─── Dimensions ───────────────────────────────────────────────────────────
        /// <summary>Trust level [-1, 1]. -1 = full distrust, 1 = full trust.</summary>
        public float Trust    { get; private set; }

        /// <summary>Affinity [-1, 1]. -1 = animosity, 1 = deep friendship.</summary>
        public float Affinity { get; private set; }

        /// <summary>Respect [0, 1]. 0 = contempt, 1 = high regard.</summary>
        public float Respect  { get; private set; }

        /// <summary>Semantic label derived from Trust+Affinity thresholds.</summary>
        public string RelationType         { get; private set; }

        /// <summary>Whether this is a family/kinship bond (resists decay).</summary>
        public bool   IsFamily            { get; private set; }

        /// <summary>Timestamp of the most recent interaction.</summary>
        public float  LastInteractionTime { get; private set; }

        // ─── Constructor ──────────────────────────────────────────────────────────
        public Relation(string ownerId, string targetId,
            float initialTrust = 0f, float initialAffinity = 0f, float initialRespect = 0.5f,
            string relationType = "Neutral", bool isFamily = false)
        {
            OwnerId      = ownerId;
            TargetId     = targetId;
            Trust        = Math.Clamp(initialTrust,    -1f, 1f);
            Affinity     = Math.Clamp(initialAffinity, -1f, 1f);
            Respect      = Math.Clamp(initialRespect,   0f, 1f);
            RelationType = relationType;
            IsFamily     = isFamily;
        }

        // ─── Interaction update ───────────────────────────────────────────────────

        /// <summary>Applies the result of a social interaction.</summary>
        public void ApplyInteraction(float trustDelta, float affinityDelta, float respectDelta, float currentTime)
        {
            Trust    = Math.Clamp(Trust    + trustDelta,    -1f, 1f);
            Affinity = Math.Clamp(Affinity + affinityDelta, -1f, 1f);
            Respect  = Math.Clamp(Respect  + respectDelta,   0f, 1f);
            LastInteractionTime = currentTime;
            UpdateRelationType();
        }

        // ─── Time decay (D4 fix) ──────────────────────────────────────────────────

        /// <summary>
        /// Drifts Trust and Affinity toward zero over time (friendships and enmities fade).
        /// Family bonds decay at 10% of the normal rate — kinship persists.
        /// </summary>
        /// <param name="deltaTime">Elapsed sim-time since last call.</param>
        /// <param name="decayRate">Base drift rate per sim-second.</param>
        public void DecayOverTime(float deltaTime, float decayRate = 0.00005f)
        {
            float rate = IsFamily ? decayRate * 0.1f : decayRate;
            float dt   = deltaTime * rate;

            // Trust drifts toward 0
            Trust    = Trust    > 0f ? Math.Max(0f, Trust    - dt) : Math.Min(0f, Trust    + dt);
            // Affinity drifts toward 0
            Affinity = Affinity > 0f ? Math.Max(0f, Affinity - dt) : Math.Min(0f, Affinity + dt);
            // Respect drifts toward neutral (0.3)
            const float neutralRespect = 0.3f;
            Respect  = Respect > neutralRespect
                ? Math.Max(neutralRespect, Respect - dt * 0.5f)
                : Math.Min(neutralRespect, Respect + dt * 0.5f);

            UpdateRelationType();
        }

        // ─── Helper ───────────────────────────────────────────────────────────────

        private void UpdateRelationType()
        {
            if (IsFamily && Trust >= 0f) { RelationType = "Family"; return; }
            RelationType = (Trust, Affinity) switch
            {
                (>= 0.6f, >= 0.6f)   => "Friend",
                (>= 0.3f, >= 0.3f)   => "Acquaintance",
                (<= -0.6f, <= -0.6f) => "Enemy",
                (<= -0.3f, _)        => "Rival",
                _                    => "Neutral"
            };
        }

        public override string ToString() =>
            $"[Relation] {OwnerId} → {TargetId} | {RelationType} | T:{Trust:+0.00;-0.00} A:{Affinity:+0.00;-0.00} R:{Respect:P0}";
    }
}
