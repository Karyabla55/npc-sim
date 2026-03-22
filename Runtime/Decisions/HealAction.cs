using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// NPC uses medicine from their inventory to restore health.
    ///
    /// Valid: health below 0.6 AND medicine in inventory.
    /// Score: inverse-quadratic health deficit × (1.5 if Heal goal active).
    ///        Higher urgency when health is critically low.
    /// Effect: restores health; consumes medicine item.
    /// </summary>
    public sealed class HealAction : IAction
    {
        public string ActionId   => "heal";
        public string ActionType => "Heal";

        private static readonly ICurve _curve = new InverseQuadraticCurve();

        public bool IsValid(ActionContext ctx) =>
            ctx.Self.Vitals.Health < 0.6f &&
            ctx.Self.Inventory.Has(NPCInventory.ItemIds.Medicine, 1);

        public float Evaluate(ActionContext ctx)
        {
            float healthDeficit = 1f - ctx.Self.Vitals.Health;
            float base_score    = _curve.Evaluate(healthDeficit);
            float goalBoost     = ctx.HasGoal(GoalType.Heal) ? 1.5f : 1f;
            return Math.Clamp(base_score * goalBoost, 0f, 1f);
        }

        public void Execute(ActionContext ctx)
        {
            ctx.Self.Inventory.Remove(NPCInventory.ItemIds.Medicine, 1);
            float healAmount = 30f + ctx.Rng.NextFloat(-5f, 10f);
            ctx.Self.Vitals.Heal(healAmount);
            ctx.Self.Psychology.SetFear(Math.Max(0f, ctx.Self.Psychology.Fear - 0.1f));

            foreach (var g in ctx.Goals.GetByType(GoalType.Heal)) g.SetProgress(1f);

            ctx.World?.PublishEvent(new SimEvent(
                "Heal",
                ctx.Self.Identity.NpcId,
                null,
                $"{ctx.Self.Identity.DisplayName} uses medicine and heals {healAmount:F0} HP.",
                impact:    0.4f,
                timestamp: ctx.CurrentTime,
                position:  ctx.Self.Position,
                rng:       ctx.Rng,
                category:  "health"));
        }
    }
}
