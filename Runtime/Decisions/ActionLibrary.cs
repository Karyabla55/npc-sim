using System;
using System.Collections.Generic;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Registry of all <see cref="IAction"/> implementations available to the simulation.
    /// Populated at startup; read-only during simulation ticks for thread safety.
    /// </summary>
    public sealed class ActionLibrary
    {
        private readonly List<IAction> _actions = new();

        // ─── Registration ─────────────────────────────────────────────────────────

        /// <summary>Registers an action. Duplicate ActionIds are ignored.</summary>
        public void Register(IAction action)
        {
            if (action == null) return;
            foreach (var a in _actions)
                if (a.ActionId == action.ActionId) return;
            _actions.Add(action);
        }

        // ─── Queries ──────────────────────────────────────────────────────────────

        /// <summary>All registered actions.</summary>
        public IReadOnlyList<IAction> GetAll() => _actions;

        /// <summary>Actions matching the given <see cref="IAction.ActionType"/>.</summary>
        public List<IAction> GetByType(string actionType)
        {
            var result = new List<IAction>();
            foreach (var a in _actions)
                if (a.ActionType.Equals(actionType, StringComparison.OrdinalIgnoreCase))
                    result.Add(a);
            return result;
        }

        public override string ToString() => $"[ActionLibrary] {_actions.Count} action(s)";
    }
}
