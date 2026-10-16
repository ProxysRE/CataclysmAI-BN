# Remaining work in the started DDA port

Snapshot: 2026-10-17. Prepared JSON is not the same as a playable port. No progress
percentage is assigned to work that has not passed runtime validation.

| Area | Already implemented or prepared | Still required |
|---|---|---|
| Shared dialogue layer | Expressions, player/NPC/world variables, world save support, NPC opinion, conditional immediate EOC expansion, item payments/rewards, elapsed time, chance conditions; real/integer random math added | Current Windows regression; delayed and recurring EOC lifecycle; context variables and numeric input; several activity types; full field/schema checks |
| Lighthouse | Four NPC templates, seven linked missions, encounter in existing BN dock variants, map updates, native quest lifecycle tests | Current native regression, manual whole-chain walkthrough, natural encounter generation, cross-stage save/reload, playable packaging |
| Isolated Road: Cody and Jay | Adapted topics and artisan service foundations, native payment/reward/time handling, quest dependency graph for exhibition items | Full BN dependency and schema closure, actual exhibition placement, whole mission/service testing and package installation |
| Island prison | Three NPCs, dialogue and mission data, two placement layouts, prisoner epilogues | Camp/ownership/food behavior required by this package, native loader and mission tests, generation and save checks |
| Hub/robofac, Godco, campus, militia, bunker merchant, chemist, lumbermill employees, scrap trader | Eight staged groups: 73 NPC definitions and 102 mission definitions within 1,767 selected definitions | 66 currently blocked definitions; unsupported fields may remain beyond those blockers; item/monster/palette dependencies; merge overlapping BN definitions; load and test each coherent package |
| Existing BN sites | Six special IDs identified as merge targets; complete BN special catalog checked; chemist replacement generated preserving all other BN map data | Other five sites and remaining map variants; reconcile layouts and NPC positions; trade-zone consumers; native install and map generation validation |
| New site candidates | Eight linked layouts identified for further comparison | Complete BN map index and dependency checks before adding; supported mapgen schemas; placement and world-generation tests |
| Windows delivery | Dedicated native build and fast content CI | Passing current native tests and assembling a playable archive; staged bulk data is not installed automatically |

The 66 blocked definitions include 36 EOC declarations requiring lifecycle review.
They are not 66 independent engine features or 66 broken NPCs. Some immediate EOC
effects are already inlined safely; delayed/recurring execution remains separate.
Zero adaptation blockers in a group does not establish runtime compatibility.

The chemist replacement changes the chair and NPC placement representation only.
It does not complete the four chemist quests or the shop zones. No second special,
second mapgen variant or extra chemist is added.

Full camp creation/construction/work assignments and the pocket system have not
been implemented. Faction stock serialization is groundwork, not a restored camp.
The standalone paranormal church and emergency settlement examples still need exact
source identification and comparison. Highway work remains in its separate branch;
this NPC snapshot does not certify highway visual fixes or combine the two builds.

Next priorities: native regression, shared event/activity compatibility, coherent
existing-location/NPC merges, then broader placement and playable packaging.
