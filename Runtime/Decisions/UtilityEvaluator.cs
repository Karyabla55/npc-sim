using System;

namespace ForgeProject.Sim
{
    // ─── Response Curves ──────────────────────────────────────────────────────────

    /// <summary>Transforms a raw input in [0,1] into a shaped output in [0,1].</summary>
    public interface ICurve
    {
        float Evaluate(float x);
    }

    /// <summary>Identity: output = input.</summary>
    public sealed class LinearCurve : ICurve
    {
        public float Evaluate(float x) => Math.Clamp(x, 0f, 1f);
    }

    /// <summary>Quadratic: output = x². Urgency builds slowly then spikes.</summary>
    public sealed class QuadraticCurve : ICurve
    {
        public float Evaluate(float x) => Math.Clamp(x * x, 0f, 1f);
    }

    /// <summary>Inverse quadratic: output = 1 - (1-x)². Diminishing returns.</summary>
    public sealed class InverseQuadraticCurve : ICurve
    {
        public float Evaluate(float x) { float v = 1f - x; return Math.Clamp(1f - v * v, 0f, 1f); }
    }

    /// <summary>
    /// Sigmoid: smooth S-curve centred on 0.5 with tunable steepness.
    /// Good for threshold-like behaviours (e.g. "flee once threat passes 0.6").
    /// </summary>
    public sealed class SigmoidCurve : ICurve
    {
        private readonly float _steepness;
        private readonly float _midpoint;

        public SigmoidCurve(float steepness = 10f, float midpoint = 0.5f)
        {
            _steepness = steepness;
            _midpoint  = midpoint;
        }

        public float Evaluate(float x)
        {
            float val = 1f / (1f + MathF.Exp(-_steepness * (x - _midpoint)));
            return Math.Clamp(val, 0f, 1f);
        }
    }

    // ─── Evaluator ────────────────────────────────────────────────────────────────

    /// <summary>
    /// Normalised utility evaluator.
    /// Delegates to <see cref="IAction.Evaluate"/> then applies:
    ///   1. An optional response curve to shape the raw score.
    ///   2. A trait-based weight modifier from <see cref="NPCTraits"/>.
    /// The result is always clamped to [0, 1].
    /// </summary>
    public sealed class UtilityEvaluator
    {
        /// <summary>Default curve applied when none is specified. Linear by default.</summary>
        public ICurve DefaultCurve { get; set; } = new LinearCurve();

        /// <summary>
        /// Evaluates an action in context and returns a final utility score in [0, 1].
        /// </summary>
        /// <param name="action">The action to evaluate.</param>
        /// <param name="ctx">Current decision context.</param>
        /// <param name="curve">Optional response curve. Falls back to <see cref="DefaultCurve"/>.</param>
        public float Evaluate(IAction action, ActionContext ctx, ICurve curve = null)
        {
            if (!action.IsValid(ctx)) return 0f;

            // Raw score from action
            float raw = Math.Clamp(action.Evaluate(ctx), 0f, 1f);

            // Shape with curve
            float shaped = (curve ?? DefaultCurve).Evaluate(raw);

            // Apply trait modifier (Brave reduces Flee, Greedy boosts Trade, etc.)
            float modifier = ctx.Self.Traits.GetWeightModifier(action.ActionType);

            return Math.Clamp(shaped * modifier, 0f, 1f);
        }
    }
}
