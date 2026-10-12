# DDA -> BN scope

The project ports DDA NPC communities and their complete gameplay chains into BN: characters, dialogue, quests, associated maps and sites, factions, trading/services, rewards, equipment and all missing transitive dependencies. Source behavior is the reference; existing BN content must survive overlapping additions. A preserved source or adapted staging definition is not a playable port.

| Block | Intended scope | Current status |
|---|---|---|
| Highways | DDA network, junctions, bridges/ramps, terrain generation | Separate highway branch; Windows release and generation tests passed |
| Isolated Road | Cody, Jay, both missions, all dialogue, weapons exhibition, crafting/banking services and associated items/locations | Native compatibility checkpoint passed; full content package not runtime validated |
| Island prison | Prisoner community, leader mission, faction, maps/floors, Alcatraz variant, camp and epilogues | Staging preserved/adapted; native camp and nutrition work pending |
| Lighthouse | Family and associated survivor, seven missions, lighthouse cleanup/repair and connected sites | New source/staging checkpoint; NPC variables and location dependencies pending |
| Other small communities | Militia lodge, campus library, bunker trader | Planned comparison and complete missing additions |
| Godco | Church community, people, quests and related locations | Planned |
| Hub 01 | Staff, expanded complex, quests, mercenaries, equipment/services and linked locations | Planned additive comparison; BN already has underground data, differences require exact audit |
| Existing settlements | Refugee center, Tacoma ranch, Isherwoods | Port missing/changed content while preserving working BN versions |
| Other services | Scrap yard, lumbermill, chemist, homeless camps | Compare and port missing characters, services, quests and locations |
| Exodii | Characters, quests, sites, equipment and dependent engine mechanics | Planned; broad native dependency scope |
| Camps | Creation, development/building, NPC assignments and work; NPC community camp registration | Agreed separate engine work; not implemented as a functioning system yet |
| Inventory pockets | DDA pocket/container behavior supporting loaded backpacks and dropping them before combat | Agreed later engine work; not implemented |

Missing dependencies are part of these packages, including weapons, ammunition, items, recipes, traits, monsters, furniture, terrain, EOCs, native dialogue/quest effects and linked communities. Do not use placeholders or remove branches to make validation pass.

This scope does not currently promise a wholesale merge of every unrelated DDA subsystem, all recipes/equipment, every monster, vehicles, mutations and the entire DDA map catalog. Such content is included when required by the agreed NPC/location packages. Additional standalone DDA content can expand the project later.

Validation gates: preserve pinned upstream provenance, resolve typed dependencies, adapt schemas, load the package in native BN, test quests/map generation and build Windows. Current engine test success does not mean all source packages have passed those gates.

Expansion agreed: standalone DDA locations are also planned, beyond NPC dependencies. Audit missing or substantially expanded BN locations and port them with their encounters/monsters/items and generation dependencies. The paranormal church and large emergency-response settlement mentioned by the user are identification candidates; do not assign exact source IDs until verified.
