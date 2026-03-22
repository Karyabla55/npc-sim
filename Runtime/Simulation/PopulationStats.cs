using System;
using System.Collections.Generic;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Aggregate civilisation-level statistics tracked across all NPCs.
    /// Updated once per sim-tick by <see cref="SimulationManager"/>.
    /// Useful for dashboards, scenario victory conditions, and AI analytics.
    /// </summary>
    public sealed class PopulationStats
    {
        // ─── Population ───────────────────────────────────────────────────────────
        public int   TotalNPCs        { get; private set; }
        public int   AliveNPCs        { get; private set; }
        public int   DeadThisTick     { get; private set; }

        // ─── Averages ─────────────────────────────────────────────────────────────
        public float AvgHealth        { get; private set; }
        public float AvgHunger        { get; private set; }
        public float AvgThirst        { get; private set; }
        public float AvgEnergy        { get; private set; }
        public float AvgStress        { get; private set; }
        public float AvgHappiness     { get; private set; }
        public float AvgFear          { get; private set; }
        public float AvgReputation    { get; private set; }

        // ─── Events this tick ─────────────────────────────────────────────────────
        public int   CombatEventsThisTick  { get; private set; }
        public int   TradeEventsThisTick   { get; private set; }
        public int   SocialEventsThisTick  { get; private set; }

        // ─── Historical ring ──────────────────────────────────────────────────────
        private const int HistoryLength = 100;
        private readonly Queue<float> _happinessHistory = new(HistoryLength);
        private readonly Queue<float> _hungerHistory    = new(HistoryLength);

        public IReadOnlyCollection<float> HappinessHistory => _happinessHistory;
        public IReadOnlyCollection<float> HungerHistory    => _hungerHistory;

        // ─── Update ───────────────────────────────────────────────────────────────

        /// <summary>
        /// Recomputes all statistics from the live NPC list.
        /// Called once per tick by <see cref="SimulationManager"/>.
        /// </summary>
        public void Update(IReadOnlyList<NPC> npcs, IReadOnlyCollection<SimEvent> events)
        {
            TotalNPCs     = npcs.Count;
            DeadThisTick  = 0;
            int alive     = 0;
            float h = 0, hunger = 0, thirst = 0, energy = 0, stress = 0, happy = 0, fear = 0, rep = 0;

            foreach (var npc in npcs)
            {
                if (!npc.Vitals.IsAlive) { DeadThisTick++; continue; }
                alive++;
                h      += npc.Vitals.Health;
                hunger += npc.Vitals.Hunger;
                thirst += npc.Vitals.Thirst;
                energy += npc.Vitals.Energy;
                stress += npc.Vitals.Stress;
                happy  += npc.Psychology.Happiness;
                fear   += npc.Psychology.Fear;
                rep    += npc.Social.Reputation;
            }

            AliveNPCs    = alive;
            float inv    = alive > 0 ? 1f / alive : 0f;
            AvgHealth    = h      * inv;
            AvgHunger    = hunger * inv;
            AvgThirst    = thirst * inv;
            AvgEnergy    = energy * inv;
            AvgStress    = stress * inv;
            AvgHappiness = happy  * inv;
            AvgFear      = fear   * inv;
            AvgReputation= rep    * inv;

            // Event breakdown
            CombatEventsThisTick = SocialEventsThisTick = TradeEventsThisTick = 0;
            foreach (var ev in events)
            {
                switch (ev.Category)
                {
                    case "combat":   CombatEventsThisTick++;  break;
                    case "social":   SocialEventsThisTick++;  break;
                    case "economy":  TradeEventsThisTick++;   break;
                }
            }

            // History ring
            if (_happinessHistory.Count >= HistoryLength) _happinessHistory.Dequeue();
            _happinessHistory.Enqueue(AvgHappiness);
            if (_hungerHistory.Count >= HistoryLength) _hungerHistory.Dequeue();
            _hungerHistory.Enqueue(AvgHunger);
        }

        // ─── Conditions ───────────────────────────────────────────────────────────

        /// <summary>Returns true when average happiness is above the given threshold (default: 0.5).</summary>
        public bool IsProsperous(float threshold = 0.5f) => AvgHappiness > threshold && AvgHunger < 0.4f;

        /// <summary>Returns true when average hunger exceeds the given threshold — a famine condition.</summary>
        public bool IsFamine(float threshold = 0.7f) => AvgHunger > threshold;

        /// <summary>Returns true when combat events dominate social events (war-like state).</summary>
        public bool IsAtWar => CombatEventsThisTick > SocialEventsThisTick * 2;

        public override string ToString() =>
            $"[PopStats] Pop:{AliveNPCs} AvgHappy:{AvgHappiness:+0.00;-0.00} AvgHunger:{AvgHunger:P0} Combat:{CombatEventsThisTick} Trade:{TradeEventsThisTick}";
    }
}
