# Verified progress, 2026-10-20 Moscow

Current layer-first transition audit: LAYER_AUDIT.md / LAYER_AUDIT.json. It distinguishes the five content layers, mixed candidates, embedded scope and actual native test evidence across all accepted targets.

The latest successful portable checkpoint is 60e5c6b21be8a964885cfe081c4588f26cfb7448, Windows run 39466430448. Source and installed suites passed core 73/11030, optional 10/2224 and geometry 8/381252. Campus is included; artifact 12289961298 was produced. The new initial-Godco patch requires a separate rerun.

PORT_PROGRESS.json is the reproducible template inventory. It now selects 83 distinct NPC templates: 73 across eight bulk communities, four lighthouse templates, three prison templates, two Isolated Road templates and one explicitly selected container-yard raider boss. Archiving other raiders in the same source file does not select them. Six templates are embedded and source/installed loading is verified: four lighthouse NPCs and the two Grey Moose roles. This is 6/83 = 7.2% template-load coverage for the selected subset, not full quest completion or the percentage of all DDA NPCs. The all-DDA denominator remains unknown. Six Civilians monster types with dialogue, class definitions, dialogue topics and repeated guard spawns do not increase this count.

The latest clean checkpoint covers Grey Moose identities and all seven community spawns across floors; the separate small island lighthouse's six maps, ladder chain, beacon and supply capacities; complete eldercare generation and all three specials in four rotations with optional mods. Church, karting, farm-store and earlier native regression coverage remains included. Natural generation frequency, manual traversal, full NPC campaign lifecycles and save continuity are not certified by these automated tests. Hub, prison and other broader communities remain incomplete/staged; selected nuclear/Hub support and radio/hotel/plaza additions are included slices.

Both complete three-level container yards remain staged, including all 155 source mapgen definitions / 121 nested identities / 119 cargo outcomes. Infrastructure adaptation adds 23 support declarations, 18 BN counterparts, 33 weighted appliance wrappers and explicit rows for 119 one-cell cargo palettes. Corrected directional normalization plus NPC/faction/flag auditing produces 82 raw explicit source obligations, rather than the former 108 misleading misses. The infrastructure candidate has 42 remaining references.

The newer cargo candidate closes another 22 of those references: 14 local quantity/selection groups, five existing group providers, stock blob population, BN money scaling and the actual source raider leader/class. It adds two missing hygiene items and their source snippets. The leader retains source characteristics, skills, faction and patrol mission through the existing BN enum adapter, with 24 references to stock bandit equipment groups. Three unsupported AI traits are explicitly omitted in favor of BN behavior. Twenty explicit dependencies remain, including machinery/folded items, AR glasses, art, some packaging and bulk materials. No cargo branch is dropped. This candidate is not embedded or native-tested. Fixed charge/volume checks do not replace actual native item/default-container and all-cargo generation tests.

There are 51 accepted missing/partial location groups. Terrain cells, map files and roof variants are different units and cannot be divided by 51 to compute completion. Camp construction/work assignments and the pocket system remain separate unfinished work.

Current sources, omissions and adaptations are recorded in container_yards/CARGO_REPORT.json and the associated authenticated source manifests. The prior successful e52486f7 checkpoint remains historical evidence; a379269 is the current complete portable checkpoint.

Geometry-first implementation: geometry_layer/ now isolates island-prison (7 mapgen definitions / 130 special cells), XEDRA church (4 / 5) and both container-yard shells (36 including structural nested maps / 102 cells total). Static typed closure and source-layout conservation checks pass. Full later-layer fields remain archived alongside authenticated inputs. Containers retain an explicit blocking cross-z roof placement unsupported by pinned BN. None of these shells is newly embedded or native validated; the successful portable checkpoint remains unchanged. See geometry_layer/README.md and REPORT.json; CI now repeats check_geometry_layer.py.

Geometry preview follow-up: optional dda_geometry_preview now embeds the prison and XEDRA church shells under collision-checked dda_geo_ identities. Both specials have zero natural occurrences and require deliberate debug placement. Two native tests cover 135 special cells, non-null terrain and absence of loot on all own-OMT cells. Source and installed Windows suites and archive completeness guards include the preview. Current patch has changed; native validation is pending and a379269 remains the previous successful artifact, not proof of this preview. Container yards remain excluded until the cross-z roof is adapted.

