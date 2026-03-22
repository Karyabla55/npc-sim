using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Tracks an NPC's physical life stats: health, energy, hunger, thirst, and stress.
    /// All setters clamp values to their valid ranges.
    /// </summary>
    [Serializable]
    public class NPCVitals
    {
        // ─── Health ───────────────────────────────────────────────────────────────
        /// <summary>Current health points [0, MaxHealth].</summary>
        public float Health    { get; private set; }
        public float MaxHealth { get; private set; }

        // ─── Energy ───────────────────────────────────────────────────────────────
        /// <summary>Current energy [0, MaxEnergy].</summary>
        public float Energy    { get; private set; }
        public float MaxEnergy { get; private set; }
        /// <summary>Energy normalised to [0, 1] for scoring convenience.</summary>
        public float EnergyNorm => MaxEnergy > 0f ? Energy / MaxEnergy : 0f;

        // ─── Needs ────────────────────────────────────────────────────────────────
        /// <summary>Hunger level [0, 1]. 0 = full, 1 = starving.</summary>
        public float Hunger { get; private set; }

        /// <summary>Thirst level [0, 1]. 0 = hydrated, 1 = dehydrated.</summary>
        public float Thirst { get; private set; }

        // ─── Stress ───────────────────────────────────────────────────────────────
        /// <summary>Stress level [0, 1].</summary>
        public float Stress { get; private set; }

        // ─── Alive check ──────────────────────────────────────────────────────────
        public bool IsAlive => Health > 0f;

        // ─── Constructor ──────────────────────────────────────────────────────────
        public NPCVitals(float maxHealth = 100f, float maxEnergy = 100f)
        {
            MaxHealth = maxHealth;
            Health    = maxHealth;
            MaxEnergy = maxEnergy;
            Energy    = maxEnergy;
            Hunger    = 0f;
            Thirst    = 0f;
            Stress    = 0f;
        }

        // ─── Mutations ────────────────────────────────────────────────────────────
        public void ApplyDamage(float amount)   => Health = Math.Clamp(Health - amount, 0f, MaxHealth);
        public void Heal(float amount)          => Health = Math.Clamp(Health + amount, 0f, MaxHealth);
        public void SetHealth(float value)      => Health = Math.Clamp(value, 0f, MaxHealth);
        public void ConsumeEnergy(float amount) => Energy = Math.Clamp(Energy - amount, 0f, MaxEnergy);
        public void RestoreEnergy(float amount) => Energy = Math.Clamp(Energy + amount, 0f, MaxEnergy);
        public void SetEnergy(float value)      => Energy = Math.Clamp(value, 0f, MaxEnergy);
        public void SetHunger(float value)      => Hunger = Math.Clamp(value, 0f, 1f);
        public void SetThirst(float value)      => Thirst = Math.Clamp(value, 0f, 1f);
        public void SetStress(float value)      => Stress = Math.Clamp(value, 0f, 1f);

        public override string ToString() =>
            $"[Vitals] HP:{Health:F0}/{MaxHealth:F0} EN:{Energy:F0}/{MaxEnergy:F0} Hunger:{Hunger:P0} Thirst:{Thirst:P0} Stress:{Stress:P0}";
    }
}
