# RPG1 Improvement Plan

## Phase 1: Gameplay Depth (The "RPG" Feel)
Focus: Making combat and progression satisfying.

- [ ] **Loot 2.0 (Rarity & Affixes):**
    - Items currently have fixed stats.
    - **Goal:** Generate items with prefixes/suffixes.
    - Example: `Sharp Iron Sword` (+2 Atk) or `Vampiric Bow` (Heal on hit).
    - Add color coding: Grey (Common), Blue (Rare), Purple (Epic), Gold (Legendary).

- [ ] **Active Skills System:**
    - Currently, different classes just use different ranges.
    - **Goal:** Add an `ActiveSkills` component.
    - **UI:** Add a Mana/Energy bar.
    - **Mechanic:** Press `1`, `2`, `3` to cast spells (Healing, Fireball, Dash).

- [ ] **Stat Allocation:**
    - Currently, stats auto-increase.
    - **Goal:** Grant 5 "Stat Points" on level up.
    - Allow player to open a menu and spend points on `Strength` (Melee/HP), `Dexterity` (Dist/Speed), `Intelligence` (Magic/Mana).

## Phase 2: World & Content (The "Giant Map")
Focus: Filling the 2000x2000 world with things to do.

- [ ] **Points of Interest (POIs):**
    - The Perlin noise generates terrain, but it needs structures.
    - **Goal:** Procedurally place "Ruins", "Shrines" (Heal/Buff), and "Monster Camps" (High density mobs with a chest) in the wilderness.

- [ ] **Multi-Level Dungeons:**
    - **Goal:** When entering a Dungeon area, allow descending stairs (`>`) to generate a new, harder map level (Z-axis).
    - Level 5 of a dungeon contains a Boss.

- [ ] **Day/Night Cycle:**
    - **Goal:** Track global turns. Every 1000 turns, cycle day/night.
    - **Effect:** Reduce view radius at night. Spawn dangerous "Night Terrors" (Ghosts/Zombies).

## Phase 3: User Experience (UI/UX)
Focus: Making the game easier to understand and play.

- [ ] **Mini-Map:**
    - The world is too big to remember.
    - **Goal:** Add a small UI panel showing a 5x5 pixel representation of nearby chunks (Green for forest, Grey for town, Red for dungeon).

- [ ] **Detailed Character Sheet:**
    - Press `C` to see detailed stats (Crit chance, Regen rate, Elemental resists).

## Phase 4: Technical Architecture
Focus: Stability and Modularity.

- [ ] **Save System Overhaul:**
    - `pickle` breaks if code changes classes.
    - **Goal:** Serialize game state to JSON. This allows players to edit saves and prevents version crashes.

- [ ] **Input Configuration:**
    - Move keybindings to `config.json` so users can remap keys easily (e.g., for different keyboard layouts).

## Immediate Next Steps (Recommended)
1.  **Implement Loot Rarity:** It instantly makes killing mobs more rewarding.
2.  **Add a Mini-Map:** Essential for the new 2000x2000 world.
3.  **Add a simple Quest:** "Kill 5 Goblins" given by the Guard.