Preview run 39345643352 compiled successfully; 73 core and 10 optional source cases passed. Geometry 2 cases / 63,630 assertions ran, but unbound content-only glyphs and a deprecated connection selector produced initialization errors, so the run failed before installed tests/packaging. Extraction now repeats the exact source fill terrain on deferred-content glyphs and normalizes explicit road connections; regression checks added. Hub first-layer candidate is also isolated: 9 maps / 81 own OMT / 102 special records including two constraints. Its 17 raw reference obligations include generated OMT forms and project-native elevators; Hub is not embedded. Full native rerun required.

Geometry checkpoint 925d3b4 / Windows run 39403524594 is fully successful: source and installed core 73/11030, optional 10/2224, geometry 2/63630; initialization clean and packaging passed (artifact 12257794350). Native patch hash matches the updated validation record.

Hub adapted first-layer candidate closes all 17 raw reference obligations using authenticated BN generated identifiers, the existing project elevator provider, three stock terrain counterparts and explicit road inheritance. Underlying source rows and late-layer archives remain intact. Source/target floor and secret-door declarations and material/light differences are recorded. Hub remains non-installed and not native validated; stair/elevator alignment, flags/schema and BN-exclusive geometry review remain. CI repeats the new adapter check.

Expanded Hub geometry is now added only to the namespaced, opt-in preview. Three native cases cover 235 placed cells; Hub adds exact terrain checks for 238 source-projected navigation points (148 shaft, 18 control, 28 stair, 44 ramp tiles). Six restricted directional controls have destination shafts in the static projection. Public controls without nearby projected shafts and unpaired/boundary stairs are retained and explicitly unverified. Source SHOULD_NOT_SPAWN and special priority are archived rather than passed to unsupported BN schema. No existing BN Hub is replaced. The patch has changed and all source/installed native suites must be rerun; 925d3b4 remains the prior successful portable checkpoint.

Campus first-layer batch: all 26 building/open-area maps, 112 unique OMT and five source special layouts (112/16/32/20/12 placements), levels 0 through 4. Row/matrix dimensions, layout conservation, complete own mapgen coverage and typed closure pass; no BN core/bundled-mod ID collisions. Four concrete OMT copy-from links are correctly resolved as concrete rather than abstract providers. Source zero-occurrence policy is retained; unsupported SHOULD_NOT_SPAWN is separately recorded. Late-layer fields remain archived. Campus is staged only, native patch unchanged by this batch; Hub Windows run 39428420703 remains the active native validation.

Hub preview checkpoint confirmed: run 39428420703 completed successfully, including installed data and archive packaging. Campus first-layer batch is now committed separately, still excluded from the native patch. Source-derived navigation checks confirm terrain placement, not complete character movement or real elevator rides.

Campus preview extension: all 26 first-layer maps and five placement layouts now use isolated identities, including correctly renamed concrete-parent inheritance. Eight native cases will cover 427 placed cells; source/installed rerun pending. Previous be7a2c1 archive remains the clean three-package checkpoint. New report_geometry_progress.py records a coarse stable-identity meter: 10/51 generation-verified group scopes = 19.6%; with prepared but unverified campus, 11/51 = 21.6%. This is not work-volume or full traversal completion.

Godco initial first-layer candidate: five world maps, two structural nested rooftop layouts, 22 own OMT, 61 placed cells plus one constraint. Typed closure and source row dimensions pass; source utility pipes/fences/gates are retained while furniture/liquids are deferred. The BN rural-road source is non-LINEAR, so DDA rural_road_forest_ns explicitly maps to the existing vertical rural_road_forest_north variant. All 18 construction updates and 20 nested definitions are audited separately; coop, food warehouse and trader-tent roofs retain three explicit z=1 blockers. No construction quests are enabled or stripped of roofs. Initial Godco is not embedded/native validated and is not credited to the completed-group meter. Campus native validation remains in progress.

Campus checkpoint 60e5c6b / run 39466430448 succeeded: core 73/11030, optional 10/2224, geometry 8/381252 on source and installed data; artifact 12289961298 packaged. Geometry meter is now 11/51 =21.6%. Initial Godco is added only to the new optional preview: ninth layout case /488 total placements, pending native validation. Stock predecessor forest remains at its entrance; native remove_all clears only source road glyphs, and loot checks follow that mask instead of demanding an empty surrounding forest. Later quest construction remains excluded.

