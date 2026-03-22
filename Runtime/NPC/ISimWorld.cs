using System.Collections.Generic;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Read-only world interface used by actions and systems.
    /// Decouples all domain logic from the concrete <see cref="SimWorldAdapter"/>,
    /// making every system independently mockable for unit testing.
    /// </summary>
    public interface ISimWorld
    {
        /// <summary>Current simulation time in seconds.</summary>
        float CurrentTime { get; }

        /// <summary>
        /// Returns all NPCs whose <see cref="NPC.Position"/> is within
        /// <paramref name="radius"/> units of <paramref name="center"/>.
        /// Implementations should use a spatial partition for efficiency.
        /// </summary>
        IReadOnlyList<NPC> GetNPCsInRadius(SimVector3 center, float radius);

        /// <summary>Returns the NPC with the given ID, or null if not found.</summary>
        NPC GetNPCById(string npcId);

        /// <summary>
        /// Teleports the NPC to <paramref name="destination"/> and refreshes the spatial grid.
        /// Called by movement actions (FleeAction, WalkToAction) to actually move NPCs.
        /// </summary>
        void MoveNPC(string npcId, SimVector3 destination);

        /// <summary>
        /// Enqueues a stimulus for dispatch this tick.
        /// The <see cref="StimulusDispatcher"/> routes it to nearby NPCs.
        /// </summary>
        void PublishStimulus(Stimulus stimulus);

        /// <summary>
        /// Records a simulation event in the world event log.
        /// Subscribers (UI, logging, replay) can listen to these events.
        /// </summary>
        void PublishEvent(SimEvent simEvent);
    }
}
