# Remaining work in the started DDA port

Snapshot: 2026-10-17. Prepared JSON is not the same as a playable port. No progress
percentage is assigned to work that has not passed runtime validation.

| Area | Already implemented or prepared | Still required |
|---|---|---|
| Shared dialogue layer | Expressions, player/NPC/world variables, world save support, NPC opinion, conditional immediate EOC expansion, item payments/rewards, elapsed time, chance conditions; real/integer random math added | Current Windows regression; delayed and recurring EOC lifecycle; context variables and numeric input; several activity types; full field/schema checks |
| Lighthouse | Four NPC templates, seven linked missions, encounter in existing BN dock variants, map updates, native quest lifecycle tests | Current native regression, manual whole-chain walkthrough, natural encounter generation, cross-stage save/reload, playable packaging |
| Isolated Road: Cody and Jay | Adapted topics and artisan service foundations, native payment/reward/time handling, expanded quest dependency graph for exhibition items, with casing native slice pending validation | Full BN dependency and schema closure, actual exhibition placement, whole mission/service testing and package installation |
| Island prison | Three NPCs, dialogue and mission data, two placement layouts, prisoner epilogues | Camp/ownership/food behavior required by this package, native loader and mission tests, generation and save checks |
| Hub/robofac, Godco, campus, militia, bunker merchant, chemist, lumbermill employees, scrap trader | Eight staged groups: 73 NPC definitions and 102 mission definitions within 1,767 selected definitions | 63 currently blocked definitions; unsupported fields may remain beyond those blockers; item/monster/palette dependencies; merge overlapping BN definitions; load and test each coherent package |
| Existing BN sites | Six special IDs identified as merge targets; complete BN special catalog checked; chemist replacement generated preserving all other BN map data | Other five sites and remaining map variants; reconcile layouts and NPC positions; trade-zone consumers; native install and map generation validation |
| New site candidates | Eight linked layouts identified for further comparison | Complete BN map index and dependency checks before adding; supported mapgen schemas; placement and world-generation tests |
| Windows delivery | Dedicated native build and fast content CI | Passing current native tests and assembling a playable archive; staged bulk data is not installed automatically |

The 63 blocked definitions include 36 EOC declarations requiring lifecycle review.
They are not 63 independent engine features or 63 broken NPCs. Some immediate EOC
effects are already inlined safely; delayed/recurring execution remains separate.
Zero adaptation blockers in a group does not establish runtime compatibility.

The chemist replacement is included in the native patch, pending Windows validation. It changes the chair and NPC placement representation only.
It does not complete the four chemist quests or the shop zones. No second special,
second mapgen variant or extra chemist is added.

Full camp creation/construction/work assignments and the pocket system have not
been implemented. Faction stock serialization is groundwork, not a restored camp.
The standalone paranormal church and emergency settlement examples still need exact
source identification and comparison. Highway work remains in its separate branch;
this NPC snapshot does not certify highway visual fixes or combine the two builds.

Next priorities: native regression, shared event/activity compatibility, coherent
existing-location/NPC merges, then broader placement and playable packaging.

## Location expansion, 2026-10-17

Nuclear power plants already exist in the pinned BN source, including levels -1 through +7 and attached hazardous-waste basements at -2. All nine main mapgen floor layouts are geometrically the same as DDA; BN has intentional reactor/grid and train substitutions. A minimal replacement adds 24 DDA shoreline cells (684 to 708 placements), retaining every BN placement and generation rule. Native Windows loading and natural generation remain pending.

Hub 01 now has a generated 102-cell replacement candidate (69 BN cells, 33 additions, two replacements). The complete DDA special has 102 cells, correcting the previous partial count of 100. Eight cells on z=-1 include foyer/security/control spaces and a shaft; the residential level is elsewhere. The candidate retains BN frequency, road connections and unique-generation policy. Five matching DDA mapgen/palette/terrain source files are staged alongside it; the candidate is not installed until dependency, schema and vertical-access review passes.

## Hub native access bridge, 2026-10-17

Code now includes the exact hidden ancillary credential, reciprocal marshal-trait exclusion, inherited BN control terrain, and native directional handlers around existing BN elevator transport. Native authorization, revocation, bounds and handler-registration tests are included. Windows compilation, actual loaded-map travel and expanded Hub generation remain pending. The existing public elevator menu is unchanged.

The latest failed run was a Windows cp1252 encoding error before compilation, not an engine compile failure. Generated Hub maps now explicitly use UTF-8/LF; a regression emulates the Windows default. The previous casing build completed 35 cases/2897 assertions in both source and installed directories and produced artifact 12101510392.

## Radio stations, 2026-10-17

Two existing BN radio station variants now have a reviewed native replacement adding DDA tower floors z=2..6, relocated into their existing courtyards. The buildings, computers and contents remain BN definitions. Static geometry/preservation checks pass; the new native real-mapgen regression covers both variants and four orientations with seven-level ladder continuity. Windows compilation/generation, natural placement and full world-save validation remain pending.