## Exodii first-layer staging and Godco Windows checkpoint

Godco initial geometry passed run 39485820362: source and installed suites each passed 73 core cases / 11030 assertions, 10 optional-mod cases / 2224 assertions, and 9 geometry cases / 406338 assertions. Portable artifact 12296363792 was produced. This validates the initial site, not future quest construction or full player traversal. The group-based meter remains 11/51 (21.6%).

Staged all 13 Exodii world map definitions and three structural nested layouts, with 88 OMT across the base, stone barn and warehouse. Nine official pinned files are checksummed. Expanded palette and inline mapping terrain is retained; original source and expanded later-layer fields are archived. No BN/core or bundled-mod identifier collisions. One absent terrain, t_glassed_sand, retains source movement/bash properties; SANDGLASS visual connections are deferred. The staged sites have zero occurrences, are not embedded, and receive no completion credit pending schema/generation checks.

## Exodii isolated native geometry preview

Added the base, stone barn and warehouse to the optional namespaced geometry mod: 88 extra placements, twelve total generation cases /576 placements. Three nested layouts and glassed-sand terrain use isolated identifiers. BN integer visibility costs replace source named levels; source geometry and concrete OMT inheritance remain intact. The generated native tests add 176 deterministic navigation-terrain expectations, including ladders, stairs, elevator tiles and controls.

Source/installed native validation is pending for this new patch; the successful Godco checkpoint remains historical evidence. No natural site spawning or late-layer content is enabled. Full player movement/elevator operation is not certified. The completion meter remains 11/51 pending native evidence.

## Exodii checkpoint and four frontier geometry packages

Windows run 39519170435 on ada9d93 passed 73 core cases /11030 assertions, 10 optional cases /2224 assertions and 12 geometry cases /508066 assertions, repeated on installed data. Portable artifact 12313885149. The Exodii group now has demonstrated generation scope: 12/51 groups (23.5%), not full traversal or quest completion.

Staged Isolated Road, gun show, Balthazar bunker and limnological station together: 20 world-map definitions, 29 own OMT and 37 placed cells including eight stock lake cells. Seven pinned official source files are authenticated, plus shared roof geometry from the existing authenticated archive. Two structural roof utilities preserve pipe/fence/gate geometry; other furniture, loot and inhabitants remain deferred. Full original specials retain source camp fields and occurrence policies in the archive, while candidate occurrences are zero. No core or bundled-mod declaration collisions. Four raw terrain obligations remain explicit (canvas roof, artisan reader, Balthazar intercom, concrete secret door); no native embedding or completion credit yet.

## Four frontier sites added to isolated geometry preview

Resolved all four raw terrain obligations in a separate adaptation. Canvas roof retains the source definition with an isolated ID. The secret door reuses the previously reviewed BN metal counterpart (material/destruction differ from DDA concrete). Artisan reader and Balthazar intercom inherit stock BN panel geometry with source descriptions and no examine action: faction access/NPC behavior belongs to later layers, and ordinary science-card/intercom interactions must not be substituted. Three extra pinned source files authenticate those decisions.

All four specials are now in the opt-in geometry preview: total 16 cases /613 placements. Generated native assertions add 1167 deterministic navigation, panel, secret-door and canvas-roof terrain expectations, in addition to all-cell non-null/empty-loot checks. Source/installed Windows validation is pending for the new patch; 12/51 (23.5%) remains the confirmed group metric.

## Fix frontier panel terrain loading

Run 39590006274 compiled successfully and passed 73 core /11030 assertions and 10 optional /2224 assertions. Geometry initialization stopped at the artisan panel: the BN terrain loader required symbol despite copy-from. Installed tests and packaging did not run.

Both reader and intercom now copy the complete authenticated BN terrain definition rather than relying on JSON inheritance. Physical fields, flags, roof, bash and drops remain exactly stock; source identity/text and no-op preview examination are explicit overrides. Added concrete-terrain guards and regression probes rejecting both the old inheritance-only object and a missing-symbol object. All four custom preview terrains are checked before compilation. Native source and installed validation remain pending for the corrected patch; confirmed progress stays 23.5%.

## Corrected frontier Windows checkpoint and raider embrasure preparation

Run 39620442620 on a8f22c2 passed 73 core /11030 assertions, 10 optional /2224 assertions and 16 geometry /542715 assertions, repeated successfully on installed data. Portable artifact 12359175270 was produced. The four frontier groups now have demonstrated generation scope: 16/51 =31.4%. Concrete panel loading is verified; full traversal and faction/intercom interactions remain outside this claim.

