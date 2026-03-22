using System;
using System.Collections.Generic;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Tracks the disposition matrix between named factions.
    /// Disposition is symmetric by default but can be made asymmetric.
    ///
    /// NPC actions modify faction standing when NPCs interact across faction lines.
    /// The PerceptionFilter can use faction disposition to boost/reduce salience of
    /// stimuli from known hostile factions.
    /// </summary>
    public sealed class FactionRegistry
    {
        // disposition[A][B] = how faction A feels about faction B. Range [-1, 1].
        private readonly Dictionary<string, Dictionary<string, float>> _disposition = new();

        // ─── Registration ─────────────────────────────────────────────────────────

        /// <summary>Registers a new faction with neutral stance toward all others.</summary>
        public void RegisterFaction(string factionId)
        {
            if (_disposition.ContainsKey(factionId)) return;
            _disposition[factionId] = new Dictionary<string, float>();
        }

        // ─── Get / Set ────────────────────────────────────────────────────────────

        /// <summary>Returns how faction A feels about faction B. 0 if unknown.</summary>
        public float GetDisposition(string factionA, string factionB)
        {
            if (factionA == factionB) return 1f; // self-regard
            if (_disposition.TryGetValue(factionA, out var row)
                && row.TryGetValue(factionB, out float val)) return val;
            return 0f;
        }

        /// <summary>Sets the one-directional disposition from A toward B.</summary>
        public void SetDisposition(string factionA, string factionB, float value)
        {
            value = Math.Clamp(value, -1f, 1f);
            EnsureFaction(factionA);
            EnsureFaction(factionB);
            _disposition[factionA][factionB] = value;
        }

        /// <summary>Sets symmetric disposition between A and B.</summary>
        public void SetMutualDisposition(string factionA, string factionB, float value)
        {
            SetDisposition(factionA, factionB, value);
            SetDisposition(factionB, factionA, value);
        }

        /// <summary>Applies a delta to the disposition from A toward B.</summary>
        public void ModifyDisposition(string factionA, string factionB, float delta)
        {
            float current = GetDisposition(factionA, factionB);
            SetDisposition(factionA, factionB, current + delta);
        }

        // ─── Query helpers ────────────────────────────────────────────────────────

        /// <summary>Returns all faction IDs registered.</summary>
        public IEnumerable<string> AllFactions => _disposition.Keys;

        /// <summary>Returns true if two factions are effectively hostile (disposition &lt; -0.5).</summary>
        public bool AreHostile(string a, string b) => GetDisposition(a, b) < -0.5f;

        /// <summary>Returns true if two factions are effectively allied (disposition &gt; 0.5).</summary>
        public bool AreAllied(string a, string b)  => GetDisposition(a, b) > 0.5f;

        // ─── Decay over time ──────────────────────────────────────────────────────

        /// <summary>Drifts all dispositions toward 0 (neutrality) over time.</summary>
        public void TickDecay(float deltaTime, float rate = 0.0001f)
        {
            foreach (var row in _disposition.Values)
            {
                foreach (var key in new List<string>(row.Keys))
                {
                    float v = row[key];
                    if (v > 0f) row[key] = Math.Max(0f, v - rate * deltaTime);
                    else if (v < 0f) row[key] = Math.Min(0f, v + rate * deltaTime);
                }
            }
        }

        private void EnsureFaction(string id)
        {
            if (!_disposition.ContainsKey(id)) _disposition[id] = new Dictionary<string, float>();
        }

        public override string ToString() => $"[FactionRegistry] {_disposition.Count} factions";
    }
}
