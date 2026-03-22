using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// NPC harvests resources from a nearby resource node or food source.
    ///
    /// Valid when: a "Food", "Water", or "Resource" percept is visible.
    /// Score: urgency-weighted (hunger/thirst drives Gather when needs are high).
    ///        Openness boosts exploration-style gathering.
    /// Effect: adds harvested item to inventory; partially relieves hunger/thirst.
    /// </summary>
    public sealed class GatherAction : IAction
    {
        public string ActionId   => "gather";
        public string ActionType => "Gather";

        public bool IsValid(ActionContext ctx)
        {
            if (ctx.HasPercept("Threat")) return false;
            return ctx.HasPercept("Food") || ctx.HasPercept("Water") || ctx.HasPercept("Resource");
        }

        public float Evaluate(ActionContext ctx)
        {
            float hunger  = ctx.Self.Vitals.Hunger;
            float thirst  = ctx.Self.Vitals.Thirst;
            float openness= ctx.Self.Psychology.Openness;

            // Urgent need → aggressive score
            float needScore  = Math.Max(hunger, thirst);
            float curiosity  = openness * 0.3f;  // curious NPCs gather even when not hungry
            float goalBoost  = (ctx.HasGoal(GoalType.FindFood) || ctx.HasGoal(GoalType.FindWater)) ? 1.3f : 1f;

            return Math.Clamp((needScore + curiosity) * goalBoost, 0f, 1f);
        }

        public void Execute(ActionContext ctx)
        {
            // Prioritize food/water based on current need
            bool gatherFood  = ctx.HasPercept("Food")  && ctx.Self.Vitals.Hunger >= ctx.Self.Vitals.Thirst;
            bool gatherWater = ctx.HasPercept("Water") && !gatherFood;

            string gathered = gatherFood  ? NPCInventory.ItemIds.Food  :
                              gatherWater ? NPCInventory.ItemIds.Water  :
                                           NPCInventory.ItemIds.Wood;  // generic resource fallback

            // Add to inventory
            ctx.Self.Inventory.Add(gathered, 1);

            // Immediate need relief
            if (gatherFood)
            {
                ctx.Self.Vitals.SetHunger(Math.Max(0f, ctx.Self.Vitals.Hunger - 0.25f));
                foreach (var g in ctx.Goals.GetByType(GoalType.FindFood)) g.SetProgress(1f);
            }
            else if (gatherWater)
            {
                ctx.Self.Vitals.SetThirst(Math.Max(0f, ctx.Self.Vitals.Thirst - 0.30f));
                foreach (var g in ctx.Goals.GetByType(GoalType.FindWater)) g.SetProgress(1f);
            }

            // Energy cost of gathering
            ctx.Self.Vitals.ConsumeEnergy(0.5f * ctx.DeltaTime);

            ctx.World?.PublishEvent(new SimEvent(
                "Gather",
                ctx.Self.Identity.NpcId,
                null,
                $"{ctx.Self.Identity.DisplayName} gathers {gathered}.",
                impact:   0.15f,
                timestamp: ctx.CurrentTime,
                position:  ctx.Self.Position,
                rng:       ctx.Rng,
                category:  "resource"));
        }
    }
}
