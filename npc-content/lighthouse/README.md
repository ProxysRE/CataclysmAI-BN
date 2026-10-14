# Lighthouse community checkpoint

Pinned official DDA sources and original IDs are preserved. Four NPCs, 26 dialogue definitions and seven missions include the lighthouse family, associated survivor, floor-cleaning sequence, family rescue and lighthouse repair. Duplicate topic IDs and shared BN topics require additive merging, not wholesale replacement.

Sources now also include both lighthouse maps, island special layouts, all 13 terrain IDs, their abstract parent, camp update maps and two camp recipes. The selected abstract is stored separately; SOURCE_MANIFEST identifies its original upstream file. Run prepare_lighthouse.py and check_lighthouse_links.py to reproduce staging and static link checks.

All thirteen terrain IDs have matching mapgen definitions, placement coordinates are unique, and referenced update mapgen IDs resolve within the checkpoint. External mission target house_04_basement remains an explicit dependency for native verification.

The native bridge handles all 23 arithmetic expressions, including NPC-scoped counters and timers. A dedicated mission-goal-context regression checks the cleanup count belongs to the NPC rather than the player. Earlier timer regression passed Windows validation; the new goal regression is pending.

This is not an installable package. Full native mission start/end and map generation tests, BN terrain inheritance and safety flags, safe-space/NPC-location conditions, common-dialogue merging, item/trait closure and the camp engine remain unresolved release gates.

Verified BN compatibility: common-topic response-only extensions append responses and keep original dynamic lines and built-in answers. Electrical expertise/fake-expertise traits and their groups already exist in pinned BN; upstream selections are kept for provenance but excluded from staging installation. BN_EXPERTISE_REFERENCE.json preserves the exact target definitions. Native regressions cover additive topic loading and real/fake engineer conditions; Windows results are pending.

World entry checkpoint: Mikhail Frolov appears via NPC_lighthouse_man_spawn at a small lake dock. The pinned DDA shore-dock layout exactly matches its BN counterpart. Preparation augments that one matching BN layout with the original 25:75 spawn/null weights at [12,21], retaining all five BN dock definitions unchanged otherwise. Do not install the standalone DDA dock file alongside the augmented BN file. The fisherman_family faction is preserved; its food schema remains part of the pending faction compatibility work. Existing BN lighthouse variants, including basement variants, also overlap DDA and require an explicit compatible migration/overlay plan.

Native faction checkpoint: DDA fac_food_supply entries now load with 64-bit calorie amounts, vitamin maps and expiration turns and survive faction save/load. Old saves clear missing ledgers and retain their scalar stock. The native regression uses the source family amount of 2,700,000,000 calories, above signed 32-bit range. The ledger is data compatibility at this checkpoint; camp food consumption, expiration processing and legacy UI consumers still need integration.
