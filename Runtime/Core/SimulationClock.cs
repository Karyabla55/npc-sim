using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Deterministic simulation clock.
    /// The ONLY source of time in the simulation — no System.DateTime, no Unity Time.
    /// Advances via explicit <see cref="Tick"/> calls driven by the SimulationManager.
    /// </summary>
    public sealed class SimulationClock
    {
        // ─── Config ───────────────────────────────────────────────────────────────

        /// <summary>How many sim-seconds are in one in-game day.</summary>
        public float DayLengthSeconds { get; }

        /// <summary>Real-time to sim-time multiplier. 1 = real time, 60 = 1 min/sec.</summary>
        public float TimeScale        { get; private set; }

        // ─── State ────────────────────────────────────────────────────────────────

        /// <summary>Total elapsed simulation time in seconds.</summary>
        public float CurrentTime      { get; private set; }

        /// <summary>Current in-game hour in [0, 24).</summary>
        public float CurrentHour  => (CurrentTime % DayLengthSeconds) / DayLengthSeconds * 24f;

        /// <summary>How many full in-game days have elapsed.</summary>
        public int   CurrentDay   => (int)(CurrentTime / DayLengthSeconds);

        private bool _paused;

        // ─── Constructor ──────────────────────────────────────────────────────────

        public SimulationClock(float dayLengthSeconds = 1440f, float timeScale = 1f)
        {
            DayLengthSeconds = MathF.Max(1f, dayLengthSeconds);
            TimeScale        = MathF.Max(0f, timeScale);
        }

        // ─── Control ──────────────────────────────────────────────────────────────

        public void Pause()                     => _paused = true;
        public void Resume()                    => _paused = false;
        public void SetTimeScale(float scale)   => TimeScale = MathF.Max(0f, scale);

        // ─── Tick ─────────────────────────────────────────────────────────────────

        /// <summary>
        /// Advances the simulation clock by <paramref name="realDeltaTime"/> × <see cref="TimeScale"/>.
        /// Returns the actual sim-delta applied.
        /// </summary>
        public float Tick(float realDeltaTime)
        {
            if (_paused || realDeltaTime <= 0f) return 0f;
            float simDelta = realDeltaTime * TimeScale;
            CurrentTime += simDelta;
            return simDelta;
        }

        public override string ToString() =>
            $"[SimClock] t={CurrentTime:F2}s Day={CurrentDay} Hour={CurrentHour:F1} Scale={TimeScale}x {(_paused ? "PAUSED" : "")}";
    }
}
