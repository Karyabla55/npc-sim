using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Defines the sensing radii and field restrictions for an NPC.
    /// Used as a fast pre-filter before the <see cref="PerceptionFilter"/> runs.
    /// Pure math — no Unity dependencies.
    /// </summary>
    [Serializable]
    public sealed class SensorRange
    {
        // ─── Radii ────────────────────────────────────────────────────────────────

        /// <summary>Maximum visual detection distance (world units).</summary>
        public float VisualRadius    { get; set; }

        /// <summary>Maximum audio detection distance (world units).</summary>
        public float AudioRadius     { get; set; }

        /// <summary>Maximum social / olfactory detection distance (world units).</summary>
        public float SocialRadius    { get; set; }

        /// <summary>Field of view half-angle in degrees. 180 = omnidirectional.</summary>
        public float FieldOfViewDeg  { get; set; }

        // ─── Constructor ──────────────────────────────────────────────────────────

        public SensorRange(
            float visualRadius   = 20f,
            float audioRadius    = 30f,
            float socialRadius   = 15f,
            float fieldOfViewDeg = 180f)
        {
            VisualRadius   = MathF.Max(0f, visualRadius);
            AudioRadius    = MathF.Max(0f, audioRadius);
            SocialRadius   = MathF.Max(0f, socialRadius);
            FieldOfViewDeg = Math.Clamp(fieldOfViewDeg, 0f, 360f);
        }

        // ─── Core Query ───────────────────────────────────────────────────────────

        /// <summary>
        /// Returns true if the NPC at <paramref name="npcPosition"/> facing
        /// <paramref name="npcForward"/> can physically sense <paramref name="stimulus"/>.
        /// Does not apply attention or priority filters.
        /// </summary>
        public bool CanSense(Stimulus stimulus, SimVector3 npcPosition, SimVector3 npcForward)
        {
            float sqrDist = SimVector3.SqrDistance(npcPosition, stimulus.SourcePosition);
            float radius  = GetRadius(stimulus.Type);

            if (sqrDist > radius * radius) return false;

            // Omnidirectional or within FOV
            if (FieldOfViewDeg >= 180f || stimulus.Type == StimulusType.Audio)
                return true;

            // Directional FOV check (dot product, no trig needed)
            SimVector3 toSource = (stimulus.SourcePosition - npcPosition).Normalized();
            SimVector3 fwd      = npcForward.Magnitude < 1e-6f ? new SimVector3(0, 0, 1) : npcForward.Normalized();
            float cosHalfFov    = MathF.Cos(FieldOfViewDeg * MathF.PI / 360f);
            float dot           = fwd.X * toSource.X + fwd.Y * toSource.Y + fwd.Z * toSource.Z;

            return dot >= cosHalfFov;
        }

        /// <summary>
        /// Simplified CanSense when facing direction is irrelevant (omnidirectional).
        /// </summary>
        public bool CanSense(Stimulus stimulus, SimVector3 npcPosition)
            => CanSense(stimulus, npcPosition, SimVector3.Zero);

        // ─── Helpers ──────────────────────────────────────────────────────────────

        private float GetRadius(StimulusType type) => type switch
        {
            StimulusType.Visual    => VisualRadius,
            StimulusType.Audio     => AudioRadius,
            StimulusType.Social    => SocialRadius,
            StimulusType.Olfactory => SocialRadius,
            _                      => VisualRadius
        };

        public override string ToString() =>
            $"[SensorRange] Visual:{VisualRadius}u Audio:{AudioRadius}u FOV:{FieldOfViewDeg}°";
    }
}
