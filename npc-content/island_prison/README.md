# Island prison port checkpoint

Sources: pinned DDA c19e95bc96d27d8bef8e2e246a63cd4cd6f89974.
Target: pinned BN c621aaf42fa182473aad10feea2b55647704dcf1.
Inherited CC-BY-SA-3.0 and upstream credits apply.

This is review staging, not an installable mod. Run `python npc-content/prepare_island_prison.py` to reproduce it from checksummed sources.

The BN source tree has the ordinary prison, but no `npcs/island_prison` package and no `prison_island.json` or `prison_alcatraz.json`. Its faction definitions do not contain `prisoners`. Preserve the existing BN prison when adding this content.

This checkpoint preserves all three NPCs, eighteen topics and the leader's military-ID mission, fourteen mapgen definitions, four palettes and nine item groups. The DDA prisoners faction is selected from the upstream factions file.

46 constant string comparisons use BN variable conditions. The survival level >= 2 check uses BN's existing `u_has_skill`, whose pinned condition.cpp handler compares `get_skill_level(skill) >= level`. No new skill-expression engine is needed for this check. Original IDs and dialogue branches remain.

The military-ID mission reward now uses the native item bridge with its explicit can_medium container. The implementation follows pinned DDA receive_item: one container receives one item with the requested charge count, then i_add_or_drop gives the filled container to the player. Both IDs were verified in pinned BN JSON. A native regression test checks the actual container and its beans, not merely the inventory count. Windows validation is pending.

NPC mission modes use the pinned BN npc.h enum: SHOPKEEP = 3 and GUARD_PATROL = 8. This also corrects the earlier artisan adapter value, which incorrectly selected a guard mode for traders.

Remaining work includes faction schema and epilogues, dependency closure, overmap placement and native load/quest tests. Runtime validation and release readiness remain false.

Placement checkpoint: both original special layouts are preserved, including the prisoners camp cell. Staging expands 86 island/alcatraz terrain IDs without replacing the ordinary BN prison. All 86 have mapgen entries; unique coordinates and both prisoner epilogue references pass static checks. Run check_prison_placement.py to reproduce. Native lake placement, camp ownership and faction nutrition remain pending; staging is not loadable stock BN faction data.
