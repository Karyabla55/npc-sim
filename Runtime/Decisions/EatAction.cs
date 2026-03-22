using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// NPC eats food to reduce hunger.
    ///
    /// Valid: Hunger above threshold AND (food percept visible OR food in inventory).
    /// Score: quadratic on Hunger — urgency spikes fast as the NPC approaches starvation.
    /// Effect: Hunger reduced significantly; small energy restore; happiness boost.
    ///         Consumes one unit of food from inventory if available; otherwise uses the percept.
    /// </summary>
    public sealed class EatAction : IAction
    {
        public string ActionId   => "eat";
        public string ActionType => "Eat";

        private const float HungerThreshold  = 0.35f;
        private const float HungerReduction  = 0.55f;
        private const float EnergyGainFrac   = 0.08f;   // fraction of MaxEnergy
        private const float HappinessGain    = 0.08f;   // B10 fix

        public bool IsValid(ActionContext ctx)
        {
            if (ctx.Self.Vitals.Hunger < HungerThreshold) return false;
            // B7 fix: can eat from inventory OR from a food percept
            return ctx.Self.Inventory.Has(NPCInventory.ItemIds.Food)
                || ctx.HasPercept("Food");
        }

        public float Evaluate(ActionContext ctx)
        {
            float h = ctx.Self.Vitals.Hunger;
            return h * h;   // quadratic urgency
        }

        public void Execute(ActionContext ctx)
        {
            var vitals    = ctx.Self.Vitals;
            var psych     = ctx.Self.Psychology;

            // B7 fix: consume from inventory first
            bool ateFromInventory = ctx.Self.Inventory.Remove(NPCInventory.ItemIds.Food, 1);

            vitals.SetHunger(Math.Max(0f, vitals.Hunger - HungerReduction));
            vitals.RestoreEnergy(EnergyGainFrac * vitals.MaxEnergy);

            // B10 fix: eating is pleasurable — boost happiness
            psych.SetHappiness(Math.Min(1f, psych.Happiness + HappinessGain));

            // Complete any FindFood goals
            foreach (var g in ctx.Goals.GetByType(GoalType.FindFood))
                g.SetProgress(1f);

            string src = ateFromInventory ? "from pack" : "from ground";
            ctx.World?.PublishEvent(new SimEvent(
                ActionType,
                ctx.Self.Identity.NpcId,
                null,
                $"{ctx.Self.Identity.DisplayName} eats {src}.",
                impact:    0.2f,
                timestamp: ctx.CurrentTime,
                position:  ctx.Self.Position,
                rng:       ctx.Rng,
                category:  "health"));
        }
    }
}
