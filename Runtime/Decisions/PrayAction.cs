using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// NPC prays, medidates, or performs a spiritual ritual.
    ///
    /// Valid: NPC has "Spiritual" or "Devout" trait, or stress > 0.6.
    ///        Not valid under imminent threat.
    /// Score: Stress level × (Openness + Agreeableness) / 2 × trait bonus.
    /// Effect: stress drops, happiness rises, fear reduces.
    ///         Social "Pray" event may attract other spiritual NPCs.
    /// </summary>
    public sealed class PrayAction : IAction
    {
        public string ActionId   => "pray";
        public string ActionType => "Pray";

        public bool IsValid(ActionContext ctx)
        {
            if (ctx.HasPercept("Threat")) return false;
            return ctx.Self.Traits.Has("Spiritual") ||
                   ctx.Self.Traits.Has("Devout")    ||
                   ctx.Self.Vitals.Stress > 0.55f;
        }

        public float Evaluate(ActionContext ctx)
        {
            float stress      = ctx.Self.Vitals.Stress;
            float openness    = ctx.Self.Psychology.Openness;
            float agreeable   = ctx.Self.Psychology.Agreeableness;
            float traitBonus  = (ctx.Self.Traits.Has("Spiritual") || ctx.Self.Traits.Has("Devout"))
                                ? 1.5f : 1f;
            float goalBoost   = ctx.HasGoal(GoalType.Pray) ? 1.2f : 1f;

            float base_score  = stress * ((openness + agreeable) / 2f) * traitBonus;
            return Math.Clamp(base_score * goalBoost, 0f, 1f);
        }

        public void Execute(ActionContext ctx)
        {
            // Stress relief (primary effect)
            float stressRelief = 0.05f + ctx.Self.Psychology.Openness * 0.05f;
            ctx.Self.Vitals.SetStress(Math.Max(0f, ctx.Self.Vitals.Stress - stressRelief * ctx.DeltaTime * 3f));

            // Happiness boost
            float happyBoost = 0.03f * ctx.Self.Psychology.Agreeableness;
            ctx.Self.Psychology.SetHappiness(ctx.Self.Psychology.Happiness + happyBoost);

            // Fear reduction
            ctx.Self.Psychology.SetFear(Math.Max(0f, ctx.Self.Psychology.Fear - 0.02f));

            // Reputation boost in community
            ctx.Self.Social.ModifyReputation(0.001f);
            foreach (var g in ctx.Goals.GetByType(GoalType.Pray)) g.SetProgress(g.Progress + 0.1f);

            // Emit a social stimulus that other Spiritual NPCs can perceive
            ctx.World?.PublishStimulus(new Stimulus(
                StimulusType.Social,
                ctx.Self.Identity.NpcId,
                ctx.Self.Position,
                intensity:  0.4f,
                timestamp:  ctx.CurrentTime,
                tag:        "Prayer"));

            ctx.World?.PublishEvent(new SimEvent(
                "Pray",
                ctx.Self.Identity.NpcId,
                null,
                $"{ctx.Self.Identity.DisplayName} prays.",
                impact:    0.1f,
                timestamp: ctx.CurrentTime,
                position:  ctx.Self.Position,
                rng:       ctx.Rng,
                category:  "spiritual"));
        }
    }
}
