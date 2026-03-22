using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Fluent factory for creating pre-configured NPCs.
    /// Uses <see cref="SimRng"/> for all ID and stat generation — fully deterministic.
    /// </summary>
    public static class NPCFactory
    {
        // ─── Generic Builder ──────────────────────────────────────────────────────

        /// <summary>
        /// Creates a minimal NPC with the given name and age.
        /// All other stats use defaults.
        /// </summary>
        public static NPC Create(
            string   displayName,
            int      age,
            SimRng   rng,
            string   gender              = "Unknown",
            string   occupation          = "Civilian",
            string   faction             = "None",
            string   personalityArchetype = "Generic",
            float    maxHealth           = 100f,
            float    maxEnergy           = 100f,
            int      memoryCapacity      = 50)
        {
            var identity = new NPCIdentity(
                rng.NextId("npc"), displayName, age,
                gender, occupation, faction, personalityArchetype);

            return new NPC(
                identity,
                new NPCVitals(maxHealth, maxEnergy),
                new NPCPsychology(),
                new NPCSocial(),
                memoryCapacity);
        }

        // ─── Presets ──────────────────────────────────────────────────────────────

        /// <summary>
        /// A resilient, alert guard. High conscientiousness and low openness.
        /// Traits: Brave, Cautious.
        /// </summary>
        public static NPC CreateGuard(SimRng rng, string name = null, string faction = "City Watch")
        {
            name ??= "Guard";
            var identity = new NPCIdentity(
                rng.NextId("npc"), name, age: rng.NextInt(22, 45),
                "Male", "Guard", faction, "Guardian");

            var vitals = new NPCVitals(maxHealth: 120f, maxEnergy: 110f);

            var psych = new NPCPsychology(
                extraversion:      rng.NextFloat(0.3f, 0.5f),
                agreeableness:     rng.NextFloat(0.3f, 0.6f),
                conscientiousness: rng.NextFloat(0.7f, 1.0f),
                neuroticism:       rng.NextFloat(0.1f, 0.4f),
                openness:          rng.NextFloat(0.1f, 0.4f));

            var traits = new NPCTraits(NPCTraits.Brave, NPCTraits.Cautious);
            return new NPC(identity, vitals, psych, new NPCSocial(), memoryCapacity: 60, traits: traits);
        }

        /// <summary>
        /// An opportunistic merchant. High extraversion and agreeableness.
        /// Traits: Greedy, Curious.
        /// </summary>
        public static NPC CreateMerchant(SimRng rng, string name = null, string faction = "Merchant Guild")
        {
            name ??= "Merchant";
            var identity = new NPCIdentity(
                rng.NextId("npc"), name, age: rng.NextInt(25, 60),
                "Unknown", "Merchant", faction, "Merchant");

            var psych = new NPCPsychology(
                extraversion:      rng.NextFloat(0.6f, 0.9f),
                agreeableness:     rng.NextFloat(0.5f, 0.8f),
                conscientiousness: rng.NextFloat(0.4f, 0.7f),
                neuroticism:       rng.NextFloat(0.2f, 0.5f),
                openness:          rng.NextFloat(0.5f, 0.8f));

            var traits = new NPCTraits(NPCTraits.Greedy, NPCTraits.Curious);
            return new NPC(identity, new NPCVitals(), psych, new NPCSocial(), memoryCapacity: 70, traits: traits);
        }

        /// <summary>
        /// A cautious civilian. Balanced stats with higher neuroticism.
        /// Traits: Cautious.
        /// </summary>
        public static NPC CreateCivilian(SimRng rng, string name = null, string faction = "None")
        {
            name ??= "Civilian";
            var identity = new NPCIdentity(
                rng.NextId("npc"), name, age: rng.NextInt(18, 70),
                "Unknown", "Civilian", faction, "Generic");

            var psych = new NPCPsychology(
                extraversion:      rng.NextFloat(0.3f, 0.7f),
                agreeableness:     rng.NextFloat(0.4f, 0.8f),
                conscientiousness: rng.NextFloat(0.3f, 0.7f),
                neuroticism:       rng.NextFloat(0.3f, 0.7f),
                openness:          rng.NextFloat(0.3f, 0.6f));

            var traits = new NPCTraits(NPCTraits.Cautious);
            return new NPC(identity, new NPCVitals(), psych, new NPCSocial(), traits: traits);
        }

        /// <summary>
        /// A scholar: high openness and conscientiousness, lower physical stats.
        /// Traits: Curious, Pacifist.
        /// </summary>
        public static NPC CreateScholar(SimRng rng, string name = null, string faction = "Academy")
        {
            name ??= "Scholar";
            var identity = new NPCIdentity(
                rng.NextId("npc"), name, age: rng.NextInt(28, 65),
                "Unknown", "Scholar", faction, "Scholar");

            var psych = new NPCPsychology(
                extraversion:      rng.NextFloat(0.2f, 0.5f),
                agreeableness:     rng.NextFloat(0.5f, 0.8f),
                conscientiousness: rng.NextFloat(0.7f, 1.0f),
                neuroticism:       rng.NextFloat(0.2f, 0.5f),
                openness:          rng.NextFloat(0.8f, 1.0f));

            var vitals = new NPCVitals(maxHealth: 80f, maxEnergy: 90f);
            var traits = new NPCTraits(NPCTraits.Curious, NPCTraits.Pacifist);
            return new NPC(identity, vitals, psych, new NPCSocial(), memoryCapacity: 100, traits: traits);
        }

        /// <summary>
        /// A hard-working farmer. Early dawn schedule, high conscientiousness.
        /// Traits: Cautious.
        /// </summary>
        public static NPC CreateFarmer(SimRng rng, string name = null, string faction = "Farmers Guild")
        {
            name ??= "Farmer";
            var identity = new NPCIdentity(
                rng.NextId("npc"), name, age: rng.NextInt(18, 60),
                "Unknown", "Farmer", faction, "Farmer");

            var psych = new NPCPsychology(
                extraversion:      rng.NextFloat(0.3f, 0.6f),
                agreeableness:     rng.NextFloat(0.5f, 0.8f),
                conscientiousness: rng.NextFloat(0.5f, 0.8f),
                neuroticism:       rng.NextFloat(0.2f, 0.5f),
                openness:          rng.NextFloat(0.4f, 0.7f));

            var traits = new NPCTraits(NPCTraits.Cautious);
            return new NPC(identity, new NPCVitals(90f, 120f), psych, new NPCSocial(), memoryCapacity: 50, traits: traits);
        }

        /// <summary>
        /// A devout priest. High agreeableness and openness, spiritual focus.
        /// Traits: Devout, Pacifist.
        /// </summary>
        public static NPC CreatePriest(SimRng rng, string name = null, string faction = "Temple")
        {
            name ??= "Priest";
            var identity = new NPCIdentity(
                rng.NextId("npc"), name, age: rng.NextInt(30, 70),
                "Unknown", "Priest", faction, "Priest");

            var psych = new NPCPsychology(
                extraversion:      rng.NextFloat(0.4f, 0.7f),
                agreeableness:     rng.NextFloat(0.7f, 1.0f),
                conscientiousness: rng.NextFloat(0.6f, 0.9f),
                neuroticism:       rng.NextFloat(0.1f, 0.4f),
                openness:          rng.NextFloat(0.6f, 1.0f));

            var traits = new NPCTraits("Devout", NPCTraits.Pacifist);
            return new NPC(identity, new NPCVitals(85f, 90f), psych, new NPCSocial(), memoryCapacity: 70, traits: traits);
        }
    }
}
