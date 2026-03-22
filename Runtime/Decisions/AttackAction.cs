using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// NPC attacks a perceived threat when provoked.
    ///
    /// Valid: Threat percept present AND (NPC has Aggressive trait OR Anger > 0.7).
    ///        Never valid for Pacifist trait.
    /// Score: inverse of Flee score — high Aggressiveness + low Neuroticism → attack.
    ///        Uses NPCTraits.GetWeightModifier("Attack") for trait adjustments.
    /// Effect: generates Combat event with negative impact; stress spikes; anger drains.
    /// </summary>
    public sealed class AttackAction : IAction
    {
        public string ActionId   => "attack";
        public string ActionType => "Attack";

        public bool IsValid(ActionContext ctx)
        {
            if (!ctx.HasPercept("Threat")) return false;
            if (ctx.Self.Traits.Has("Pacifist")) return false;
            return ctx.Self.Traits.Has("Aggressive") || ctx.Self.Psychology.Anger > 0.65f;
        }

        public float Evaluate(ActionContext ctx)
        {
            float anger        = ctx.Self.Psychology.Anger;
            float bravery      = 1f - ctx.Self.Psychology.Neuroticism;
            float traitMod     = ctx.Self.Traits.GetWeightModifier(ActionType);
            float goalBoost    = ctx.HasGoal(GoalType.Attack) ? 1.3f : 1f;

            // Attack is more appealing when angry, brave, and provoked
            float raw = ((anger + bravery) / 2f) * traitMod * goalBoost;
            return Math.Clamp(raw, 0f, 1f);
        }

        public void Execute(ActionContext ctx)
        {
            var threat = ctx.GetTopPercept("Threat");
            if (threat == null) return;

            // Stress spike; anger drains (it was spent)
            ctx.Self.Vitals.SetStress(Math.Min(1f, ctx.Self.Vitals.Stress + 0.1f));
            ctx.Self.Psychology.SetAnger(Math.Max(0f, ctx.Self.Psychology.Anger - 0.2f));

            // Damage to target NPC (if reachable within melee range)
            float meleeDist = 3f;
            float sqrDist   = SimVector3.SqrDistance(ctx.Self.Position, threat.LastKnownPosition);
            if (sqrDist <= meleeDist * meleeDist)
            {
                var targetNPC = ctx.World?.GetNPCById(threat.ObjectId);
                if (targetNPC != null)
                {
                    float damage = 10f + ctx.Rng.NextFloat(-3f, 3f);
                    targetNPC.Vitals.ApplyDamage(damage);

                    // Victim witnesses attack
                    var attackEvent = new SimEvent("Combat",
                        ctx.Self.Identity.NpcId, threat.ObjectId,
                        $"{ctx.Self.Identity.DisplayName} attacks {threat.ObjectId} for {damage:F0} damage!",
                        impact: -0.8f, timestamp: ctx.CurrentTime,
                        position: ctx.Self.Position, rng: ctx.Rng, category: "combat");

                    targetNPC.WitnessEvent(attackEvent,
                        new[] { ctx.Self.Identity.NpcId, "World_Safety" }, ctx.CurrentTime);

                    ctx.World?.PublishEvent(attackEvent);

                    // Attacker's reputation drops
                    ctx.Self.Social.ModifyReputation(-0.05f);
                    targetNPC.Social.ModifyReputation(0.02f); // victim sympathy
                }
            }
            else
            {
                // Out of range — move toward threat
                SimVector3 dir    = (threat.LastKnownPosition - ctx.Self.Position).Normalized();
                SimVector3 newPos = ctx.Self.Position + dir * 4f * ctx.DeltaTime;
                ctx.World?.MoveNPC(ctx.Self.Identity.NpcId, newPos);
            }

            ctx.World?.PublishEvent(new SimEvent(
                "AttackAttempt",
                ctx.Self.Identity.NpcId, threat.ObjectId,
                $"{ctx.Self.Identity.DisplayName} attempts to attack {threat.ObjectId}.",
                impact: -0.6f, timestamp: ctx.CurrentTime,
                position: ctx.Self.Position, rng: ctx.Rng, category: "combat"));
        }
    }
}
