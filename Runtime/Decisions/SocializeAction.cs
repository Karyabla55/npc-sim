using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// NPC engages in conversation with a nearby ally.
    ///
    /// Valid: ally percept visible, not starving, no imminent threat.
    /// Score: Extraversion × social-hour schedule preference × 1.2 if Socialize goal active.
    /// Effect: Both NPCs gain Trust/Affinity. Beliefs are partially "gossiped" to the listener.
    ///         RepuNation increases modestly.
    /// </summary>
    public sealed class SocializeAction : IAction
    {
        public string ActionId   => "socialize";
        public string ActionType => "Socialize";

        public bool IsValid(ActionContext ctx)
        {
            if (ctx.HasPercept("Threat"))   return false;
            if (ctx.Self.Vitals.Hunger > 0.80f) return false;
            return ctx.HasPercept("Ally");
        }

        public float Evaluate(ActionContext ctx)
        {
            float extraversion = ctx.Self.Psychology.Extraversion;
            float schedPref    = ctx.Self.Schedule.PreferenceAt("social", ctx.SimDayHour);
            float goalBoost    = ctx.HasGoal(GoalType.Socialize) ? 1.3f : 1f;

            return Math.Clamp(extraversion * schedPref * goalBoost, 0f, 1f);
        }

        public void Execute(ActionContext ctx)
        {
            var ally = ctx.GetTopPercept("Ally");
            if (ally == null) return;

            // Update this NPC's relation to the ally
            var relation = ctx.Self.Social.GetOrCreateRelation(ctx.Self.Identity.NpcId, ally.ObjectId);
            relation.ApplyInteraction(0.02f, 0.03f, 0.01f, ctx.CurrentTime);

            // Happiness boost from social contact (Extraversion-scaled)
            float happyBoost = 0.05f * ctx.Self.Psychology.Extraversion;
            ctx.Self.Psychology.SetHappiness(ctx.Self.Psychology.Happiness + happyBoost);

            // Gossip: attempt to update the ally's beliefs from this NPC's memory
            // (requires world access to retrieve the other NPC object)
            var allyNPC = ctx.World?.GetNPCById(ally.ObjectId);
            if (allyNPC != null)
            {
                // Reciprocal relation update
                var reciprocal = allyNPC.Social.GetOrCreateRelation(ally.ObjectId, ctx.Self.Identity.NpcId);
                float allyAgree = allyNPC.Psychology.Agreeableness;
                reciprocal.ApplyInteraction(0.01f * allyAgree, 0.02f * allyAgree, 0.01f, ctx.CurrentTime);

                // Gossip: share the NPC's most salient memory with the ally
                var salientMemory = ctx.Self.Memory.GetMostSalient();
                if (salientMemory != null)
                {
                    allyNPC.Memory.Remember(salientMemory.Event, salientMemory.EmotionalWeight * 0.4f, ctx.CurrentTime);
                }
            }

            // Reputation bump from being seen socializing
            ctx.Self.Social.ModifyReputation(0.002f);

            // Complete any Socialize goal
            foreach (var g in ctx.Goals.GetByType(GoalType.Socialize))
                g.SetProgress(1f);

            ctx.World?.PublishEvent(new SimEvent(
                "Socialize",
                ctx.Self.Identity.NpcId,
                ally.ObjectId,
                $"{ctx.Self.Identity.DisplayName} socializes with {ally.ObjectId}.",
                impact:    0.15f,
                timestamp: ctx.CurrentTime,
                position:  ctx.Self.Position,
                rng:       ctx.Rng,
                category:  "social"));
        }
    }
}
