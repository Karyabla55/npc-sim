using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// NPC rests to recover energy.
    /// Valid when: Energy below threshold AND no active threats.
    /// Score: inverse-quadratic on (1 - Energy) — urgent at zero, tapering near threshold.
    /// Effect: Energy restored over time; NPC is temporarily vulnerable.
    /// </summary>
    public sealed class SleepAction : IAction
    {
        public string ActionId   => "sleep";
        public string ActionType => "Sleep";

        private const float EnergyThreshold  = 0.30f;
        private const float EnergyRestoreRate = 0.40f;  // fraction of MaxEnergy per execution

        public bool IsValid(ActionContext ctx)
            => ctx.Self.Vitals.Energy / ctx.Self.Vitals.MaxEnergy < EnergyThreshold
            && !ctx.HasPercept("Threat");   // don't sleep when threatened

        public float Evaluate(ActionContext ctx)
        {
            float depleted = 1f - ctx.Self.Vitals.Energy / ctx.Self.Vitals.MaxEnergy;
            // Squash: urgent when fully depleted, tapering off as energy recovers
            float v = 1f - depleted;
            return Math.Clamp(1f - v * v, 0f, 1f);
        }

        public void Execute(ActionContext ctx)
        {
            var vitals = ctx.Self.Vitals;
            vitals.RestoreEnergy(EnergyRestoreRate * ctx.DeltaTime * vitals.MaxEnergy);

            ctx.World?.PublishEvent(new SimEvent(
                ActionType,
                ctx.Self.Identity.NpcId,
                null,
                $"{ctx.Self.Identity.DisplayName} rests.",
                impact:    0.0f,
                timestamp: ctx.CurrentTime,
                position:  ctx.Self.Position,
                rng:       ctx.Rng));
        }
    }
}
