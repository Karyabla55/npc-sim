using System;
using System.Collections.Generic;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Per-NPC perception orchestrator.
    /// Each tick it:
    ///   1. Pre-filters stimuli by sensor range (cheap distance check).
    ///   2. Evaluates salience via <see cref="PerceptionFilter"/> (psychology-aware).
    ///   3. Upserts / creates <see cref="PerceivedObject"/> entries.
    ///   4. Prunes expired percepts.
    ///   5. Returns changed percepts so the caller can route them to NPC.WitnessEvent().
    ///
    /// Held per-NPC. Stateful between ticks (retains percepts until they expire).
    /// </summary>
    public sealed class PerceptionSystem
    {
        // ─── Configuration ────────────────────────────────────────────────────────

        /// <summary>How many sim-seconds a percept survives without refresh.</summary>
        public float PerceptTimeout { get; set; } = 30f;

        // ─── Components ───────────────────────────────────────────────────────────

        private readonly SensorRange      _sensor;
        private readonly PerceptionFilter _filter;

        // ─── State ────────────────────────────────────────────────────────────────

        private readonly List<PerceivedObject> _percepts = new();

        /// <summary>All currently active perceived objects.</summary>
        public IReadOnlyList<PerceivedObject> ActivePercepts => _percepts;

        // ─── Constructor ──────────────────────────────────────────────────────────

        public PerceptionSystem(SensorRange sensor = null, PerceptionFilter filter = null)
        {
            _sensor = sensor ?? new SensorRange();
            _filter = filter ?? new PerceptionFilter();
        }

        // ─── Tick ─────────────────────────────────────────────────────────────────

        /// <summary>
        /// Processes a batch of stimuli for a single tick.
        /// </summary>
        /// <param name="stimuli">All stimuli available this tick (pre-dispatched to this NPC).</param>
        /// <param name="npcPosition">Current world position of the NPC.</param>
        /// <param name="npcForward">Facing direction (Zero = omnidirectional).</param>
        /// <param name="vitals">NPC vitals used by the filter.</param>
        /// <param name="psychology">NPC psychology used by the filter.</param>
        /// <param name="currentTime">Current simulation timestamp.</param>
        /// <returns>List of percepts that were newly created or updated this tick.</returns>
        public List<PerceivedObject> Tick(
            IReadOnlyList<Stimulus> stimuli,
            SimVector3   npcPosition,
            SimVector3   npcForward,
            NPCVitals    vitals,
            NPCPsychology psychology,
            float        currentTime)
        {
            // Mark all existing percepts as "not currently visible" before this tick
            foreach (var p in _percepts) p.MarkNotVisible();

            var changed = new List<PerceivedObject>();

            foreach (var stimulus in stimuli)
            {
                // Step 1: Spatial pre-filter (cheap)
                if (!_sensor.CanSense(stimulus, npcPosition, npcForward)) continue;

                // Step 2: Salience evaluation (psychology-based)
                float salience = _filter.Evaluate(stimulus, vitals, psychology);
                if (salience <= 0f) continue;

                // Derive threat level from intensity + tag
                float threat = stimulus.Tag.Equals("Threat", StringComparison.OrdinalIgnoreCase)
                    ? stimulus.Intensity * (0.5f + psychology.Neuroticism * 0.5f)
                    : 0f;

                // Step 3: Upsert percept
                var existing = FindPercept(stimulus.SourceId);
                if (existing != null)
                {
                    existing.Refresh(stimulus.SourcePosition, currentTime, threat, salience);
                }
                else
                {
                    string objectType = InferObjectType(stimulus);
                    existing = new PerceivedObject(
                        stimulus.SourceId, objectType, stimulus.SourcePosition,
                        currentTime, threat, salience, stimulus.Tag);
                    _percepts.Add(existing);
                }

                changed.Add(existing);
            }

            // Step 4: Prune expired percepts
            _percepts.RemoveAll(p => p.IsExpired(currentTime, PerceptTimeout));

            return changed;
        }

        // ─── Convenience queries ──────────────────────────────────────────────────

        /// <summary>Returns all active percepts tagged as threats, sorted by threat level descending.</summary>
        public List<PerceivedObject> GetThreats()
        {
            var result = _percepts.FindAll(p =>
                p.Tag.Equals("Threat", StringComparison.OrdinalIgnoreCase) && p.ThreatLevel > 0f);
            result.Sort((a, b) => b.ThreatLevel.CompareTo(a.ThreatLevel));
            return result;
        }

        /// <summary>Returns all active percepts tagged as allies.</summary>
        public List<PerceivedObject> GetAllies() =>
            _percepts.FindAll(p => p.Tag.Equals("Ally", StringComparison.OrdinalIgnoreCase));

        /// <summary>Returns the closest food percept, or null.</summary>
        public PerceivedObject GetNearestFood(SimVector3 npcPosition)
        {
            PerceivedObject nearest = null;
            float nearestSqr = float.MaxValue;

            foreach (var p in _percepts)
            {
                if (!p.Tag.Equals("Food", StringComparison.OrdinalIgnoreCase)) continue;
                float d = SimVector3.SqrDistance(npcPosition, p.LastKnownPosition);
                if (d < nearestSqr) { nearestSqr = d; nearest = p; }
            }
            return nearest;
        }

        // ─── Helpers ──────────────────────────────────────────────────────────────

        private PerceivedObject FindPercept(string sourceId)
        {
            foreach (var p in _percepts)
                if (p.ObjectId == sourceId) return p;
            return null;
        }

        private static string InferObjectType(Stimulus s) => s.Type switch
        {
            StimulusType.Visual    => s.Tag == "Threat" ? "Hazard" : "Entity",
            StimulusType.Social    => "NPC",
            StimulusType.Audio     => "Noise",
            StimulusType.Olfactory => "Scent",
            _                      => "Unknown"
        };

        public override string ToString() =>
            $"[PerceptionSystem] {_percepts.Count} active percept(s)";
    }
}
