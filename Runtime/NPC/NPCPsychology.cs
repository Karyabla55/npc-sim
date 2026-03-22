using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// NPC's psychological profile: Big Five personality traits,
    /// transient emotional state, and a derived mood label.
    /// Emotional decay is ticked each sim frame so emotions return toward baseline.
    /// </summary>
    [Serializable]
    public class NPCPsychology
    {
        // ─── Big Five Personality [0, 1] ──────────────────────────────────────────
        /// <summary>Extraversion: 0 = introverted, 1 = extraverted.</summary>
        public float Extraversion     { get; private set; }

        /// <summary>Agreeableness: 0 = competitive, 1 = cooperative.</summary>
        public float Agreeableness    { get; private set; }

        /// <summary>Conscientiousness: 0 = impulsive, 1 = disciplined.</summary>
        public float Conscientiousness{ get; private set; }

        /// <summary>Neuroticism: 0 = calm, 1 = anxious.</summary>
        public float Neuroticism      { get; private set; }

        /// <summary>Openness: 0 = conservative, 1 = creative/curious.</summary>
        public float Openness         { get; private set; }

        // ─── Transient emotions ───────────────────────────────────────────────────
        /// <summary>Happiness [-1, 1]. -1 = deeply miserable, 1 = elated.</summary>
        public float Happiness { get; private set; }

        /// <summary>Fear [0, 1]. 0 = unafraid, 1 = terrified.</summary>
        public float Fear      { get; private set; }

        /// <summary>Anger [0, 1]. 0 = tranquil, 1 = furious.</summary>
        public float Anger     { get; private set; }

        // ─── Derived mood ─────────────────────────────────────────────────────────
        /// <summary>Summary mood label derived from current emotion values.</summary>
        public string MoodLabel { get; private set; }

        // ─── Constructor ──────────────────────────────────────────────────────────
        public NPCPsychology(
            float extraversion       = 0.5f,
            float agreeableness      = 0.5f,
            float conscientiousness  = 0.5f,
            float neuroticism        = 0.5f,
            float openness           = 0.5f)
        {
            Extraversion      = Math.Clamp(extraversion,      0f, 1f);
            Agreeableness     = Math.Clamp(agreeableness,     0f, 1f);
            Conscientiousness = Math.Clamp(conscientiousness, 0f, 1f);
            Neuroticism       = Math.Clamp(neuroticism,       0f, 1f);
            Openness          = Math.Clamp(openness,          0f, 1f);
            RecalculateMood();
        }

        // ─── Emotion setters (D6 fix) ─────────────────────────────────────────────
        public void SetHappiness(float value) { Happiness = Math.Clamp(value, -1f, 1f); RecalculateMood(); }
        public void SetFear(float value)      { Fear      = Math.Clamp(value,  0f, 1f); RecalculateMood(); }
        public void SetAnger(float value)     { Anger     = Math.Clamp(value,  0f, 1f); RecalculateMood(); }

        // ─── Emotion decay (D6 fix) ───────────────────────────────────────────────

        /// <summary>
        /// Decays Fear, Anger, and Happiness toward their baselines each tick.
        /// High-Neuroticism NPCs retain fear longer; low-Neuroticism NPCs recover faster.
        /// </summary>
        public void DecayEmotions(float deltaTime, float fearRate = 0.0005f, float happinessRate = 0.0003f, float angerRate = 0.0004f)
        {
            // Fear: high-Neuroticism means slow recovery
            float fearDecay = deltaTime * fearRate * (1f - Neuroticism * 0.5f);
            Fear = Math.Max(0f, Fear - fearDecay);

            // Happiness drifts back toward 0 (neutral)
            float happyDecay = deltaTime * happinessRate;
            Happiness = Happiness > 0f
                ? Math.Max(0f, Happiness - happyDecay)
                : Math.Min(0f, Happiness + happyDecay);

            // Anger: high-Agreeableness means faster cooling
            float angerDecay = deltaTime * angerRate * (1f + Agreeableness * 0.5f);
            Anger = Math.Max(0f, Anger - angerDecay);

            RecalculateMood();
        }

        // ─── Mood derivation ──────────────────────────────────────────────────────

        private void RecalculateMood()
        {
            if      (Fear      > 0.8f)             MoodLabel = "Terrified";
            else if (Anger     > 0.7f)             MoodLabel = "Furious";
            else if (Fear      > 0.5f)             MoodLabel = "Afraid";
            else if (Anger     > 0.4f)             MoodLabel = "Irritated";
            else if (Happiness > 0.7f)             MoodLabel = "Euphoric";
            else if (Happiness > 0.3f)             MoodLabel = "Happy";
            else if (Happiness < -0.6f)            MoodLabel = "Depressed";
            else if (Happiness < -0.2f)            MoodLabel = "Sad";
            else if (Neuroticism > 0.7f)           MoodLabel = "Anxious";
            else                                   MoodLabel = "Calm";
        }

        public override string ToString() =>
            $"[Psychology] Mood:{MoodLabel} | E:{Extraversion:F2} A:{Agreeableness:F2} C:{Conscientiousness:F2} N:{Neuroticism:F2} O:{Openness:F2}";
    }
}
