using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// NPC works at their occupation, generating food/gold/resources over time.
    ///
    /// Valid: during work hours, energy not critically low, no threats.
    /// Score: Conscientiousness × work-hour schedule preference × urgency from Work goal.
    /// Effect: adds income item to inventory; small energy cost; reputation boost over time.
    /// </summary>
    public sealed class WorkAction : IAction
    {
        public string ActionId   => "work";
        public string ActionType => "Work";

        // Work produces different items based on occupation
        private static string OutputItem(string occupation) => occupation?.ToLowerInvariant() switch
        {
            "farmer"   => NPCInventory.ItemIds.Grain,
            "merchant" => NPCInventory.ItemIds.Gold,
            "guard"    => NPCInventory.ItemIds.Gold,     // wage
            "scholar"  => NPCInventory.ItemIds.Gold,     // stipend
            "priest"   => NPCInventory.ItemIds.Gold,     // donation
            _          => NPCInventory.ItemIds.Gold
        };

        public bool IsValid(ActionContext ctx)
        {
            if (ctx.HasPercept("Threat"))        return false;
            if (ctx.Self.Vitals.Energy < 0.15f)  return false;
            // Only valid during scheduled work hours
            float schedPref = ctx.Self.Schedule.PreferenceAt("work", ctx.SimDayHour);
            return schedPref > 0.3f;
        }

        public float Evaluate(ActionContext ctx)
        {
            float conscientious = ctx.Self.Psychology.Conscientiousness;
            float schedPref     = ctx.Self.Schedule.PreferenceAt("work", ctx.SimDayHour);
            float goalBoost     = ctx.HasGoal(GoalType.Work) ? 1.25f : 1f;

            return Math.Clamp(conscientious * schedPref * goalBoost, 0f, 1f);
        }

        public void Execute(ActionContext ctx)
        {
            // Drain energy (work is tiring)
            float energyCost = 2f * ctx.DeltaTime;
            ctx.Self.Vitals.ConsumeEnergy(energyCost);

            // Generate output (scaled by Conscientiousness)
            // One "unit" of work per real-time second, at full Conscientiousness
            float workRate = ctx.Self.Psychology.Conscientiousness;
            if (ctx.Rng.Chance(workRate * ctx.DeltaTime * 0.5f))
            {
                string item = OutputItem(ctx.Self.Identity.Occupation);
                ctx.Self.Inventory.Add(item, 1);

                // Happiness bump from productive work
                ctx.Self.Psychology.SetHappiness(
                    ctx.Self.Psychology.Happiness + 0.02f * workRate);
                ctx.Self.Social.ModifyReputation(0.001f);

                ctx.World?.PublishEvent(new SimEvent(
                    "Work",
                    ctx.Self.Identity.NpcId,
                    null,
                    $"{ctx.Self.Identity.DisplayName} works and earns {item}.",
                    impact:    0.1f,
                    timestamp: ctx.CurrentTime,
                    position:  ctx.Self.Position,
                    rng:       ctx.Rng,
                    category:  "economy"));
            }

            // Update Work goal progress
            foreach (var g in ctx.Goals.GetByType(GoalType.Work))
                g.SetProgress(g.Progress + 0.05f);
        }
    }
}
