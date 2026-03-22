namespace ForgeProject.Sim
{
    /// <summary>
    /// Contract for all NPC actions in the utility AI system.
    /// Every action is stateless — all context arrives via <see cref="ActionContext"/>.
    /// This makes actions independently testable and thread-safe to read.
    /// </summary>
    public interface IAction
    {
        /// <summary>Unique identifier for this action instance.</summary>
        string ActionId { get; }

        /// <summary>
        /// Semantic category label (e.g. "Eat", "Sleep", "Flee", "Attack", "Trade").
        /// Used by <see cref="NPCTraits.GetWeightModifier"/> and debugging.
        /// </summary>
        string ActionType { get; }

        /// <summary>
        /// Returns true when all preconditions for this action are met.
        /// Called before <see cref="Evaluate"/> to avoid wasting evaluation budget.
        /// </summary>
        bool IsValid(ActionContext ctx);

        /// <summary>
        /// Returns a normalised utility score [0, 1].
        /// Higher = more desirable for this NPC given the current context.
        /// Must NOT have side-effects.
        /// </summary>
        float Evaluate(ActionContext ctx);

        /// <summary>
        /// Commits the action: mutates NPC state and/or publishes a <see cref="SimEvent"/>.
        /// Called only after <see cref="IsValid"/> and <see cref="Evaluate"/>
        /// confirm selection.
        /// </summary>
        void Execute(ActionContext ctx);
    }
}
