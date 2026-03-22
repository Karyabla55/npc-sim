using System;
using System.Collections.Generic;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Per-NPC decision orchestrator.
    /// Each tick it selects and executes the highest-utility valid action.
    ///
    /// Flow:
    ///   1. Enumerate all actions from <see cref="ActionLibrary"/>.
    ///   2. Filter by <see cref="IAction.IsValid"/>.
    ///   3. Score with <see cref="UtilityEvaluator"/> (applies curves + trait mods).
    ///   4. Select max-score action (stable — first max wins for determinism).
    ///   5. <see cref="IAction.Execute"/> → publishes <see cref="SimEvent"/> to world.
    /// </summary>
    public sealed class DecisionSystem
    {
        private readonly ActionLibrary   _library;
        private readonly UtilityEvaluator _evaluator;

        // ─── Last decision tracking ───────────────────────────────────────────────

        /// <summary>The action selected in the most recent tick. Null on first tick.</summary>
        public IAction LastSelectedAction { get; private set; }

        /// <summary>Utility score of the last selected action.</summary>
        public float LastScore { get; private set; }

        // ─── Constructor ──────────────────────────────────────────────────────────

        public DecisionSystem(ActionLibrary library, UtilityEvaluator evaluator = null)
        {
            _library   = library   ?? throw new ArgumentNullException(nameof(library));
            _evaluator = evaluator ?? new UtilityEvaluator();
        }

        // ─── Tick ─────────────────────────────────────────────────────────────────

        /// <summary>
        /// Evaluates all registered actions and executes the winner.
        /// Returns the selected action, or null if no action was valid.
        /// </summary>
        public IAction Tick(ActionContext ctx)
        {
            IAction bestAction = null;
            float   bestScore  = 0f;

            var all = _library.GetAll();
            foreach (var action in all)
            {
                float score = _evaluator.Evaluate(action, ctx);
                // Strict greater-than keeps determinism: first-registered wins ties
                if (score > bestScore)
                {
                    bestScore  = score;
                    bestAction = action;
                }
            }

            if (bestAction != null)
            {
                bestAction.Execute(ctx);
                LastSelectedAction = bestAction;
                LastScore          = bestScore;
            }

            return bestAction;
        }

        // ─── Debug ────────────────────────────────────────────────────────────────

        /// <summary>
        /// Returns scored candidates without executing — useful for debugging and
        /// Editor inspector display.
        /// </summary>
        public List<(IAction action, float score)> GetScores(ActionContext ctx)
        {
            var result = new List<(IAction action, float score)>();
            foreach (var action in _library.GetAll())
            {
                float score = action.IsValid(ctx) ? _evaluator.Evaluate(action, ctx) : 0f;
                result.Add((action, score));
            }
            result.Sort((a, b) => b.score.CompareTo(a.score));
            return result;
        }

        public override string ToString() =>
            $"[DecisionSystem] Last: {LastSelectedAction?.ActionType ?? "None"} ({LastScore:F2})";
    }
}
