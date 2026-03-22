namespace ForgeProject.Sim
{
    /// <summary>
    /// Factory for per-archetype <see cref="SensorRange"/> profiles.
    /// Used by <see cref="SimulationManager.AddNPC"/> (D7 fix) to give
    /// each NPC type realistic sensory capabilities.
    /// </summary>
    public static class SensorRangePresets
    {
        /// <summary>
        /// Returns a SensorRange tuned for the given personality archetype string.
        /// Matches the values set by <see cref="NPCFactory"/> archetypes.
        /// </summary>
        public static SensorRange ForArchetype(string archetype) => archetype?.ToLowerInvariant() switch
        {
            // Guards are highly alert: wide visual, strong audio, narrow FOV for patrol focus
            "guardian" => new SensorRange(visualRadius: 35f, audioRadius: 45f, socialRadius: 15f, fieldOfViewDeg: 160f),
            "guard"    => new SensorRange(visualRadius: 35f, audioRadius: 45f, socialRadius: 15f, fieldOfViewDeg: 160f),

            // Merchants depend on social cues, average vision
            "merchant" => new SensorRange(visualRadius: 22f, audioRadius: 30f, socialRadius: 30f, fieldOfViewDeg: 180f),

            // Scholars observe broadly but don't react as fast
            "scholar"  => new SensorRange(visualRadius: 18f, audioRadius: 25f, socialRadius: 20f, fieldOfViewDeg: 180f),

            // Farmers work land: low visual range, good audio (hear animals/weather)
            "farmer"   => new SensorRange(visualRadius: 20f, audioRadius: 35f, socialRadius: 15f, fieldOfViewDeg: 140f),

            // Priests: high social sensing (community bonds), moderate vision
            "priest"   => new SensorRange(visualRadius: 18f, audioRadius: 25f, socialRadius: 40f, fieldOfViewDeg: 180f),

            // Civilians — balanced defaults
            _          => new SensorRange(visualRadius: 20f, audioRadius: 30f, socialRadius: 15f, fieldOfViewDeg: 180f)
        };

        /// <summary>Returns a wide-range "omniscient" profile for testing / spectator cameras.</summary>
        public static SensorRange Omniscient => new SensorRange(500f, 500f, 500f, 360f);
    }
}
