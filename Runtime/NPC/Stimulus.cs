using System;

namespace ForgeProject.Sim
{
    /// <summary>Types of sensory stimuli emitted into the world.</summary>
    public enum StimulusType
    {
        Visual,
        Audio,
        Social,
        Olfactory
    }

    /// <summary>
    /// A raw world signal emitted by any entity (NPC, object, event).
    /// The <see cref="StimulusDispatcher"/> routes stimuli to nearby NPCs;
    /// each NPC's <see cref="PerceptionSystem"/> then filters them.
    /// </summary>
    [Serializable]
    public sealed class Stimulus
    {
        // ─── Identity ─────────────────────────────────────────────────────────────
        public string       SourceId       { get; }
        public StimulusType Type           { get; }

        // ─── Spatial ──────────────────────────────────────────────────────────────
        public SimVector3   SourcePosition { get; }

        // ─── Signal ───────────────────────────────────────────────────────────────
        /// <summary>Base intensity [0, 1]. Attenuated with distance by the dispatcher.</summary>
        public float        Intensity      { get; }

        /// <summary>
        /// Semantic tag that percept filters match against.
        /// Examples: "Threat", "Food", "Ally", "Noise", "Fire".
        /// </summary>
        public string       Tag            { get; }

        /// <summary>Simulation timestamp when this stimulus was emitted.</summary>
        public float        Timestamp      { get; }

        /// <summary>Optional arbitrary payload (ItemRef, NpcRef, SimEvent…).</summary>
        public object       Payload        { get; }

        // ─── Constructor ──────────────────────────────────────────────────────────

        public Stimulus(
            StimulusType type,
            string       sourceId,
            SimVector3   sourcePosition,
            float        intensity,
            float        timestamp,
            string       tag     = "",
            object       payload = null)
        {
            Type           = type;
            SourceId       = sourceId       ?? string.Empty;
            SourcePosition = sourcePosition;
            Intensity      = Math.Clamp(intensity, 0f, 1f);
            Timestamp      = timestamp;
            Tag            = tag            ?? string.Empty;
            Payload        = payload;
        }

        public override string ToString() =>
            $"[Stimulus] {Type} '{Tag}' from {SourceId} @ {SourcePosition} I={Intensity:F2} t={Timestamp:F1}";
    }
}
