using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Determines whether a sensed <see cref="Stimulus"/> is salient enough
    /// to become a <see cref="PerceivedObject"/>.
    ///
    /// Psychological traits bias the filter:
    /// - High Neuroticism → extra sensitivity to Threat stimuli.
    /// - High Openness    → novel stimuli bypass the threshold.
    /// - Low Energy       → attention threshold rises (fatigue effect).
    /// </summary>
    public sealed class PerceptionFilter
    {
        // ─── Tuneable parameters ──────────────────────────────────────────────────

        /// <summary>
        /// Minimum salience score [0, 1] required for a stimulus to be perceived.
        /// Stimuli scoring below this are silently dropped.
        /// </summary>
        public float AttentionThreshold { get; set; } = 0.2f;

        /// <summary>Tags always perceived regardless of threshold (e.g. "Threat", "Fire").</summary>
        public string[] HighPriorityTags { get; set; } = { "Threat", "Fire", "Ally" };

        // ─── Core evaluation ──────────────────────────────────────────────────────

        /// <summary>
        /// Returns the salience score [0, 1] for the given stimulus.
        /// A score of 0 means "do not perceive". Scores below <see cref="AttentionThreshold"/>
        /// are also discarded unless the tag is high-priority.
        /// </summary>
        /// <param name="stimulus">The incoming stimulus.</param>
        /// <param name="vitals">NPC vitals — fatigue affects threshold.</param>
        /// <param name="psychology">NPC psychology — traits bias scoring.</param>
        public float Evaluate(Stimulus stimulus, NPCVitals vitals, NPCPsychology psychology)
        {
            float score = stimulus.Intensity;

            // Neuroticism amplifies threat sensitivity
            if (HasTag(stimulus.Tag, "Threat"))
                score *= 1f + psychology.Neuroticism * 0.8f;

            // Openness lowers the cost of filtering novel/unfamiliar stimuli
            if (stimulus.Type == StimulusType.Social)
                score *= 0.7f + psychology.Openness * 0.3f;

            // Agreeableness boosts social / ally signals
            if (HasTag(stimulus.Tag, "Ally") || HasTag(stimulus.Tag, "Social"))
                score *= 0.8f + psychology.Agreeableness * 0.2f;

            score = Math.Clamp(score, 0f, 1f);

            // Fatigue effect: attention threshold rises when energy is low
            float effectiveThreshold = AttentionThreshold + (1f - vitals.Energy / vitals.MaxEnergy) * 0.15f;

            // High-priority tags always pass, regardless of threshold
            if (score < effectiveThreshold && !IsHighPriority(stimulus.Tag))
                return 0f;

            return score;
        }

        // ─── Helpers ──────────────────────────────────────────────────────────────

        private bool IsHighPriority(string tag)
        {
            if (string.IsNullOrEmpty(tag)) return false;
            foreach (var t in HighPriorityTags)
                if (string.Equals(t, tag, StringComparison.OrdinalIgnoreCase)) return true;
            return false;
        }

        private static bool HasTag(string stimulusTag, string check) =>
            string.Equals(stimulusTag, check, StringComparison.OrdinalIgnoreCase);

        public override string ToString() =>
            $"[PerceptionFilter] Threshold:{AttentionThreshold:F2} PriorityTags:{string.Join(",", HighPriorityTags)}";
    }
}