Prepared the raider wooden embrasure and widened damaged opening from authenticated DDA terrain definitions. Two complete concrete terrain objects retain coverage, movement, source bash thresholds and wood items; source roof and field-emission differences are documented. The new adaptation has closed typed references but is not embedded or native/combat tested.

## Raider geometry preview integration

Added drug lab, bandit drug lab, work camp and deserter settlement to the isolated optional preview. All 15 world maps and 25 placements are included, bringing the fixture to 20 cases /638 placements. Native tests project source navigation and wooden-embrasure terrain expectations into their global-map cells. The complete source city registration remains archived; the debug-only special does not replace BN city generation.

Six custom terrain definitions passed concrete-field preflight. Only the two preview JSON files and geometry C++ test sections changed in the native patch; their generated new-file diffs apply and reproduce source bytes. All other patch sections remain byte-identical to the successful Windows checkpoint. Native source/installed generation and embrasure combat/fire/bash acceptance remain pending. Confirmed progress remains 16/51 (31.4%).

## Raider Windows checkpoint and urban geometry closure

Run 39647265421 on d75ca47 passed source and installed suites: 73 core cases /11030 assertions, 10 Civilians+Exotic Ammo cases /2224 assertions and 20 optional geometry cases /571932 assertions. Portable artifact 12371454521 (205642479 bytes, sha256:eacbb84e844a349d23576ee276d28f4faba84e295e1b08a9063b92a96af67b11). Raider generation adds two accepted groups, not four: the three drug-lab/work-camp specials share one catalog group; deserters are the second. Confirmed scope is 18/51 =35.3%. Combat, fire, destruction and player traversal remain outside this acceptance.

Police department, textile museum and supermarket retain 66 own OMT, 14 world maps, four structural nested chunks including the police gym carpet, and separate late-layer content. Unavailable wall paint uses existing BN walls of matching construction. A complete concrete BN pavement object supplies a new isolated white crossing with DDA presentation, BN pavement connectivity and dirt after destruction. Typed dependencies are closed; BN schema loading and all-floor generation remain pending. These three groups add no completion credit yet.

## Urban geometry preview integration

Added department, textile museum and supermarket to the opt-in preview: 23 layout cases /704 placements. Their 120 projected navigation and marking points now have native terrain assertions, with coordinate rotation for southern police cells. All seven concrete preview terrains pass required-field checks. Only the two preview JSON sections and geometry C++ test section changed in the checksummed engine patch; other sections are preserved. Source and installed Windows generation remain pending. Verified progress stays 18/51 (35.3%).

## Urban Windows checkpoint and waterside staging

Run 39686560752 on 45a077a passed 73 core cases /11030 assertions, 10 optional cases /2224 assertions and 23 geometry cases /648216 assertions, repeated on installed data. Portable artifact 12389029662 (205652350 bytes, sha256:856ddbfd9d1ceb01309c3b06b35bd8e4cc865c9d906d9e800d2b5237d5d087f2). The department, textile museum and supermarket add three confirmed groups: 21/51 =41.2%, without full player-traversal or later-layer certification.

Staged hot springs, pottery cottage and sunken helicopter: eight mapgen definitions, eleven own OMT and nineteen special placements (including stock surrounding river/lake cells). Source geometry and later content are separated. Neutral item-only glyphs on predecessor maps now preserve their underlying terrain; the extractor also accepts authenticated white linoleum fallback alongside gray. Existing preview output remains reproducible. Missing thermal-water and helicopter terrain definitions remain explicit; no native installation or completion credit for this batch.

## Waterside material and firepit adaptation

Expanded the cottage garden nest: its trunks are structural terrain and are retained under an isolated nested identity; the fire ring, seating and wood remain deferred. Prepared sixteen complete wreck terrain definitions from authenticated BN metal floors/walls, half-wall and window parents, applying source water flags, descriptions and quarterpanel destruction. DDA lc_steel_chunk reuses BN steel_chunk with the same quantity. Source window shoot behavior is archived, and stock BN ranged mechanics remain. Unavailable wall colors reuse the same BN construction.

