using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Deterministic pseudo-random number generator.
    /// All randomness in the simulation flows through this class.
    /// Given the same seed, identical sequences are produced every time —
    /// enabling full replay support.
    /// </summary>
    public sealed class SimRng
    {
        private readonly Random _random;
        private readonly int    _seed;
        private int             _callCount;

        /// <summary>The seed this instance was created with.</summary>
        public int Seed => _seed;

        /// <summary>How many values have been drawn — useful for debugging replay drift.</summary>
        public int CallCount => _callCount;

        public SimRng(int seed)
        {
            _seed   = seed;
            _random = new Random(seed);
        }

        // ─── Primitives ───────────────────────────────────────────────────────────

        /// <summary>Returns a float in [0, 1).</summary>
        public float NextFloat()
        {
            _callCount++;
            return (float)_random.NextDouble();
        }

        /// <summary>Returns a float in [min, max).</summary>
        public float NextFloat(float min, float max)
        {
            _callCount++;
            return min + (float)_random.NextDouble() * (max - min);
        }

        /// <summary>Returns an int in [min, maxExclusive).</summary>
        public int NextInt(int min, int maxExclusive)
        {
            _callCount++;
            return _random.Next(min, maxExclusive);
        }

        /// <summary>Returns true with the given probability [0, 1].</summary>
        public bool Chance(float probability)
        {
            _callCount++;
            return _random.NextDouble() < probability;
        }

        // ─── ID Generation ────────────────────────────────────────────────────────

        /// <summary>
        /// Generates a deterministic, unique-ish ID string.
        /// Format: "{prefix}_{hex}" — avoids Guid.NewGuid() which is non-deterministic.
        /// </summary>
        public string NextId(string prefix = "id")
        {
            // Combine seed + call count for a stable, collision-resistant string.
            uint hash = (uint)(_seed * 2654435761u ^ (uint)(_callCount * 40503u));
            _callCount++;
            return $"{prefix}_{hash:x8}";
        }

        // ─── Helpers ──────────────────────────────────────────────────────────────

        /// <summary>Shuffles a list in-place using Fisher-Yates.</summary>
        public void Shuffle<T>(System.Collections.Generic.List<T> list)
        {
            for (int i = list.Count - 1; i > 0; i--)
            {
                int j = NextInt(0, i + 1);
                (list[i], list[j]) = (list[j], list[i]);
            }
        }

        public override string ToString() => $"[SimRng] seed={_seed} calls={_callCount}";
    }
}