## Eldercare creature checkpoint, 2026-10-18

The shared support layer now prepares eight creature adaptations, four spawn groups, three equipment groups and one emitter (16 definitions). Added unique mother/warehouse cellar spiders and the five-entry timed basement group; source days map to BN numeric hours and follow BN upgrade-factor/boundary semantics. The stock BN death-spawn hook releases six juvenile spiders instead of DDA's random 3..8 age mixture. See eldercare_fauna/README.md for exact differences.

Eleven definitions remain staged for the complete nursing-home/retirement sites: seven living civilians and four mixed, recursive or timed civilian-containing groups. Their friendly human role, dialogue, conditional guns and transition to zombies require actual adaptation; hostile-feral aliases would be incorrect. Full site installation/generation remains disabled. The previous creature checkpoint 0ad8b3a passed fast CI; new native Windows/installed checks, combat and generation remain pending.


## Noncombatant civilian checkpoint, 2026-10-18

Three unarmed living human types are now prepared with a native read-only dialogue graph in the BN chat menu and the existing human-faction/evolution/corpse mechanisms. A single-monster upgrade-only group preserves exact source hierarchical probabilities (90600 total). Seven definitions remain for the full sites: four armed civilian types and three mixed/timed map groups. Conditional guns and real hostile-target selection require their own native work; no armed type is silently replaced by a feral. Stock BN GUILT is an explicit approximation. New native compilation, source/installed runs and manual menu/behavior checks remain gates. See civilians/README.md.


## Current Civilians reuse correction, 2026-10-18

Supersedes the standalone civilian checkpoint above. Six existing Civilians mod types now receive dialogue only. The duplicate core monsters and 90600-weight evolution group are removed; every original stock-mod field and all Lua/spawn/evolution data are preserved. Full sites remain conditional on Civilians and disabled. Five source candidates remain: two unique armed types and three location groups. A complete bundled-mod catalog/collision gate and mod-disabled/mod-enabled source/installed tests are added; full CI and manual behavior validation remain pending.

## Eldercare population closure (2026-10-18)

All five previously staged definitions are resolved: two armed people reuse existing Civilians counterparts, and three group tables compile to the stock BN format inside the optional mod. See eldercare/GROUP_ADAPTATION.md for intentional loadout/profile differences and exact probability checks. Typed adapted dependency closure is now zero staged/zero unresolved; whole sites remain disabled pending mapgen/schema/generation checks and the Civilians Lua population audit. New native source/installed validation is pending.

## Full eldercare map layer (2026-10-18, follow-up)

Prepared all 71 site declarations / 32 mapgen definitions, covering 190 custom OMT tiles and all source rows, parameters, stories and vertical layouts. Extended reference/rotation checks found and adapted the missing road parent, parking-lot ID, station rotations and memorial loot using existing BN providers. See eldercare/MAP_ADAPTATION.md. The maps and Civilians Lua prefix exclusions are reproducible candidates, not installed payloads. Three source frontage cells contain placement constraints without terrain assignment, unsupported by BN's fixed-special loader; resolve that exact behavior before native generation validation and activation. The earlier dependency closure did not cover these additional reference positions or special-loader compatibility.

## Constraint-only fixed specials (2026-10-19 Moscow)

Prepared the small source-based DDA placement behavior in BN's existing fixed-special class: retain all required locations, skip NULL_ID terrain writes/occupied cells, and omit those non-generated cells from mapgen parameter collection/preview. Four-rotation placement/water/terrain tests and invalid-input checks are embedded for Windows source/installed execution. GLOBALLY_UNIQUE is retained using BN's existing global tracking. Full eldercare maps remain uninstalled pending bridge and full generation validation; see frontage/README.md.

## Grey Moose promotion and measured NPC coverage (2026-10-19 Moscow)

The whole Grey Moose community is now embedded for native testing: two templates, nine dialogue topics, faction/shop data and five maps covering 24 OMT tiles, with one trader and six guards. Existing BN items/loot and the ported cigar wrapper close all five missing trade-stock references; Civilians ambient spawning is excluded only on GMLODGE using its existing Lua mechanism. Native tests and packaging guards are prepared; no successful militia native run is claimed yet. See militia/README.md.

PORT_PROGRESS.json now distinguishes 82 started templates, four native-load verified at clean e52486f7 (4.9%), and six embedded including two pending militia templates (7.3%). These are template-level metrics for selected packages, not all-DDA or full quest completion percentages. The clean checkpoint passed both core/mod-enabled suites on source and installed data and packaged Windows successfully; the newer frontage and militia changes await their runs.

## Complete eldercare promotion, 2026-10-19

Supersedes older candidate-only notes: all 71 site declarations are embedded with Civilians, alongside atomic nursing_home/retirement_community ambient exclusions. Three native generation fixtures cover all 190 distinct custom tiles / 219 actual placements including variants and stock BN station/parking/sewer tiles. Source/installed native generation, natural special placement, stairs/elevators and manual traversal remain pending. No new NPC templates are counted for living monsters.
