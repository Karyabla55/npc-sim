using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// NPC navigates to a named world destination.
    ///
    /// Valid: no immediate threat, NPC has somewhere to go (percept with "Place" tag, or a GoHome goal).
    /// Score: base 0.3 + goal urgency boost if a GoHome/Work/Explore goal is active.
    /// Effect: teleports NPC.Position toward destination (sim-space only; Unity bridge
    ///         picks up the position change and drives the NavMesh agent).
    /// </summary>
    public sealed class WalkToAction : IAction
    {
        private readonly string     _placeId;
        private readonly SimVector3 _destination;
        private readonly string     _reasonGoalType;  // which goal this walk serves

        public string ActionId   => $"walkto_{_placeId}";
        public string ActionType => "Walk";

        /// <param name="placeId">The WorldRegistry key used for event descriptions.</param>
        /// <param name="destination">Sim-space position to move toward.</param>
        /// <param name="reasonGoalType">If the NPC has this goal, the walk score is boosted.</param>
        public WalkToAction(string placeId, SimVector3 destination, string reasonGoalType = "")
        {
            _placeId        = placeId;
            _destination    = destination;
            _reasonGoalType = reasonGoalType;
        }

        public bool IsValid(ActionContext ctx)
        {
            // Don't walk when fleeing
            if (ctx.HasPercept("Threat")) return false;
            // Don't walk to current location
            return SimVector3.SqrDistance(ctx.Self.Position, _destination) > 1f;
        }

        public float Evaluate(ActionContext ctx)
        {
            float base_score = 0.3f;

            // Boost if this walk serves an active goal
            if (!string.IsNullOrEmpty(_reasonGoalType) && ctx.HasGoal(_reasonGoalType))
            {
                var goal = ctx.GetTopGoalOfType(_reasonGoalType);
                base_score += goal?.Priority * 0.5f ?? 0f;
            }

            return Math.Clamp(base_score, 0f, 1f);
        }

        public void Execute(ActionContext ctx)
        {
            // Move toward destination by a step proportional to speed
            float speed      = 5f; // world units per second
            SimVector3 diff  = _destination - ctx.Self.Position;
            float dist       = diff.Magnitude;
            float step       = Math.Min(dist, speed * ctx.DeltaTime);
            SimVector3 newPos = dist > 0.01f
                ? ctx.Self.Position + diff.Normalized() * step
                : _destination;

            ctx.World?.MoveNPC(ctx.Self.Identity.NpcId, newPos);

            if (dist <= step + 0.5f)
            {
                // Arrived — complete any matching goal
                foreach (var g in ctx.Goals.GetByType(_reasonGoalType))
                    g.SetProgress(1f);

                ctx.World?.PublishEvent(new SimEvent(
                    "Arrived",
                    ctx.Self.Identity.NpcId,
                    _placeId,
                    $"{ctx.Self.Identity.DisplayName} arrived at {_placeId}.",
                    impact: 0.05f,
                    timestamp: ctx.CurrentTime,
                    position: ctx.Self.Position,
                    rng: ctx.Rng));
            }
        }
    }
}
