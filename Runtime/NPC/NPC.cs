using System;
using System.Collections.Generic;

namespace ForgeProject.Sim
{
    /// <summary>
    /// The primary NPC data container.
    /// Aggregates Vitals, Identity, Psychology, Social, Belief, Memory, Goals, Traits, and Inventory.
    /// All logic lives in Systems — this class is pure data + minimal wiring.
    /// </summary>
    public class NPC
    {
        // ─── Components ───────────────────────────────────────────────────────────
        public NPCVitals     Vitals      { get; private set; }
        public NPCIdentity   Identity    { get; private set; }
        public NPCPsychology Psychology  { get; private set; }
        public NPCSocial     Social      { get; private set; }
        public BeliefSystem  Beliefs     { get; private set; }
        public NPCMemory     Memory      { get; private set; }
        public NPCGoals      Goals       { get; private set; }
        public NPCTraits     Traits      { get; private set; }
        public NPCInventory  Inventory   { get; private set; }
        public NPCSchedule   Schedule    { get; private set; }

        // ─── World State ──────────────────────────────────────────────────────────
        /// <summary>Current world position. Updated by movement actions / SimWorldAdapter.</summary>
        public SimVector3 Position { get; set; } = SimVector3.Zero;

        /// <summary>Forward facing direction (used by SensorRange FOV check).</summary>
        public SimVector3 Forward  { get; set; } = new SimVector3(0, 0, 1);

        /// <summary>Whether this NPC is participating in the active simulation.</summary>
        public bool IsActive { get; private set; } = true;

        // ─── Config reference (injected by SimulationManager) ─────────────────────
        private SimulationConfig _config;

        // ─── Constructor ──────────────────────────────────────────────────────────
        /// <summary>Creates a fully configured NPC. Config is injected later by SimulationManager.</summary>
        public NPC(NPCIdentity    identity,
                   NPCVitals      vitals        = null,
                   NPCPsychology  psychology    = null,
                   NPCSocial      social        = null,
                   int            memoryCapacity = 50,
                   NPCTraits      traits        = null,
                   int            inventorySlots = 10)
        {
            Identity   = identity   ?? throw new ArgumentNullException(nameof(identity));
            Vitals     = vitals     ?? new NPCVitals();
            Psychology = psychology ?? new NPCPsychology();
            Social     = social     ?? new NPCSocial();
            Beliefs    = new BeliefSystem();
            Memory     = new NPCMemory(memoryCapacity);
            Goals      = new NPCGoals();
            Traits     = traits     ?? new NPCTraits();
            Inventory  = new NPCInventory(inventorySlots);
            Schedule   = NPCSchedule.ForOccupation(identity.Occupation);
        }

        // ─── Config injection ─────────────────────────────────────────────────────
        /// <summary>Called by SimulationManager.AddNPC to wire simulation-wide config rates.</summary>
        public void InjectConfig(SimulationConfig config) => _config = config;

        /// <summary>
        /// Replaces this NPC's daily schedule. Called by the Bridge layer when a
        /// <see cref="ForgeProject.Sim.Bridge.NPCScheduleSO"/> override is assigned.
        /// </summary>
        public void SetSchedule(NPCSchedule schedule) => Schedule = schedule ?? Schedule;

        // ─── Tick ─────────────────────────────────────────────────────────────────
        /// <summary>
        /// Called every simulation step via <see cref="SimulationManager"/>.
        /// Applies physiological decay, emotional decay, relation decay, memory/belief decay,
        /// goal expiry pruning, and cross-component stress links.
        /// </summary>
        public void Tick(float deltaTime, float currentTime)
        {
            if (!IsActive || !Vitals.IsAlive) return;

            // Use config rates where available, fallback to sensible defaults
            float hungerRate  = _config?.HungerDecayRate         ?? 0.001f;
            float thirstRate  = _config?.ThirstDecayRate         ?? 0.002f;
            float energyRate  = _config?.EnergyDecayRate         ?? 0.5f;
            float memDecay    = _config?.GlobalMemoryDecayRate   ?? 0.001f;
            float beliefDecay = _config?.GlobalBeliefDecayRate   ?? 0.005f;
            float relDecay    = _config?.RelationDecayRate       ?? 0.00005f;
            float fearRate    = _config?.FearDecayRate           ?? 0.0005f;
            float happyRate   = _config?.HappinessDecayRate      ?? 0.0003f;
            float angerRate   = _config?.AngerDecayRate          ?? 0.0004f;

            // ── Physiology (D1 fix) ──
            Vitals.SetHunger(Vitals.Hunger + hungerRate * deltaTime);
            Vitals.SetThirst(Vitals.Thirst + thirstRate * deltaTime);
            Vitals.ConsumeEnergy(energyRate * deltaTime);

            // ── DeathByNeglect ──
            if (_config?.DeathByNeglect == true)
            {
                if (Vitals.Hunger >= 1f || Vitals.Thirst >= 1f)
                    Vitals.ApplyDamage(10f * deltaTime);
            }

            // ── Cross-component: Stress → Anger (Neuroticism-scaled) ──
            float stressAngerSpill = Vitals.Stress * 0.02f * deltaTime * Psychology.Neuroticism;
            Psychology.SetAnger(Psychology.Anger + stressAngerSpill);

            // ── Hunger/Thirst → Stress ──
            float needStress = (Vitals.Hunger + Vitals.Thirst) * 0.01f * deltaTime;
            Vitals.SetStress(Vitals.Stress + needStress);

            // ── Emotional decay (D6 fix) ──
            Psychology.DecayEmotions(deltaTime, fearRate, happyRate, angerRate);

            // ── Relation decay (D4 fix) ──
            Social.TickDecay(deltaTime, relDecay);

            // ── Memory and belief decay ──
            Memory.DecayAll(memDecay * deltaTime);
            Beliefs.DecayAll(beliefDecay * deltaTime);

            // ── Prune expired goals ──
            Goals.PruneExpired(currentTime);
        }