Hot water retains source movement, flags and heat_radiation=1, but BN lacks the DDA liquid_source/min_temp loader. Its source-temperature collection is an explicit pending mechanism; examination is disabled in this geometry-only candidate. All typed refs close, with river_north classified as generated BN overmap terrain. 148 deterministic projected terrain checks are prepared, with random-rotation invariance filtering. Native data loading, underwater traversal/destruction, thermal gameplay and installed-data generation are pending. No native patch changes and no additional completion credit: 21/51 remains 41.2%.

## Waterside native preview integration

Added hot springs, pottery cottage and sunken helicopter to the opt-in preview: 26 layout cases /723 source special placements, plus four lake-water context cells in the helicopter fixture. All 24 concrete custom terrain definitions passed required-field checks. The 148 deterministic navigation/underwater terrain points are native assertions. Predecessor maps without rows retain stock lake-bed generation; random-rotation loot masks check only the intersection of terrain-painted cells. BN remove_all clears only terrain-painted predecessor glyphs. Hot-water collection remains disabled pending source-temperature support.

The two preview JSON sections and geometry C++ test section of the native patch were replaced and independently applied to reproduce source bytes; unaffected patch sections are preserved. Source/installed Windows loading and generation remain pending. Verified progress stays 21/51 (41.2%).

## Scope correction and Windows encoding fix

The user explicitly excluded DDA collected-water temperature on 2026-10-22. It is no longer a planned mechanism or release gate. Springs now use BN water_source and stock untreated-water/contamination behavior, confirmed against pinned mapbuffer::water_from; heat radiation remains an existing supported terrain field. Source liquid_source/min_temp is archival only. This supersedes earlier pending-temperature and disabled-collection notes.

Run 39776684153 stopped before compilation: Windows cp1252 default decoding split UTF-8 cottage glyphs, causing row-width preflight to fail. Both waterside scripts now read/write text explicitly as UTF-8. The complete extractor passes with Path.read_text defaults simulated as cp1252, and source-row dimensions remain unchanged. Native source files and patch are regenerated; corrected Windows validation is pending.

## XEDRA field sites and LIXA staging

While the corrected waterside Windows run proceeds beyond source preflight, staged Morgantown, the XEDRA fishing shack and physics lab LIXA together. Six authenticated official files provide 26 world-map definitions /50 own OMT /100 source-special placements. A 27th nested definition retains ruined tent walls, floor and door with exact source weights and no invented roof. The flat-space barrier line is also preserved as structural furniture and explicitly included in typed reference scanning.

All source rows and dimensions are preserved. 25 raw typed obligations and no exact core/bundled-mod declaration collisions remain. Full passcode door definitions, terrain transforms, device unfolding, EOCs/updates, graffiti and other later content are retained. No invented stair connects the -4 device to its -8 unfolded region. UTF-8 extraction and simulated Windows cp1252 defaults pass. These packages remain non-installed and add no progress credit; confirmed scope remains 21/51 (41.2%).

## XEDRA/LIXA physical adaptation

Prepared 19 isolated concrete terrain definitions and the flat-space structural barrier. Typed dependencies close against pinned BN, including all bash/deconstruction drops and target transitions. The LIXA wall/folded-wall/unfolded-wall cycle and source thresholds are preserved, with explicit checks for all three edges. Source movement, light, coverage, shaft markers, doors and physical device surfaces remain intact.

Ordinary carpet, metal roofing, concrete roof geometry, regional vegetation, metal wall and road context reuse BN counterparts with documented material/appearance/durability differences. BN wire and steel_chunk replace source component tiers. The source road abstract expands into the compatible generic_transportation base, and BN LINEAR road data justifies road_ns. Reader/ledge EOC actions, shooting objects, emissions, tools and unsupported display groups remain archived; no generic science-card access is added.

Native schema, all-floor generation, source device mechanics, actor traversal and combat are pending. No native patch or confirmed percentage change while the existing waterside build continues: 21/51 (41.2%).

## Waterside overmap-flag loading fix

Run 39786965319 compiled successfully and passed core NPC and optional Civilians/Exotic Ammo tests. Geometry initialization stopped on DDA's generic WATER overmap flag, which pinned BN does not recognize; installed suites and packaging were not reached.

The hot-spring overmap classification is now archived without substituting a lake or river. Its local water terrain, ordinary BN collection and heat radiation are unchanged. Added a checksum-authenticated BN overmap header and a precompile audit of every preview overmap flag, including extend/delete flag sets. A mutation probe rejects WATER and the current preview passes the entire supported-flag audit. Rebuilt the preview patch sections and verified their application reproduces native source bytes. Corrected Windows source/installed validation remains pending; confirmed progress stays 21/51 (41.2%).

