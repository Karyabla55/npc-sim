using System;
using System.Collections.Generic;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Concrete implementation of <see cref="ISimWorld"/>.
    /// Holds the live NPC registry and the spatial grid.
    /// Maintains a ring-buffer event log for replay / debugging.
    /// </summary>
    public sealed class SimWorldAdapter : ISimWorld
    {
        // ─── Time ─────────────────────────────────────────────────────────────────
        public float CurrentTime => _clock.CurrentTime;
        private readonly SimulationClock _clock;

        // ─── NPC registry ─────────────────────────────────────────────────────────
        private readonly List<NPC>        _npcs = new();
        private readonly ISpatialGrid     _grid;

        public IReadOnlyList<NPC> AllNPCs => _npcs;

        // ─── Stimulus queue ───────────────────────────────────────────────────────
        private readonly Queue<Stimulus>  _stimulusQueue;
        private readonly int              _stimulusQueueCap;

        public IReadOnlyCollection<Stimulus> PendingStimuli => _stimulusQueue;

        // ─── Event log (ring buffer via Queue) ────────────────────────────────────
        private readonly Queue<SimEvent>  _eventLog;
        private readonly int              _eventLogCap;

        public IReadOnlyCollection<SimEvent> EventLog => _eventLog;

        // ─── Event hook ───────────────────────────────────────────────────────────
        /// <summary>Raised whenever a <see cref="SimEvent"/> is published.</summary>
        public event Action<SimEvent> OnEventPublished;

        // ─── Constructor ──────────────────────────────────────────────────────────

        public SimWorldAdapter(SimulationClock clock, SimulationConfig config, ISpatialGrid grid = null)
        {
            _clock            = clock  ?? throw new ArgumentNullException(nameof(clock));
            _grid             = grid   ?? new DictionaryGrid(config?.SpatialGridCellSize ?? 50f);
            _stimulusQueueCap = config?.StimulusQueueSize ?? 1024;
            _stimulusQueue    = new Queue<Stimulus>(_stimulusQueueCap);
            _eventLogCap      = 2000;
            _eventLog         = new Queue<SimEvent>(_eventLogCap);
        }

        // ─── ISimWorld ────────────────────────────────────────────────────────────

        public IReadOnlyList<NPC> GetNPCsInRadius(SimVector3 center, float radius)
            => _grid.QueryRadius(center, radius);

        public void PublishStimulus(Stimulus stimulus)
        {
            if (stimulus == null) return;
            if (_stimulusQueue.Count >= _stimulusQueueCap)
                _stimulusQueue.Dequeue();   // drop oldest when full
            _stimulusQueue.Enqueue(stimulus);
        }

        public void PublishEvent(SimEvent simEvent)
        {
            if (simEvent == null) return;
            if (_eventLog.Count >= _eventLogCap)
                _eventLog.Dequeue();        // O(1) ring behaviour
            _eventLog.Enqueue(simEvent);
            OnEventPublished?.Invoke(simEvent);
        }

        // ─── NPC management ───────────────────────────────────────────────────────

        public void AddNPC(NPC npc)
        {
            if (npc == null || _npcs.Contains(npc)) return;
            _npcs.Add(npc);
            _grid.Insert(npc);
        }

        public bool RemoveNPC(string npcId)
        {
            int idx = _npcs.FindIndex(n => n.Identity.NpcId == npcId);
            if (idx < 0) return false;
            _grid.Remove(_npcs[idx]);
            _npcs.RemoveAt(idx);
            return true;
        }

        /// <summary>Returns the NPC with the given ID, or null.</summary>
        public NPC GetNPCById(string npcId)
        {
            foreach (var npc in _npcs)
                if (npc.Identity.NpcId == npcId) return npc;
            return null;
        }

        /// <summary>
        /// Directly sets the NPC's sim-space position and updates the spatial grid.
        /// Called by actions (FleeAction, WalkToAction) when the NPC moves.
        /// </summary>
        public void MoveNPC(string npcId, SimVector3 destination)
        {
            var npc = GetNPCById(npcId);
            if (npc == null) return;
            npc.Position = destination;
            _grid.Update(npc);
        }

        /// <summary>
        /// Notify the spatial grid that an NPC's position changed.
        /// Call this after any movement action executes.
        /// </summary>
        public void UpdateNPCPosition(NPC npc) => _grid.Update(npc);

        // ─── Stimulus drain ───────────────────────────────────────────────────────

        // Re-used swap buffer for DrainStimuli — avoids ToArray() allocation each tick.
        private List<Stimulus> _drainBuffer = new();

        /// <summary>
        /// Dequeues all pending stimuli into a reusable buffer and returns it.
        /// Caller must NOT hold a reference across ticks — the buffer is reused.
        /// </summary>
        public IReadOnlyList<Stimulus> DrainStimuli()
        {
            if (_stimulusQueue.Count == 0) return Array.Empty<Stimulus>();

            // Swap: fill a fresh list while we reclaim the previous one
            var result   = _drainBuffer;
            _drainBuffer = new List<Stimulus>(result.Capacity);     // fresh for next tick

            while (_stimulusQueue.Count > 0)
                result.Add(_stimulusQueue.Dequeue());

            return result;
        }

        public override string ToString() =>
            $"[SimWorld] NPCs:{_npcs.Count} Events:{_eventLog.Count} Stimuli:{_stimulusQueue.Count}";
    }
}
