using System;
using System.Collections.Generic;

namespace ForgeProject.Sim
{
    // ─── Goal type constants ───────────────────────────────────────────────────────
    /// <summary>Well-known goal type strings used by actions and the need system.</summary>
    public static class GoalType
    {
        public const string Survive   = "Survive";
        public const string FindFood  = "FindFood";
        public const string FindWater = "FindWater";
        public const string Rest      = "Rest";
        public const string Socialize = "Socialize";
        public const string Work      = "Work";
        public const string Explore   = "Explore";
        public const string Trade     = "Trade";
        public const string Attack    = "Attack";
        public const string Pray      = "Pray";
        public const string Heal      = "Heal";
        public const string GoHome    = "GoHome";
    }

    /// <summary>
    /// NPC'nin sahip olduğu hedefleri ve bu hedeflerin önceliklerini yönetir.
    /// Hedefler karar sistemlerine girdi olarak sağlanır.
    /// </summary>
    [Serializable]
    public class NPCGoals
    {
        // ─── Hedef Listesi ────────────────────────────────────────────────────────
        public IReadOnlyList<Goal> Goals => _goals;
        private readonly List<Goal> _goals = new();

        // ─── İşlemler ─────────────────────────────────────────────────────────────
        /// <summary>Sisteme yeni bir hedef ekler.</summary>
        public void AddGoal(Goal goal)
        {
            if (goal == null) return;
            _goals.Add(goal);
            SortGoals();
        }

        /// <summary>Tamamlanan veya geçersizleşen hedefi kaldırır.</summary>
        public bool RemoveGoal(string goalId) =>
            _goals.RemoveAll(g => g.GoalId == goalId) > 0;

        /// <summary>Returns the highest priority active goal, or null.</summary>
        public Goal GetTopGoal() => _goals.Find(g => g.IsActive);

        /// <summary>Returns all active goals of a given type.</summary>
        public List<Goal> GetByType(string goalType) =>
            _goals.FindAll(g => g.GoalType == goalType && g.IsActive);

        /// <summary>Returns true if there is at least one active goal of the given type.</summary>
        public bool HasActiveGoal(string goalType) =>
            _goals.Exists(g => g.GoalType == goalType && g.IsActive);

        /// <summary>Prunes goals that have exceeded their expiry time, or are fully complete.</summary>
        public void PruneExpired(float currentTime) =>
            _goals.RemoveAll(g => g.IsExpired(currentTime));

        private void SortGoals() =>
            _goals.Sort((a, b) => b.Priority.CompareTo(a.Priority));

        public override string ToString() =>
            $"[Goals] {_goals.Count} goal(s) | Top: {GetTopGoal()?.GoalType ?? "None"}";
    }

    // ─── Yardımcı Tür ─────────────────────────────────────────────────────────────
    /// <summary>Tek bir NPC hedefini tanımlar.</summary>
    [Serializable]
    public class Goal
    {
        // Sequential deterministic counter — replaces Guid.NewGuid()
        private static int _counter;

        public string GoalId       { get; private set; }
        public string GoalType     { get; private set; }
        public string Description  { get; private set; }
        public float  Priority     { get; private set; }   // [0, 1]
        public bool   IsActive     { get; private set; } = true;
        public float  Progress     { get; private set; }   // [0, 1]
        /// <summary>If > 0, the goal auto-abandons after this sim-time.</summary>
        public float  ExpiresAt    { get; private set; }

        public Goal(string goalType, string description, float priority, float expiresAt = 0f)
        {
            GoalId      = $"goal_{System.Threading.Interlocked.Increment(ref _counter):D6}";
            GoalType    = goalType;
            Description = description;
            Priority    = Math.Clamp(priority, 0f, 1f);
            ExpiresAt   = expiresAt;
        }

        public void SetProgress(float value)  => Progress  = Math.Clamp(value, 0f, 1f);
        public void SetPriority(float value)  => Priority  = Math.Clamp(value, 0f, 1f);
        public void Complete()                => IsActive   = false;
        public void Abandon()                 => IsActive   = false;

        /// <summary>
        /// Returns true when this goal has expired or is no longer active.
        /// An ExpiresAt of 0 means the goal never expires by time (only by completion).
        /// </summary>
        public bool IsExpired(float currentTime)
        {
            if (!IsActive) return true;                        // completed/abandoned
            if (ExpiresAt > 0f && currentTime > ExpiresAt)    // timed out
                return true;
            return false;
        }

        public override string ToString() =>
            $"[Goal] {GoalType} | {Description} | P:{Priority:F2} | Progress:{Progress:P0} | {(IsActive ? "Active" : "Done")}";
    }
}
