# Island prison port checkpoint

Sources: pinned DDA c19e95bc96d27d8bef8e2e246a63cd4cd6f89974.
Target: pinned BN c621aaf42fa182473aad10feea2b55647704dcf1.
Inherited CC-BY-SA-3.0 and upstream credits apply.

This is review staging, not an installable mod. Run `python npc-content/prepare_island_prison.py` to reproduce it from checksummed sources.

The BN source tree has the ordinary prison, but no `npcs/island_prison` package and no `prison_island.json` or `prison_alcatraz.json`. Its faction definitions do not contain `prisoners`. Preserve the existing BN prison when adding this content.

This checkpoint preserves all three NPCs, eighteen topics and the leader's military-ID mission, fourteen mapgen definitions, four palettes and nine item groups. The DDA prisoners faction is selected from the upstream factions file.

46 constant string comparisons use BN variable conditions. The survival level >= 2 check uses BN's existing `u_has_skill`, whose pinned condition.cpp handler compares `get_skill_level(skill) >= level`. No new skill-expression engine is needed for this check. Original IDs and dialogue branches remain.

The mission stays verbatim because its bean reward explicitly requests `can_medium` as its container; the current native item bridge cannot represent this yet. Do not drop that option or substitute a loose food item. Remaining work includes the guard-patrol enum, faction schema and epilogues, dependency closure, overmap placement and native load/quest tests. Runtime validation and release readiness are false.
