using System;
using System.Collections.Generic;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Immutable set of personality trait tags attached to an NPC.
    /// Traits act as multipliers inside <c>UtilityEvaluator</c>, biasing
    /// action scores without hardcoding behavioural branches.
    /// </summary>
    /// <example>
    /// A "Brave" NPC has their FleeAction score reduced by 0.3.
    /// A "Greedy" NPC has their TradeAction score increased by 0.2.
    /// </example>
    [Serializable]
    public sealed class NPCTraits
    {
        // ─── Well-known trait constants ────────────────────────────────────────────

        public const string Brave       = "Brave";
        public const string Coward      = "Coward";
        public const string Greedy      = "Greedy";
        public const string Generous    = "Generous";
        public const string Loyal       = "Loyal";
        public const string Treacherous = "Treacherous";
        public const string Curious     = "Curious";
        public const string Cautious    = "Cautious";
        public const string Aggressive  = "Aggressive";
        public const string Pacifist    = "Pacifist";

        // ─── Storage ──────────────────────────────────────────────────────────────

        private readonly HashSet<string> _tags;

        /// <summary>All active trait tags.</summary>
        public IReadOnlyCollection<string> Tags => _tags;

        // ─── Constructors ─────────────────────────────────────────────────────────

        public NPCTraits(params string[] initialTags)
        {
            _tags = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var tag in initialTags)
                if (!string.IsNullOrWhiteSpace(tag))
                    _tags.Add(tag);
        }

        // ─── Queries ──────────────────────────────────────────────────────────────

        /// <summary>Returns true if the NPC has the specified trait.</summary>
        public bool Has(string trait) => _tags.Contains(trait);

        /// <summary>Returns true if the NPC has ANY of the specified traits.</summary>
        public bool HasAny(params string[] traits)
        {
            foreach (var t in traits) if (_tags.Contains(t)) return true;
            return false;
        }

        /// <summary>Returns true if the NPC has ALL of the specified traits.</summary>
        public bool HasAll(params string[] traits)
        {
            foreach (var t in traits) if (!_tags.Contains(t)) return false;
            return true;
        }

        // ─── Utility weight modifier ──────────────────────────────────────────────

        /// <summary>
        /// Returns a multiplier [0.5, 2.0] for a given action type based on traits.
        /// Evaluators call this to bend scores without branching logic.
        /// </summary>
        public float GetWeightModifier(string actionType)
        {
            float modifier = 1f;

            switch (actionType)
            {
                case "Flee":
                    if (Has(Brave))   modifier -= 0.35f;
                    if (Has(Coward))  modifier += 0.50f;
                    break;

                case "Attack":
                    if (Has(Aggressive)) modifier += 0.40f;
                    if (Has(Pacifist))   modifier -= 0.50f;
                    if (Has(Brave))      modifier += 0.20f;
                    break;

                case "Trade":
                    if (Has(Greedy))    modifier += 0.30f;
                    if (Has(Generous))  modifier += 0.15f;
                    break;

                case "Explore":
                    if (Has(Curious))  modifier += 0.35f;
                    if (Has(Cautious)) modifier -= 0.20f;
                    break;
            }

            return Math.Clamp(modifier, 0.1f, 2.0f);
        }

        public override string ToString() =>
            _tags.Count == 0 ? "[Traits] None" : $"[Traits] {string.Join(", ", _tags)}";
    }
}
