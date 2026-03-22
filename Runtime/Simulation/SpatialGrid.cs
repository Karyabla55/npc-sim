using System;
using System.Collections.Generic;

namespace ForgeProject.Sim
{
    // ─── Spatial Partition Abstraction ────────────────────────────────────────────

    /// <summary>
    /// Abstracts the spatial indexing strategy so <see cref="StimulusDispatcher"/>
    /// and <see cref="SimWorldAdapter"/> remain decoupled from the partition algorithm.
    /// Swap in a quad-tree or Unity NativeArray grid without touching dispatch logic.
    /// </summary>
    public interface ISpatialGrid
    {
        void Insert(NPC npc);
        void Remove(NPC npc);
        void Update(NPC npc);
        void Clear();
        IReadOnlyList<NPC> QueryRadius(SimVector3 center, float radius);
    }

    /// <summary>
    /// Default spatial grid: dictionary-bucketed uniform grid.
    /// O(1) insert/remove, O(k) radius query where k = NPCs in candidate cells.
    /// Good for dense urban placement. Cell size should be ≥ max sensor radius.
    /// </summary>
    public sealed class DictionaryGrid : ISpatialGrid
    {
        private readonly float _cellSize;
        private readonly Dictionary<long, List<NPC>> _cells = new();
        private readonly Dictionary<string, (int cx, int cy)> _index  = new();

        public DictionaryGrid(float cellSize = 50f)
        {
            _cellSize = MathF.Max(1f, cellSize);
        }

        public void Insert(NPC npc)
        {
            var (cx, cy) = Cell(npc.Position);
            GetOrCreate(cx, cy).Add(npc);
            _index[npc.Identity.NpcId] = (cx, cy);
        }

        public void Remove(NPC npc)
        {
            if (!_index.TryGetValue(npc.Identity.NpcId, out var cell)) return;
            var key = Key(cell.cx, cell.cy);
            if (_cells.TryGetValue(key, out var list)) list.Remove(npc);
            _index.Remove(npc.Identity.NpcId);
        }

        public void Update(NPC npc)
        {
            if (_index.TryGetValue(npc.Identity.NpcId, out var old))
            {
                var (ncx, ncy) = Cell(npc.Position);
                if (ncx == old.cx && ncy == old.cy) return;  // same cell, skip
                var oldKey = Key(old.cx, old.cy);
                if (_cells.TryGetValue(oldKey, out var list)) list.Remove(npc);
            }
            Insert(npc);
        }

        public void Clear() { _cells.Clear(); _index.Clear(); }

        public IReadOnlyList<NPC> QueryRadius(SimVector3 center, float radius)
        {
            int cellR = (int)MathF.Ceiling(radius / _cellSize);
            var (cx, cy) = Cell(center);
            var result   = new List<NPC>();
            float sqrR   = radius * radius;

            for (int dx = -cellR; dx <= cellR; dx++)
            for (int dy = -cellR; dy <= cellR; dy++)
            {
                var key = Key(cx + dx, cy + dy);
                if (!_cells.TryGetValue(key, out var bucket)) continue;
                foreach (var npc in bucket)
                    if (SimVector3.SqrDistance(center, npc.Position) <= sqrR)
                        result.Add(npc);
            }
            return result;
        }

        private (int cx, int cy) Cell(SimVector3 pos)
            => ((int)MathF.Floor(pos.X / _cellSize), (int)MathF.Floor(pos.Z / _cellSize));

        private List<NPC> GetOrCreate(int cx, int cy)
        {
            var key = Key(cx, cy);
            if (!_cells.TryGetValue(key, out var list))
                _cells[key] = list = new List<NPC>();
            return list;
        }

        private static long Key(int x, int y) => ((long)x << 32) | (uint)y;
    }
}
