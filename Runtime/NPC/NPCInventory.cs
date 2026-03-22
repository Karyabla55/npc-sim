using System;
using System.Collections.Generic;

namespace ForgeProject.Sim
{
    /// <summary>
    /// NPC's personal inventory — a simple slot-based container for resource items.
    /// Consumed by WorkAction, GatherAction, EatAction, TradeAction, HealAction.
    /// </summary>
    [Serializable]
    public class NPCInventory
    {
        private readonly List<ItemStack> _stacks;
        private readonly int _capacity;

        /// <summary>Max distinct item types the NPC can carry.</summary>
        public int Capacity => _capacity;

        /// <summary>View of all item stacks currently held.</summary>
        public IReadOnlyList<ItemStack> Stacks => _stacks;

        public NPCInventory(int capacity = 10)
        {
            _capacity = Math.Max(1, capacity);
            _stacks   = new List<ItemStack>(_capacity);
        }

        // ─── Access ───────────────────────────────────────────────────────────────

        public int GetAmount(string itemId)
        {
            foreach (var stack in _stacks)
                if (stack.ItemId == itemId) return stack.Amount;
            return 0;
        }

        public bool Has(string itemId, int amount = 1) => GetAmount(itemId) >= amount;

        // ─── Mutation ─────────────────────────────────────────────────────────────

        /// <summary>Adds amount to an existing stack or creates a new one.</summary>
        public bool Add(string itemId, int amount = 1)
        {
            foreach (var stack in _stacks)
            {
                if (stack.ItemId == itemId) { stack.Add(amount); return true; }
            }
            if (_stacks.Count >= _capacity) return false; // No room
            _stacks.Add(new ItemStack(itemId, amount));
            return true;
        }

        /// <summary>Removes amount from a stack. Returns false if not enough.</summary>
        public bool Remove(string itemId, int amount = 1)
        {
            for (int i = 0; i < _stacks.Count; i++)
            {
                if (_stacks[i].ItemId != itemId) continue;
                if (_stacks[i].Amount < amount) return false;
                _stacks[i].Remove(amount);
                if (_stacks[i].Amount <= 0) _stacks.RemoveAt(i);
                return true;
            }
            return false;
        }

        /// <summary>Removes all stacks.</summary>
        public void Clear() => _stacks.Clear();

        // ─── Well-known item ID constants ─────────────────────────────────────────
        /// <summary>
        /// String constants for all built-in item types.
        /// Use these instead of raw strings to avoid typos.
        /// </summary>
        public static class ItemIds
        {
            public const string Food     = "food";
            public const string Water    = "water";
            public const string Medicine = "medicine";
            public const string Wood     = "wood";
            public const string Stone    = "stone";
            public const string Gold     = "gold";
            public const string Grain    = "grain";
            public const string Cloth    = "cloth";
            public const string Tools    = "tools";
            public const string Weapon   = "weapon";
        }

        public override string ToString() => $"[Inventory] {_stacks.Count}/{_capacity} stacks";
    }

    /// <summary>A quantity of a single item type.</summary>
    [Serializable]
    public class ItemStack
    {
        public string ItemId { get; }
        public int    Amount { get; private set; }

        public ItemStack(string itemId, int amount)
        {
            ItemId = itemId;
            Amount = Math.Max(0, amount);
        }

        public void Add(int n)    => Amount += Math.Max(0, n);
        public void Remove(int n) => Amount  = Math.Max(0, Amount - n);
        public override string ToString() => $"{ItemId}×{Amount}";
    }
}
