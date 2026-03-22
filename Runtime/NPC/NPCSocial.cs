using System;
using System.Collections.Generic;

namespace ForgeProject.Sim
{
    /// <summary>
    /// Manages social relationships, reputation, and group standing for an NPC.
    /// Relations decay over time via <see cref="TickDecay"/> (D4 fix).
    /// </summary>
    [Serializable]
    public class NPCSocial
    {
        // ─── Relations ────────────────────────────────────────────────────────────
        /// <summary>Key = targetNpcId. Value = Relation object.</summary>
        public IReadOnlyDictionary<string, Relation> Relations => _relations;
        private readonly Dictionary<string, Relation> _relations = new();

        // ─── Reputation ───────────────────────────────────────────────────────────
        /// <summary>General social reputation [0, 1]. 0 = disliked, 1 = highly respected.</summary>
        public float Reputation    { get; private set; }

        /// <summary>Standing within the NPC's faction/group [0, 1].</summary>
        public float GroupStanding { get; private set; }

        // ─── Constructor ──────────────────────────────────────────────────────────
        public NPCSocial(float initialReputation = 0.5f, float initialGroupStanding = 0.5f)
        {
            Reputation    = Math.Clamp(initialReputation,    0f, 1f);
            GroupStanding = Math.Clamp(initialGroupStanding, 0f, 1f);
        }

        // ─── Relation operations ──────────────────────────────────────────────────

        /// <summary>Returns or creates the relation with the target NPC.</summary>
        public Relation GetOrCreateRelation(string ownerId, string targetId)
        {
            if (!_relations.TryGetValue(targetId, out Relation relation))
            {
                relation = new Relation(ownerId, targetId);
                _relations[targetId] = relation;
            }
            return relation;
        }

        /// <summary>Returns the relation to a specific NPC, or null.</summary>
        public Relation GetRelation(string targetId) =>
            _relations.TryGetValue(targetId, out Relation rel) ? rel : null;

        /// <summary>Returns all relations of a given type label (e.g. "Friend", "Enemy").</summary>
        public List<Relation> GetRelationsByType(string type)
        {
            var result = new List<Relation>();
            foreach (var rel in _relations.Values)
                if (rel.RelationType == type) result.Add(rel);
            return result;
        }

        // ─── Reputation ───────────────────────────────────────────────────────────
        public void ModifyReputation(float delta) =>
            Reputation = Math.Clamp(Reputation + delta, 0f, 1f);

        public void ModifyGroupStanding(float delta) =>
            GroupStanding = Math.Clamp(GroupStanding + delta, 0f, 1f);

        // ─── Relation time-decay (D4 fix) ─────────────────────────────────────────

        /// <summary>
        /// Drifts all relations toward neutral over time — friendships fade without contact.
        /// Call once per sim-second from <see cref="NPC.Tick"/>.
        /// </summary>
        public void TickDecay(float deltaTime, float decayRate = 0.00005f)
        {
            foreach (var rel in _relations.Values)
                rel.DecayOverTime(deltaTime, decayRate);
        }

        public override string ToString() =>
            $"[Social] Relations:{_relations.Count} | Rep:{Reputation:P0} | Group:{GroupStanding:P0}";
    }
}