        // ─── Event witnessing ─────────────────────────────────────────────────────
        /// <summary>
        /// NPC witnesses a SimEvent — stores it in memory, updates beliefs, and reacts emotionally.
        /// </summary>
        public void WitnessEvent(SimEvent simEvent, IEnumerable<string> beliefSubjects, float currentTime)
        {
            if (simEvent == null) return;

            // Record in episodic memory
            float emotionalWeight = simEvent.Impact * (1f - Psychology.Neuroticism * 0.5f);
            Memory.Remember(simEvent, emotionalWeight, currentTime);

            // Update beliefs about each subject
            Beliefs.ProcessEvent(simEvent, beliefSubjects, currentTime);

            // Emotional reaction (D6 fix) ─────────────────────────────────────────
            float stressDelta = MathF.Abs(simEvent.Impact) * 0.1f * Psychology.Neuroticism;
            Vitals.SetStress(Vitals.Stress + stressDelta);

            if (simEvent.Impact < -0.3f)
            {
                // Negative event → Fear spike (Neuroticism-amplified)
                float fearSpike = MathF.Abs(simEvent.Impact) * 0.15f * Psychology.Neuroticism;
                Psychology.SetFear(Psychology.Fear + fearSpike);
            }
            else if (simEvent.Impact > 0.2f)
            {
                // Positive event → Happiness boost (dampened by Neuroticism)
                float happyBoost = simEvent.Impact * 0.1f * (1f - Psychology.Neuroticism * 0.5f);
                Psychology.SetHappiness(Psychology.Happiness + happyBoost);
            }
        }

        // ─── Social interaction ───────────────────────────────────────────────────
        /// <summary>Interacts with another NPC, updating the relation between them.</summary>
        public void Interact(NPC other, float trustDelta, float affinityDelta, float respectDelta, float currentTime)
        {
            if (other == null) return;
            var relation = Social.GetOrCreateRelation(Identity.NpcId, other.Identity.NpcId);
            relation.ApplyInteraction(trustDelta, affinityDelta, respectDelta, currentTime);
        }

        // ─── Need → Goal pipeline ─────────────────────────────────────────────────
        /// <summary>
        /// Converts urgent physiological needs into active goals.
        /// Called by NeedSystem each tick — avoids goal flooding by checking HasActiveGoal.
        /// </summary>
        public void RefreshNeedGoals(float currentTime, float urgencyWindow = 300f)
        {
            float expiry = currentTime + urgencyWindow;

            if (Vitals.Hunger > 0.65f && !Goals.HasActiveGoal(GoalType.FindFood))
                Goals.AddGoal(new Goal(GoalType.FindFood, "I need to eat", Vitals.Hunger, expiry));

            if (Vitals.Thirst > 0.70f && !Goals.HasActiveGoal(GoalType.FindWater))
                Goals.AddGoal(new Goal(GoalType.FindWater, "I need water", Vitals.Thirst, expiry));

            if (Vitals.Energy < 0.30f && !Goals.HasActiveGoal(GoalType.Rest))
                Goals.AddGoal(new Goal(GoalType.Rest, "I need rest", 1f - Vitals.Energy, expiry));
        }

        // ─── Lifecycle ────────────────────────────────────────────────────────────
        public void Deactivate() => IsActive = false;

        public override string ToString() =>
            $"[NPC] {Identity.DisplayName} (ID:{Identity.NpcId}) | {(IsActive ? "Active" : "Inactive")} | {Vitals} | {Psychology} | {Inventory}";
    }
}
