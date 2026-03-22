using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Flat configuration data for a simulation run.
    /// Plain C# class — no Unity dependency. Can be serialized to JSON for persistence.
    /// </summary>
    [Serializable]
    public sealed class SimulationConfig
    {
        // ─── Identity ─────────────────────────────────────────────────────────────

        /// <summary>Seed for <see cref="SimRng"/>. Same seed + same config → identical run.</summary>
        public int   Seed                    { get; set; } = 42;

        // ─── Timing ───────────────────────────────────────────────────────────────

        /// <summary>How many simulation ticks per real second.</summary>
        public float TickRate                { get; set; } = 10f;

        /// <summary>Sim-seconds in one in-game day (default: 1440 = 24 min real-time at scale 1).</summary>
        public float DayLengthSeconds        { get; set; } = 1440f;

        /// <summary>Initial time scale. 1 = realtime, 60 = 1 min → 1 sec.</summary>
        public float InitialTimeScale        { get; set; } = 1f;

        // ─── World ────────────────────────────────────────────────────────────────

        /// <summary>Soft cap on active NPCs. Factory will not exceed this.</summary>
        public int   MaxNPCCount             { get; set; } = 500;

        /// <summary>Width/depth of the spatial grid cell (world units).</summary>
        public float SpatialGridCellSize     { get; set; } = 50f;

        // ─── Physiological decay rates (per sim-second) ────────────────────────── 

        /// <summary>Hunger increase per sim-second.</summary>
        public float HungerDecayRate         { get; set; } = 0.001f;

        /// <summary>Thirst increase per sim-second.</summary>
        public float ThirstDecayRate         { get; set; } = 0.002f;

        /// <summary>Energy drain per sim-second when active.</summary>
        public float EnergyDecayRate         { get; set; } = 0.5f;

        // ─── Psychological decay rates (per sim-second) ────────────────────────── 

        /// <summary>Fear reduction per sim-second (natural calming).</summary>
        public float FearDecayRate           { get; set; } = 0.0005f;

        /// <summary>Happiness drift toward neutral per sim-second.</summary>
        public float HappinessDecayRate      { get; set; } = 0.0003f;

        /// <summary>Anger reduction per sim-second.</summary>
        public float AngerDecayRate          { get; set; } = 0.0004f;

        // ─── Memory / Belief ──────────────────────────────────────────────────────

        /// <summary>Emotional weight decay per tick per NPC.</summary>
        public float GlobalMemoryDecayRate   { get; set; } = 0.001f;

        /// <summary>Belief confidence decay per tick per NPC.</summary>
        public float GlobalBeliefDecayRate   { get; set; } = 0.005f;

        // ─── Social ───────────────────────────────────────────────────────────────

        /// <summary>Relation Trust/Affinity drift toward zero per sim-second.</summary>
        public float RelationDecayRate       { get; set; } = 0.00005f;

        // ─── Perception ───────────────────────────────────────────────────────────

        /// <summary>Sim-seconds before an unseen percept is pruned.</summary>
        public float PerceptTimeout          { get; set; } = 30f;

        // ─── Stimulus queue ───────────────────────────────────────────────────────

        /// <summary>Max stimuli queued per tick. Excess stimuli are dropped (oldest first).</summary>
        public int   StimulusQueueSize       { get; set; } = 1024;

        // ─── Civilisation / Lifecycle ─────────────────────────────────────────────

        /// <summary>NPC age at which natural death becomes possible.</summary>
        public int   OldAgeThreshold         { get; set; } = 75;

        /// <summary>If true, NPCs die when Hunger or Thirst reaches 1.0.</summary>
        public bool  DeathByNeglect          { get; set; } = true;

        /// <summary>Maximum items an NPC's inventory can hold.</summary>
        public int   MaxInventorySlots       { get; set; } = 10;

        /// <summary>Radius for idle movement when no urgent goal exists.</summary>
        public float WanderRadius            { get; set; } = 30f;

        public override string ToString() =>
            $"[SimConfig] Seed:{Seed} TickRate:{TickRate} Day:{DayLengthSeconds}s MaxNPC:{MaxNPCCount}";
    }
}
