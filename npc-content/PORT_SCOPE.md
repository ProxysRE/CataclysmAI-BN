# DDA -> BN scope

The project ports DDA NPC communities and their complete gameplay chains into BN: characters, dialogue, quests, associated maps and sites, factions, trading/services, rewards, equipment and all missing transitive dependencies. Source behavior is the reference; existing BN content must survive overlapping additions. A preserved source or adapted staging definition is not a playable port.

| Block | Intended scope | Current status |
|---|---|---|
| Highways | DDA network, junctions, bridges/ramps, terrain generation | Separate highway branch; Windows release and generation tests passed |
| Isolated Road | Cody, Jay, both missions, all dialogue, weapons exhibition, crafting/banking services and associated items/locations | Native compatibility checkpoint passed; full content package not runtime validated |
| Island prison | Prisoner community, leader mission, faction, maps/floors, Alcatraz variant, camp and epilogues | Staging preserved/adapted; native camp and nutrition work pending |
| Lighthouse | Family and associated survivor, seven missions, lighthouse cleanup/repair and connected sites | New source/staging checkpoint; NPC variables and location dependencies pending |
| Other small communities | Militia lodge, campus library, bunker trader | Grey Moose whole community is in the native payload pending tests; campus/bunker remain staged. See PORT_PROGRESS.json for verified template coverage. |
| Godco | Church community, people, quests and related locations | Bulk source/adapted staging with locations prepared; shared blockers/BN merges and native tests pending |
| Hub 01 | Staff, expanded complex, quests, mercenaries, equipment/services and linked locations | Bulk source/adapted staging with locations prepared; additive BN merge and dependency/native checks pending |
| Existing settlements | Refugee center, Tacoma ranch, Isherwoods | Port missing/changed content while preserving working BN versions |
| Other services | Scrap yard, lumbermill, chemist, homeless camps | Scrap trader, lumbermill and chemist bulk staging prepared; homeless camps remain planned |
| Exodii | Characters, quests, sites, equipment and dependent engine mechanics | Planned; broad native dependency scope |
| Camps | Creation, development/building, NPC assignments and work; NPC community camp registration | Agreed separate engine work; not implemented as a functioning system yet |
| Inventory pockets | DDA pocket/container behavior supporting loaded backpacks and dropping them before combat | Agreed later engine work; not implemented |

Missing dependencies are part of these packages, including weapons, ammunition, items, recipes, traits, monsters, furniture, terrain, EOCs, native dialogue/quest effects and linked communities. Do not use placeholders or remove branches to make validation pass.

This scope does not currently promise a wholesale merge of every unrelated DDA subsystem, all recipes/equipment, every monster, vehicles, mutations and the entire DDA map catalog. Such content is included when required by the agreed NPC/location packages. Additional standalone DDA content can expand the project later.

Validation gates: preserve pinned upstream provenance, resolve typed dependencies, adapt schemas, load the package in native BN, test quests/map generation and build Windows. Current engine test success does not mean all source packages have passed those gates.

Expansion agreed: standalone DDA locations are also planned, beyond NPC dependencies. Audit missing or substantially expanded BN locations and port them with their encounters/monsters/items and generation dependencies. The catalog identifies the XEDRA rural church as a plausible match for the paranormal example and compares the DDA modular FEMA camp with the existing fixed BN camp; identification of the exact player-visited instances is not assumed.

Accepted on 2026-10-17: every confirmed missing or partial location group in location_catalog/MISSING_AND_PARTIAL.md is now a project target, including standalone locations. See location_catalog/PORT_TARGETS.json for all source identities and location_catalog/PORT_ROADMAP.md for adaptive delivery order. All associated NPCs, quests, linked locations and necessary engine/data dependencies are included. Three unresolved renamed-layout groups remain under comparison, not automatic duplication.

Complete eldercare promotion (2026-10-19): both nursing-home layouts and Shady Hills, all floors/basements/roofs and story/loot/population links, are embedded in the optional Civilians mod. Existing BN counterparts and the previously ported support dependencies are reused. Native source/installed generation tests cover all 219 placements; no passing runtime or manual exploration result is claimed yet.

Small island lighthouse (2026-10-19): all six above-ground levels, lake footprint, submerged foundation, boat placement, generators and supply loot embedded as a separate core location. Existing BN analogues reused with explicit semantic differences. Native source/installed generation and ladder/capacity tests prepared; manual placement/access/power validation pending.
