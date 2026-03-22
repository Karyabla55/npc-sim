using System;
using System.Collections.Generic;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Immutable snapshot of all information an action needs to evaluate or execute.
    /// Created once per NPC per tick and passed to every action candidate.
    /// </summary>
    public sealed class ActionContext
    {
        // ─── Self ─────────────────────────────────────────────────────────────────
        /// <summary>The NPC currently making a decision.</summary>
        public NPC Self { get; }

        // ─── Shortcut accessors (D5 fix) ──────────────────────────────────────────
        /// <summary>Shortcut to Self.Goals — actions can freely query the NPC's goal list.</summary>
        public NPCGoals Goals => Self.Goals;

        // ─── World Perception ─────────────────────────────────────────────────────
        /// <summary>All percepts active for this NPC this tick.</summary>
        public IReadOnlyList<PerceivedObject> ActivePercepts { get; }

        // ─── Time ─────────────────────────────────────────────────────────────────
        /// <summary>Current simulation timestamp (seconds since start).</summary>
        public float CurrentTime { get; }

        /// <summary>Elapsed simulation seconds since the last tick.</summary>
        public float DeltaTime   { get; }

        /// <summary>
        /// Current simulation hour of day [0, 24).
        /// Computed from CurrentTime and DayLengthSeconds for schedule-aware actions.
        /// </summary>
        public float SimDayHour  { get; }

        // ─── World Access ─────────────────────────────────────────────────────────
        /// <summary>World interface. Actions use this to query entities, move NPCs, or publish events.</summary>
        public ISimWorld World { get; }

        // ─── Determinism ──────────────────────────────────────────────────────────
        /// <summary>Shared simulation RNG. Draw values here to remain deterministic.</summary>
        public SimRng Rng { get; }

        // ─── Constructor ──────────────────────────────────────────────────────────
        public ActionContext(
            NPC                            self,
            IReadOnlyList<PerceivedObject> percepts,
            float                          currentTime,
            float                          deltaTime,
            ISimWorld                      world,
            SimRng                         rng,
            float                          dayLengthSeconds = 1440f)
        {
            Self           = self    ?? throw new ArgumentNullException(nameof(self));
            ActivePercepts = percepts ?? Array.Empty<PerceivedObject>();
            CurrentTime    = currentTime;
            DeltaTime      = deltaTime;
            World          = world;
            Rng            = rng;
            // Hour of day [0, 24)
            SimDayHour     = dayLengthSeconds > 0f
                ? (currentTime % dayLengthSeconds) / dayLengthSeconds * 24f
                : 12f;
        }

        // ─── Perception helpers ───────────────────────────────────────────────────

        /// <summary>Returns true if any active percept has the given tag (case-insensitive).</summary>
        public bool HasPercept(string tag)
        {
            foreach (var p in ActivePercepts)
                if (p.Tag.Equals(tag, StringComparison.OrdinalIgnoreCase)) return true;
            return false;
        }

        /// <summary>Returns the highest-salience percept matching the given tag, or null.</summary>
        public PerceivedObject GetTopPercept(string tag)
        {
            PerceivedObject best    = null;
            float           bestSal = -1f;
            foreach (var p in ActivePercepts)
            {
                if (!p.Tag.Equals(tag, StringComparison.OrdinalIgnoreCase)) continue;
                if (p.Salience > bestSal) { bestSal = p.Salience; best = p; }
            }
            return best;
        }

        /// <summary>Returns all percepts with the given tag.</summary>
        public List<PerceivedObject> GetAllPercepts(string tag)
        {
            var result = new List<PerceivedObject>();
            foreach (var p in ActivePercepts)
                if (p.Tag.Equals(tag, StringComparison.OrdinalIgnoreCase)) result.Add(p);
            return result;
        }

        // ─── Goal helpers (D5 fix) ────────────────────────────────────────────────

        /// <summary>Returns true if the NPC has an active goal of the given type.</summary>
        public bool HasGoal(string goalType) => Goals.HasActiveGoal(goalType);

        /// <summary>Returns the highest priority active goal of the given type, or null.</summary>
        public Goal GetTopGoalOfType(string goalType)
        {
            var list = Goals.GetByType(goalType);
            return list.Count > 0 ? list[0] : null;
        }

        public override string ToString() =>
            $"[ActionContext] {Self.Identity.DisplayName} percepts:{ActivePercepts.Count} hour:{SimDayHour:F1}h t={CurrentTime:F1}";
    }
}
