using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// NPC flees from the most threatening perceived entity.
    /// Valid when: there is at least one Threat percept.
    /// Score: sigmoid on avgThreatLevel × neuroticismBias — threshold-like response.
    /// Trait modifiers: Brave lowers score, Coward raises it.
    /// Effect: NPC physically moves away from threat, stress and fear spike.
    /// </summary>
    public sealed class FleeAction : IAction
    {
        public string ActionId   => "flee";
        public string ActionType => "Flee";

        // Sigmoid tuned so score crosses 0.5 when threat × neuroticism ≈ 0.5
        private static readonly ICurve _curve = new SigmoidCurve(steepness: 8f, midpoint: 0.45f);

        // World-space distance the NPC runs per flee execution (world units)
        private const float FleeDistance = 12f;

        public bool IsValid(ActionContext ctx) => ctx.HasPercept("Threat");

        public float Evaluate(ActionContext ctx)
        {
            float totalThreat = 0f;
            int   count       = 0;

            foreach (var p in ctx.ActivePercepts)
            {
                if (!p.Tag.Equals("Threat", StringComparison.OrdinalIgnoreCase)) continue;
                totalThreat += p.ThreatLevel;
                count++;
            }

            if (count == 0) return 0f;

            float avg      = totalThreat / count;
            float neuro    = ctx.Self.Psychology.Neuroticism;
            float rawScore = avg * (0.5f + neuro * 0.5f);

            return _curve.Evaluate(rawScore);
        }

        public void Execute(ActionContext ctx)
        {
            var vitals = ctx.Self.Vitals;

            // Stress and fear spike when fleeing
            vitals.SetStress(Math.Min(1f, vitals.Stress + 0.15f));
            ctx.Self.Psychology.SetFear(Math.Min(1f, ctx.Self.Psychology.Fear + 0.20f));

            // Find the primary threat and move directly away from it
            PerceivedObject topThreat = ctx.GetTopPercept("Threat");
            if (topThreat != null)
            {
                SimVector3 diff    = ctx.Self.Position - topThreat.LastKnownPosition;
                SimVector3 awayDir = diff.Magnitude > 1e-4f
                    ? diff.Normalized()
                    : new SimVector3(ctx.Rng.NextFloat(-1f, 1f), 0f, ctx.Rng.NextFloat(-1f, 1f)).Normalized();

                SimVector3 newPos = ctx.Self.Position + awayDir * FleeDistance;

                // ISimWorld.MoveNPC updates NPC.Position and the spatial grid
                ctx.World?.MoveNPC(ctx.Self.Identity.NpcId, newPos);

                ctx.World?.PublishEvent(new SimEvent(
                    "FleeMovement",
                    ctx.Self.Identity.NpcId,
                    topThreat.ObjectId,
                    $"{ctx.Self.Identity.DisplayName} flees from {topThreat.ObjectId}.",
                    impact:    -0.6f,
                    timestamp: ctx.CurrentTime,
                    position:  ctx.Self.Position,
                    rng:       ctx.Rng,
                    category:  "combat"));
            }

            ctx.World?.PublishEvent(new SimEvent(
                ActionType,
                ctx.Self.Identity.NpcId,
                null,
                $"{ctx.Self.Identity.DisplayName} is fleeing!",
                impact:    -0.5f,
                timestamp: ctx.CurrentTime,
                position:  ctx.Self.Position,
                rng:       ctx.Rng,
                category:  "combat"));
        }
    }
}
