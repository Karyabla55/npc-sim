using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// NPC exchanges goods with a Merchant percept (trade interaction).
    ///
    /// Valid: a "Merchant" percept is present, NPC has gold, not fleeing.
    /// Score: Agreeableness × (1 if Trade goal active) × urgency.
    ///        Merchants socre 1.5× because TradeAction is their primary behaviour.
    /// Effect: NPC spends gold, gains food/goods; both NPCs gain trust.
    ///         Merchant gains gold. Trade event published.
    /// </summary>
    public sealed class TradeAction : IAction
    {
        public string ActionId   => "trade";
        public string ActionType => "Trade";

        public bool IsValid(ActionContext ctx)
        {
            if (ctx.HasPercept("Threat")) return false;
            if (!ctx.HasPercept("Merchant")) return false;
            // Need gold to buy, or someone has to be selling
            return ctx.Self.Inventory.Has(NPCInventory.ItemIds.Gold, 1)
                || ctx.Self.Identity.Occupation?.ToLowerInvariant() == "merchant";
        }

        public float Evaluate(ActionContext ctx)
        {
            float agreeableness = ctx.Self.Psychology.Agreeableness;
            float goalBoost     = ctx.HasGoal(GoalType.Trade) ? 1.4f : 1f;

            // Merchants are much more trade-motivated
            float occupationBoost = ctx.Self.Identity.Occupation?.ToLowerInvariant() == "merchant" ? 1.5f : 1f;
            // Hunger adds urgency (buying food)
            float hungerUrgency  = ctx.Self.Vitals.Hunger * 0.3f;

            return Math.Clamp((agreeableness + hungerUrgency) * goalBoost * occupationBoost, 0f, 1f);
        }

        public void Execute(ActionContext ctx)
        {
            var merchantPercept = ctx.GetTopPercept("Merchant");
            if (merchantPercept == null) return;

            var merchantNPC = ctx.World?.GetNPCById(merchantPercept.ObjectId);

            // Simple transaction: buyer pays 1 gold, receives 1 food
            bool buyerHasGold  = ctx.Self.Inventory.Has(NPCInventory.ItemIds.Gold);
            bool merchantHasFood = merchantNPC?.Inventory.Has(NPCInventory.ItemIds.Food) ?? false;

            if (buyerHasGold && merchantHasFood)
            {
                ctx.Self.Inventory.Remove(NPCInventory.ItemIds.Gold, 1);
                ctx.Self.Inventory.Add(NPCInventory.ItemIds.Food, 1);
                merchantNPC.Inventory.Remove(NPCInventory.ItemIds.Food, 1);
                merchantNPC.Inventory.Add(NPCInventory.ItemIds.Gold, 1);

                // Reduce hunger immediately
                ctx.Self.Vitals.SetHunger(Math.Max(0f, ctx.Self.Vitals.Hunger - 0.3f));

                // Both NPCs gain trust from the interaction
                ctx.Self.Interact(merchantNPC, 0.03f, 0.02f, 0.01f, ctx.CurrentTime);
                merchantNPC.Interact(ctx.World?.GetNPCById(ctx.Self.Identity.NpcId), 0.02f, 0.01f, 0.02f, ctx.CurrentTime);

                merchantNPC.Social.ModifyReputation(0.003f);
                foreach (var g in ctx.Goals.GetByType(GoalType.Trade)) g.SetProgress(1f);

                ctx.World?.PublishEvent(new SimEvent(
                    "Trade",
                    ctx.Self.Identity.NpcId,
                    merchantPercept.ObjectId,
                    $"{ctx.Self.Identity.DisplayName} buys food from {merchantPercept.ObjectId}.",
                    impact:    0.2f,
                    timestamp: ctx.CurrentTime,
                    position:  ctx.Self.Position,
                    rng:       ctx.Rng,
                    category:  "economy"));
            }
        }
    }
}
