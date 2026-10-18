# Optional eldercare population tables

The three DDA groups now live in `data/mods/Civilians/dda_eldercare_groups.json`, loaded only with `civilians`. No existing Civilians group, evolution table, Lua rule or monster statistic changes. The whole nursing-home and retirement-community sites remain uninstalled.

| DDA type | Existing BN mod counterpart | Deliberate difference |
|---|---|---|
| mon_civilian_police_rifle | mon_civilian_police | Same officer role; stock Glock, baton, ammunition, loot and evolution replace the rifle loadout. |
| mon_civilian_zombiegunner | mon_civilian_survivor_pistol | Existing armed survivor fighting zombies; stock stronger survivor profile and evolution retained. No last-stand dialogue is grafted onto its different personality. |

Both are optional-mod providers, never core aliases. There are no new monster definitions. The exact-ID core/all-bundled-mod catalogs and the archived Civilians definitions were checked before choosing these counterparts.

## Narrow exact group compilation

The pinned graph has one subgroup level and exactly one subgroup draw per parent selection. The child total is 266, nursing-home total 103, retirement-community total 105. Expand each child leaf with weight `10 * child_weight`, multiply direct parent weights by 266, and set totals to 27398 and 27930. Preserve every leaf pack size, time window and cost multiplier. Convert source days to BN integer hours; BN applies its own evolution option when loading. This is equivalence at equal effective elapsed time, not a promise that differently configured engine evolution options have identical calendars.

The pinned DDA recursive selector does **not** use the subgroup's default on an empty recursive result: the root supplies its own default, with pack size one and budget cost one. Leaving the corresponding probability mass unallocated in the BN table preserves this behavior. Never redistribute it among surviving child entries. Standalone GROUP_CIVILIANS_STANDARD still uses its own default (panic), even after the timed leaves expire; this follows DDA, rather than inventing complete civilian disappearance.

`check_eldercare_groups.py` independently compares the recursive source law with enumeration of every BN integer RNG roll. It checks 48 exact Fraction-valued distributions over monster identity, pack size and budget cost: before/at/after 8, 12, 16 and 24 days, plus initial and late time. The compiler rejects subgroup packs, added conditions, unknown fields, deeper nesting or changed parent shapes instead of generalizing incorrectly. It does not port DDA's vector-returning `use_pack_size` API; the supported scope is the ordinary map population selection represented by BN's existing result API.

Native tests cover optional presence/absence, loaded weights, counterparts, late fallback and budget decrement. Windows source and installed test results remain pending. Static closure is not full mapgen compatibility. Before enabling these sites, audit actual mapgen schemas and Civilians Lua's NPC_TERRAINS exclusions so explicit source populations do not stack with ambient civilian spawning.
