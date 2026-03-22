using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Unity-free 3D vector for use throughout the simulation core.
    /// Keeps all domain logic independent of UnityEngine.
    /// </summary>
    [Serializable]
    public readonly struct SimVector3 : IEquatable<SimVector3>
    {
        public readonly float X;
        public readonly float Y;
        public readonly float Z;

        public static readonly SimVector3 Zero = new(0f, 0f, 0f);
        public static readonly SimVector3 One  = new(1f, 1f, 1f);

        public SimVector3(float x, float y, float z)
        {
            X = x; Y = y; Z = z;
        }

        // ─── Math ─────────────────────────────────────────────────────────────────

        public float SqrMagnitude => X * X + Y * Y + Z * Z;
        public float Magnitude    => MathF.Sqrt(SqrMagnitude);

        /// <summary>Euclidean distance squared — avoids sqrt for range checks.</summary>
        public static float SqrDistance(SimVector3 a, SimVector3 b)
        {
            float dx = a.X - b.X;
            float dy = a.Y - b.Y;
            float dz = a.Z - b.Z;
            return dx * dx + dy * dy + dz * dz;
        }

        /// <summary>Euclidean distance.</summary>
        public static float Distance(SimVector3 a, SimVector3 b)
            => MathF.Sqrt(SqrDistance(a, b));

        /// <summary>Returns true when <paramref name="other"/> is within <paramref name="radius"/>.</summary>
        public bool WithinRadius(SimVector3 other, float radius)
            => SqrDistance(this, other) <= radius * radius;

        public SimVector3 Normalized()
        {
            float m = Magnitude;
            return m > 1e-6f ? new SimVector3(X / m, Y / m, Z / m) : Zero;
        }

        // ─── Operators ────────────────────────────────────────────────────────────

        public static SimVector3 operator +(SimVector3 a, SimVector3 b) => new(a.X + b.X, a.Y + b.Y, a.Z + b.Z);
        public static SimVector3 operator -(SimVector3 a, SimVector3 b) => new(a.X - b.X, a.Y - b.Y, a.Z - b.Z);
        public static SimVector3 operator *(SimVector3 v, float s)      => new(v.X * s, v.Y * s, v.Z * s);
        public static SimVector3 operator *(float s, SimVector3 v)      => v * s;

        // ─── Equality ─────────────────────────────────────────────────────────────

        public bool Equals(SimVector3 other) => X == other.X && Y == other.Y && Z == other.Z;
        public override bool Equals(object obj) => obj is SimVector3 v && Equals(v);
        public override int GetHashCode() => HashCode.Combine(X, Y, Z);
        public static bool operator ==(SimVector3 a, SimVector3 b) => a.Equals(b);
        public static bool operator !=(SimVector3 a, SimVector3 b) => !a.Equals(b);

        public override string ToString() => $"({X:F2}, {Y:F2}, {Z:F2})";
    }
}