## Cottage placement predicate correction (2026-10-22)

Windows run 39801557898 on 60cdfa75 compiled and reached the geometry suite, but initialization rejected four cottage upper-floor `open_air` location constraints. The pinned BN defines `open_air` overmap terrain but no same-named overmap_location. Added an isolated `dda_geo_open_air` predicate restricted to that stock terrain, preserving all four source coordinates and air-only semantics. No source map rows, natural occurrence policy or ordinary BN registrations changed.

Archived the pinned BN special_locations registry with a manifest checksum. Precompile validation now checks both special-wide and per-cell placement predicates, plus terrain references in new predicates. Mutation probes reject the original unsupported name in both positions. All other preview predicates close against the pinned registry. Only the preview JSON new-file patch section changed; independent git application reproduces all three preview files byte-for-byte. Source/installed Windows rerun remains required; verified geometry scope stays 21/51 (41.2%).

## XEDRA/LIXA native geometry preview integration (2026-10-22)

Embedded the prepared Morgantown, XEDRA fishing shack and LIXA physical shells in the opt-in geometry preview: 29 layout cases /823 source-special placements, plus four helicopter water-context cells. Includes all 27 research mapgen definitions, 19 concrete terrains and the structural flat-space barrier. The separation between LIXA's device regions is not bridged by an invented staircase; source unfolding/access remains a later-layer requirement.

Native generation tests now project 2,383 deterministic research terrain points and 16 furniture points for the complete barrier line, with directional rotation for source cells. A precompile fixture audit independently compares all generated C++ placement coordinates/terrain IDs to embedded special declarations. Predecessor maps clear loot only on terrain-painted cells, preserving untouched BN surroundings. Source originals and deferred interactions remain archived. Unknown placement predicates and overmap flags are checked directly in the Windows preflight, not only the parallel fast CI.

The three geometry preview patch sections independently apply to reproduce source bytes; all other sections remain byte-identical. All 49 embedded native files match the patch/checksum. Static reference/collision, source-row, schema-field, predicate and fixture checks pass locally. Native Windows source/installed generation and player traversal are pending; no additional completion credit: 21/51 (41.2%).

## Three further large-site shells (2026-10-22)

While fff46f9 remains in Windows compilation and a183f02 waits, prepared the oil platform, football stadium and office skyscraper together: 32 world-map definitions /307 own OMT /393 source placements. The nested room/roof graph preserves 291 definitions /189 identities and all weighted alternatives, rows, dimensions and source coordinates. Full source registrations and later-layer content are archived separately. Twenty-four new authenticated source files and already archived house/roof providers support the batch.

Closed 31 initial typed obligations with BN counterparts, expanded overmap parents and four concrete drilling/water terrains. Source greenhouse z=+1 roof nests remain explicit integration blockers; BN's absent ocean predicates require a platform habitat adaptation. Unsupported OCEAN flags are archived. No native patch modification, sea-generation claim or completion credit: confirmed geometry scope remains 21/51 (41.2%). Reproducibility, exact layouts/weights, predicates/flags and preserved blockers have a dedicated fast CI check. See geometry_layer/LARGE_SITES_GEOMETRY.md.

## Waterside Windows checkpoint and reachable large-site integration (2026-10-22)

Run 39828961648 on fff46f9 completed successfully. Source and installed suites both passed: core 73 cases /11,030 assertions, Civilians+Exotic Ammo 10 /2,224, geometry 26 /663,753. Portable artifact 12452926077 is 205,655,665 bytes, sha256:c04b8a59f71fb560ee31a556bd09f7a3ddd189645501f937cd399a5bdd7b7d63. Springs, cottage and sunken helicopter add three confirmed groups: 24/51 =47.1% of the coarse geometry-generation scope. Research preview run 39829689355 is separately compiling; no research-generation credit yet.

The two upward greenhouse nests are not reachable from the three new large-site world layouts. A new selector embeds only the actual dependency graph: all 32 world maps and every alternative of 140 reachable nested identities (222 definitions). Forty-nine unused identities, including both blocked greenhouse variants, remain in the authenticated full staging. A nonzero-z guard rejects future attempts to embed them; no global multi-floor nested-mapgen support was added.

