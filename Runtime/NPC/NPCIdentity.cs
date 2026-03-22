using System;

namespace ForgeProject.Sim
{
    /// <summary>
    /// NPC'nin kalıcı kimlik bilgilerini (isim, yaş, meslek, kişilik tipi) tutar.
    /// </summary>
    [Serializable]
    public class NPCIdentity
    {
        // ─── Temel Kimlik ─────────────────────────────────────────────────────────
        public string NpcId       { get; private set; }
        public string DisplayName { get; private set; }
        public int    Age         { get; private set; }
        public string Gender      { get; private set; }

        // ─── Sosyal Statü ─────────────────────────────────────────────────────────
        /// <summary>Meslek veya toplumsal rol (ör. "Smith", "Guard", "Merchant").</summary>
        public string Occupation  { get; private set; }

        /// <summary>Fraksiyon / grup üyeliği (ör. "NorthernClan", "MerchantGuild").</summary>
        public string Faction     { get; private set; }

        // ─── Kişilik Tipi ─────────────────────────────────────────────────────────
        /// <summary>
        /// Kişilik arketipi (ör. "Hero", "Coward", "Scholar", "Merchant").
        /// Karar sistemleri bu değeri kullanarak davranış ağırlıklarını belirler.
        /// </summary>
        public string PersonalityArchetype { get; private set; }

        // ─── Oluşturucu ───────────────────────────────────────────────────────────
        public NPCIdentity(
            string npcId,
            string displayName,
            int    age,
            string gender                = "Unknown",
            string occupation            = "Civilian",
            string faction               = "None",
            string personalityArchetype  = "Generic")
        {
            NpcId                = npcId;
            DisplayName          = displayName;
            Age                  = Math.Max(0, age);
            Gender               = gender;
            Occupation           = occupation;
            Faction              = faction;
            PersonalityArchetype = personalityArchetype;
        }

        public override string ToString() =>
            $"[Identity] {DisplayName} (ID:{NpcId}) | Age:{Age} | {Gender} | {Occupation} @ {Faction} | Archetype:{PersonalityArchetype}";
    }
}
