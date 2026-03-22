using System;
using System.Collections.Generic;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Top-level simulation orchestrator. Pure C# — no MonoBehaviour.
    /// Wires together:
    ///   Clock → StimulusDispatcher → PerceptionSystem → NPC.Tick → DecisionSystem
    ///   + PopulationStats (aggregate tracking)
    ///   + FactionRegistry (inter-faction politics)
    ///   + NeedSystem (need → goal pipeline)
    ///
    /// Usage:
    ///   var manager = new SimulationManager(config);
    ///   manager.AddNPC(NPCFactory.CreateGuard(manager.Rng));
    ///   manager.ActionLibrary.Register(new EatAction());
    ///   // In Unity Update or headless loop:
    ///   manager.Tick(Time.deltaTime);
    /// </summary>
    public sealed class SimulationManager
    {
        // ─── Public surface ───────────────────────────────────────────────────────

        public SimulationClock    Clock           { get; }
        public SimWorldAdapter    World           { get; }
        public StimulusDispatcher Dispatcher      { get; }
        public ActionLibrary      ActionLibrary   { get; }
        public SimRng             Rng             { get; }
        public SimulationConfig   Config          { get; }
        public FactionRegistry    Factions        { get; }
        public PopulationStats    Stats           { get; }

        // Per-NPC systems — keyed by NpcId
        private readonly Dictionary<string, PerceptionSystem> _perceptionSystems = new();
        private readonly Dictionary<string, DecisionSystem>   _decisionSystems   = new();

        // Sorted NPC list for deterministic tick order
        private readonly List<NPC> _activeNPCs = new();
        private bool _dirty;   // rebuild sort when NPC list changes

        // ─── Constructor ──────────────────────────────────────────────────────────

        public SimulationManager(SimulationConfig config = null, ISpatialGrid grid = null)
        {
            Config        = config ?? new SimulationConfig();
            Rng           = new SimRng(Config.Seed);
            Clock         = new SimulationClock(Config.DayLengthSeconds, Config.InitialTimeScale);
            World         = new SimWorldAdapter(Clock, Config, grid);
            Dispatcher    = new StimulusDispatcher();
            ActionLibrary = new ActionLibrary();
            Factions      = new FactionRegistry();
            Stats         = new PopulationStats();
        }

        // ─── NPC Management ───────────────────────────────────────────────────────

        /// <summary>Adds an NPC to the simulation, wiring per-NPC systems.</summary>
        public void AddNPC(NPC npc)
        {
            if (npc == null) return;

            // Inject config so NPC.Tick uses the correct decay rates (D1 fix)
            npc.InjectConfig(Config);

            World.AddNPC(npc);
            _activeNPCs.Add(npc);

            // D7 fix: per-archetype sensor range
            var sensor = SensorRangePresets.ForArchetype(npc.Identity.PersonalityArchetype);
            var filter = new PerceptionFilter { AttentionThreshold = 0.2f };
            var perc   = new PerceptionSystem(sensor, filter)
            {
                PerceptTimeout = Config.PerceptTimeout
            };
            var eval = new UtilityEvaluator();
            var dec  = new DecisionSystem(ActionLibrary, eval);

            _perceptionSystems[npc.Identity.NpcId] = perc;
            _decisionSystems  [npc.Identity.NpcId] = dec;
            _dirty = true;
        }

        /// <summary>Removes an NPC by ID.</summary>
        public bool RemoveNPC(string npcId)
        {
            bool removed = World.RemoveNPC(npcId);
            if (removed)
            {
                _activeNPCs.RemoveAll(n => n.Identity.NpcId == npcId);
                _perceptionSystems.Remove(npcId);
                _decisionSystems.Remove(npcId);
                _dirty = true;
            }
            return removed;
        }

        /// <summary>
        /// Replaces the PerceptionSystem for an already-registered NPC with custom sensor
        /// and filter values. Used by <c>NPCSpawner</c> when a <c>SensorRangeProfileSO</c>
        /// overrides the archetype default.
        /// </summary>
        public void ReplacePerceptionSystem(string npcId, SensorRange sensor, PerceptionFilter filter)
        {
            if (!_perceptionSystems.ContainsKey(npcId)) return;
            var perc = new PerceptionSystem(sensor, filter)
            {
                PerceptTimeout = Config.PerceptTimeout
            };
            _perceptionSystems[npcId] = perc;
        }

        // ─── Clock Control ────────────────────────────────────────────────────────

        public void Pause()                   => Clock.Pause();
        public void Resume()                  => Clock.Resume();
        public void SetTimeScale(float scale) => Clock.SetTimeScale(scale);

        // ─── Main Tick ────────────────────────────────────────────────────────────

        /// <summary>
        /// Advances the simulation by one real-time frame.
        /// Should be called once per Update (Unity) or per loop iteration (headless).
        /// </summary>
        public void Tick(float realDeltaTime)
        {
            // 1. Advance simulation time
            float simDelta = Clock.Tick(realDeltaTime);
            if (simDelta <= 0f) return;

            float currentTime = Clock.CurrentTime;

            // 2. Drain stimulus queue → dispatch to nearby NPCs
            var stimuli = World.DrainStimuli();
            foreach (var s in stimuli)
            {
                Dispatcher.Dispatch(s, World, maxRadius: 60f);
            }

            // 3. Sort NPC list by ID for deterministic tick order
            if (_dirty)
            {
                _activeNPCs.Sort((a, b) =>
                    string.Compare(a.Identity.NpcId, b.Identity.NpcId, StringComparison.Ordinal));
                _dirty = false;
            }

            // 4. Per-NPC update
            var toRemove = new List<NPC>();

            foreach (var npc in _activeNPCs)
            {
                if (!npc.IsActive || !npc.Vitals.IsAlive)
                {
                    toRemove.Add(npc);
                    continue;
                }

                string id = npc.Identity.NpcId;

                // 4a. Drain stimuli buffered for this NPC by the dispatcher
                var npcStimuli = Dispatcher.DrainFor(id);

                // 4b. Perception tick — D7: forward direction from NPC
                var percSystem = _perceptionSystems[id];
                var changed    = percSystem.Tick(
                    npcStimuli, npc.Position, npc.Forward,
                    npc.Vitals, npc.Psychology, currentTime);

                // Route changed percepts → episodic memory / beliefs
                foreach (var percept in changed)
                {
                    if (percept.ThreatLevel > 0.1f)
                    {
                        var threatEvent = new SimEvent(
                            "ThreatPerceived", percept.ObjectId, id,
                            $"{npc.Identity.DisplayName} perceives threat from {percept.ObjectId}.",
                            impact:    -(percept.ThreatLevel),
                            timestamp: currentTime,
                            position:  npc.Position,
                            rng:       Rng,
                            category:  "combat");

                        npc.WitnessEvent(threatEvent,
                            new[] { percept.ObjectId, "World_Safety" },
                            currentTime);
                    }
                }

                // 4c. NPC vitals / decay tick (D1: uses config-injected rates)
                npc.Tick(simDelta, currentTime);

                // 4d. Need → Goal pipeline (converts urgent physiology to active goals)
                npc.RefreshNeedGoals(currentTime);

                // 4e. Decision tick (D5: ActionContext now exposes Goals)
                var decSystem = _decisionSystems[id];
                var ctx = new ActionContext(
                    npc,
                    percSystem.ActivePercepts,
                    currentTime,
                    simDelta,
                    World,
                    Rng,
                    Config.DayLengthSeconds);

                decSystem.Tick(ctx);

                // 4f. Update spatial grid if NPC moved
                World.UpdateNPCPosition(npc);
            }

            // 5. Remove dead / deactivated NPCs
            foreach (var npc in toRemove)
                RemoveNPC(npc.Identity.NpcId);

            // 6. Update aggregate population statistics
            Stats.Update(World.AllNPCs, World.EventLog);

            // 7. Faction disposition decay
            Factions.TickDecay(simDelta);
        }

        public override string ToString() =>
            $"[SimulationManager] {_activeNPCs.Count} NPC(s) | {Clock} | {Stats}";
    }
}