Embedded stadium, skyscraper and platform shells in the opt-in preview, totaling 32 layout cases /1,216 source-special placements plus four helicopter context cells. The platform uses reviewed BN lake placement predicates/classification instead of inventing an ocean system; source geometry and local salt-water collection remain, while BN surroundings retain normal freshwater behavior. Natural spawning and lake-depth/travel acceptance remain pending. Added 671 deterministic terrain/furniture points, excluding random-overlay intersections, plus all-cell non-null coverage. Homogeneous water samples are bounded to avoid excessive Windows test stack use. Only the three geometry-preview patch sections change; unrelated engine sections are preserved. Windows source/installed validation is pending; confirmed progress remains 24/51.

## Research roof correction and publication continuation (2026-10-23)

The user explicitly authorized publication of prepared commit 171c40e and ongoing work in the same public port/dda-npc-locations branch. The previous attempt after approval was not executed because the automatic approval-review service hit a usage limit; it was not a new safety rejection.

Research run 39829689355 compiled and passed core 73/11030 and optional 10/2224, but its geometry initialization rejected five automatic roof links to t_strconc_floor_no_roof. Those links now use the existing BN flat roof, which satisfies bash_below and no-recursive-roof requirements. Explicit walkable source concrete-roof surfaces still reuse BN reinforced-concrete flooring. Source layout, LIXA wall destruction cycle/thresholds and device placement remain unchanged. Current geometry preflight checks all custom roof links against authenticated pinned BN definitions and rejects both the original floor-provider regression and recursive roof chains.

Added update_geometry_preview_patch.py to reproducibly replace only the three generated geometry sections of the existing engine patch, independently apply them and verify exact bytes, preserve unrelated sections and update the Windows checksum. Local source/adapter reproducibility, all 49 embedded-file checks, terrain/roof schema, large-site graph/fixture checks and coarse progress checks pass. The corrected research preview and the prepared large-site preview still require Windows source/installed validation. Confirmed scope remains 24/51 (47.1%); no research or new large-site completion credit yet.

## Modular apartment geometry staging (2026-10-23)

Published the roof correction and reachable large-site preview together as 8f54d0c. Its three fast CI workflows passed; Windows run 39871832681 has reached executable compilation and has not yet produced a generation or packaging result.

While compilation proceeds, prepared all five modular apartment city layouts: 322 source placements, 31 world-map definitions, 37 own OMT and 103 nested definitions, including every weighted apartment-room variant. Original maps, source city registrations and deferred content remain archived. The extended layout's two-cell parking geometry uses isolated identities to avoid replacing stock BN parking.

Physical typed references close with BN wall/linoleum counterparts and an expanded roof abstract. Unsupported SHOULD_NOT_SPAWN registration policy is archived; occurrences remain zero. Source rows, dimensions, weights and six above-conditioned garage stair placements are checked independently. The reachable graph retains all 83 variants of 40 nested identities and has no nonzero-z placements; unused greenhouse roof blockers remain preserved in full staging. BN conditional-stair and duplicate-OMT variant behavior still require review before native embedding. Added a separate reproducibility/conservation CI check. No native patch change or additional progress credit: 24/51 (47.1%).

## Windows geometry failure: implicit air and LIXA phase order (2026-10-23)

Run 39871832681 on 8f54d0c compiled successfully and passed source core 73 cases /11,030 assertions and optional Civilians+Exotic Ammo 10 /2,224. Geometry finished with two failed assertions in LIXA and strict data errors for the drill machinery/string. Installed suites and packaging were not reached. The previous automatic-roof errors did not recur; this run still adds no accepted generation credit.

Two drilling terrains now use BN's required null destruction result rather than explicit t_open_air. Pinned map::bash_ter_success supplies open air through its normal fallback; source thresholds and drops are retained. Precompile regression probes reject explicit air results in bash/deconstruction. Two legacy sound-volume fields on the research illuminated carpet use the exact dB strings recommended by BN's loader.

The LIXA barrier discrepancy came from generation order: DDA applies set operations in their terrain/furniture phases; BN applies all set operations before row terrain. The compressor WALL tiles at (12,9) and (15,9) therefore erased two previously placed barrier cells. The adaptation expands the original horizontal line into sixteen late-phase place_furniture points, preserving every coordinate and the complete native acceptance line. Original source set data stays in staging. Added pinned runtime source evidence, a source-order audit and a regression probe rejecting the old early-phase representation. The existing native test source is unchanged.

