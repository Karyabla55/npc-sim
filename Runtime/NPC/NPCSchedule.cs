using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Defines an NPC's preferred daily activity schedule.
    /// Used by time-aware actions (WorkAction, RestAtHomeAction) to boost relevance during appropriate hours.
    /// Schedules are assigned at factory time based on the NPC's occupation.
    /// </summary>
    [Serializable]
    public class NPCSchedule
    {
        // ─── Hour windows ─────────────────────────────────────────────────────────

        /// <summary>Hour of day [0, 24) when the NPC prefers to start work.</summary>
        public float WorkStartHour  { get; private set; }

        /// <summary>Hour of day [0, 24) when the NPC prefers to stop work.</summary>
        public float WorkEndHour    { get; private set; }

        /// <summary>Hour of day [0, 24) when the NPC prefers to sleep.</summary>
        public float SleepStartHour { get; private set; }

        /// <summary>Hour of day [0, 24) when the NPC prefers to wake.</summary>
        public float WakeHour       { get; private set; }

        /// <summary>Hour of day [0, 24) when the NPC prefers to socialize.</summary>
        public float SocialHour     { get; private set; }

        // ─── Constructor ──────────────────────────────────────────────────────────
        public NPCSchedule(
            float workStart  = 8f,
            float workEnd    = 18f,
            float sleepStart = 22f,
            float wakeHour   = 7f,
            float socialHour = 19f)
        {
            WorkStartHour  = workStart;
            WorkEndHour    = workEnd;
            SleepStartHour = sleepStart;
            WakeHour       = wakeHour;
            SocialHour     = socialHour;
        }

        // ─── Archetype presets ────────────────────────────────────────────────────

        /// <summary>Returns a schedule appropriate for the given occupation string.</summary>
        public static NPCSchedule ForOccupation(string occupation) => occupation?.ToLowerInvariant() switch
        {
            "guard"    => new NPCSchedule(workStart: 6f,  workEnd: 14f, sleepStart: 21f, wakeHour: 5f,  socialHour: 16f),
            "merchant" => new NPCSchedule(workStart: 9f,  workEnd: 19f, sleepStart: 23f, wakeHour: 8f,  socialHour: 20f),
            "scholar"  => new NPCSchedule(workStart: 8f,  workEnd: 20f, sleepStart: 24f, wakeHour: 7f,  socialHour: 18f),
            "farmer"   => new NPCSchedule(workStart: 5f,  workEnd: 17f, sleepStart: 20f, wakeHour: 4f,  socialHour: 18f),
            "priest"   => new NPCSchedule(workStart: 7f,  workEnd: 13f, sleepStart: 21f, wakeHour: 5f,  socialHour: 14f),
            "civilian" => new NPCSchedule(workStart: 9f,  workEnd: 17f, sleepStart: 22f, wakeHour: 7f,  socialHour: 19f),
            _          => new NPCSchedule()
        };

        /// <summary>Returns a score [0,1] reflecting how much the given activity is preferred at this hour.</summary>
        public float PreferenceAt(string activity, float hour)
        {
            return activity.ToLowerInvariant() switch
            {
                "work"    => IsInWindow(hour, WorkStartHour,  WorkEndHour)    ? 1f : 0.1f,
                "sleep"   => IsInWindow(hour, SleepStartHour, WakeHour + 24f) ? 1f :
                             IsInWindow(hour, WakeHour,       WorkStartHour)  ? 0.3f : 0f,
                "social"  => MathF.Max(0f, 1f - MathF.Abs(hour - SocialHour) / 3f),
                _         => 0.5f
            };
        }

        private static bool IsInWindow(float hour, float start, float end)
        {
            // Wrap-around support for windows crossing midnight
            if (end > 24f)
                return hour >= start || hour < end - 24f;
            return hour >= start && hour < end;
        }

        public override string ToString() =>
            $"[Schedule] Work:{WorkStartHour:F0}-{WorkEndHour:F0}h Sleep:{SleepStartHour:F0}h Wake:{WakeHour:F0}h";
    }
}