Rebuilt only the preview JSON/test patch sections, with all unrelated engine sections preserved. Corrected source/installed Windows validation remains pending; confirmed scope remains 24/51 (47.1%). Apartment integration stays separate until this correction has been submitted for validation.

## Apartment preview candidate and native expectation preparation (2026-10-23)

The user authorized the exact 21-file correction package for public publication. Published it as 9b9ba5a; Windows run 39945286436 is compiling the executable. No new source/installed test result yet.

Prepared a fully namespaced apartment preview candidate without changing that native patch. Pinned BN code confirms above-neighbor predicates, vertical neighbor lookup and additive per-cell loading of repeated-ID mapgen slices. The entrance's four equally weighted 24x24 slices remain in the complete 96x24 source template. Neighbor type references are namespaced with their declarations, with a regression guard rejecting the original unnamespaced spelling.

The candidate keeps 31 world maps, 37 own OMT and all 83 variants of 40 reachable nested identities. Prepared 284 fixture expectations across the five source layouts: 272 projected navigation points and twelve conditional garage-stair points (three positive, nine negative), including rotated wings. Deterministic navigation uses the intersection across repeated-ID variants and conservatively masks random nested overlays. Original source cells, weights and full staging are retained. The candidate is not embedded; no Windows generation, full traversal or additional progress credit is claimed. Verified scope remains 24/51 (47.1%).

## Inherited map-extra isolation and apartment native integration (2026-10-23)

Run 39945286436 on 9b9ba5a compiled and passed source core 73/11,030 and optional Civilians+Exotic Ammo 10/2,224. The previous roof, explicit-air destruction, legacy-volume and LIXA-barrier failures did not recur. Geometry stopped with 27 empty-loot assertion failures in two cases: stadium and skyscraper. Installed suites and packaging were not reached; confirmed progress stays 24/51.

The affected OMT inherit BN generic_city_building, whose parent generic_city_building_no_sidewalk supplies extras=build. Pinned BN generation applies regional map extras after draw_map, allowing random events to add content and alter an otherwise stripped shell. Every own preview OMT now explicitly sets extras to an empty string, preventing inherited ambient events. Original registrations and late-layer data remain archived; stock surrounding OMT retain BN behavior. Added precompile rejection of missing/nonempty extras overrides, with regression probes for the inherited build pool. Empty-loot assertions remain unchanged; no post-test item clearing was added.

Integrated all five prepared apartment layouts into the optional native preview: 37 layout cases /1542 fixture cells, including four helicopter context cells. All 322 apartment source placements and 284 prepared navigation/stair expectations are embedded, including three positive and nine negative conditional checks. A fixture audit compares every apartment C++ expectation with its prepared source-derived record and verifies that above-neighbor types are namespaced. The candidate retains all 83 reachable nested alternatives without adding a general nested-mapgen z-offset feature.

Only the canonical three geometry patch sections were regenerated, preserving unrelated engine sections. Source/installed Windows generation, player traversal and later-layer content remain pending. No additional geometry-generation credit is claimed: 24/51 (47.1%).

## Survivor housing and Lacroix source staging (2026-10-23)

Windows run 39962621096 on 58601a4 passed compilation, source core dialogue and optional Civilians+Exotic Ammo suites. Geometry is still running; installed suites and packaging have not yet completed. Confirmed geometry credit remains 24/51.

Prepared five further source specials in one staging batch: prepper cabin, Liam cabin, survivor forest camp, locked LMOE shelter and Lacroix cemetery. Eight full official files match pinned Git blobs and SHA-256; authenticated shared roof and rural nested sources are reused. The staged shell retains 16 special placements, 12 OMT identities, 11 world-map alternatives and six structural nests. Two whole-palette cabin choices retain their original correlation as two weight-500 alternatives. Exact source rows, rotations, special coordinates and weights are checked, including the camp's dynamic source weight. Full late-layer data and unused source objects are preserved.

Three upward structural placements remain explicit blockers: LMOE surface exit, its roof and intact leather-tent roof. Two fallback forest predecessors and the time-dependent camp weight also require BN adaptation. The ruined tents intentionally have no source roof. No vertical geometry was silently discarded. This batch is not embedded and receives no completion credit; a separate CI check validates its reproducibility and conservation.
