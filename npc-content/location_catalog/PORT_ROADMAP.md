# Accepted location port roadmap

Accepted by the user on 2026-10-17: all 38 confirmed missing-location/variant groups and all 13 partial/older-version groups in MISSING_AND_PARTIAL.md are project goals. These are groups, not a count of individual map files or buildings. PORT_TARGETS.json preserves every accepted source identity and its intended operation. Acceptance does not claim implementation or runtime validation.

Three unresolved renamed-layout groups remain under comparison. They are not discarded: confirm the actual difference and merge missing content without creating duplicate BN sites. Existing NPC, service, camp, pocket and highway work remains in scope.

## Delivery order — revised 2026-10-20 Moscow

The user's layer-first policy supersedes the old community-by-community completion order. Move broad batches through geometry/access, then furnishing/equipment, loot/items, creatures/NPCs, and interactions/quests/events. Save later-layer source data without installing it into early shells. Navigation-critical objects belong to geometry even if technically furniture.

Start the geometry pass with already preserved large candidates (Hub, campus, Godco, island prison, container yards), then the remaining accepted groups. This order is adaptive, not an exclusive priority list. Existing complete tested locations are retained; do not rebuild them solely to match the new staging format. Otherworld geometry must retain explicit placement/dimension limitations until real travel and event support exists.

Use ../LAYER_AUDIT.md and ../LAYER_AUDIT.json for the current transition inventory. No independent geometry-only shell batch has yet been validated. Source selection and mixed mapgen candidates are not geometry completion.

## Definition of a location package

Include the source maps/floors, generation, inhabitants, dialogue, factions, quests, connected quest sites and all missing transitive dependencies. Reuse BN items, monsters and mechanics when appropriate. Add native support where source behavior cannot otherwise work. An NPC-owned shop must retain its actual services and mission links; an underground complex must have working access.

A completed package must pass native data loading, generation/navigation checks, applicable quest and save/reload tests, Windows compilation and installed-data verification. Report each gate separately.

## Historical farm-store integration checkpoint

Both source layouts and roofs remain non-installed candidates. Merchandise uses BN resources, battery capacities, glues and stock money. A reusable native corpse mapgen action now supports explicit placements and palette bindings; species/age/null-group tests are included in the Windows suite, with results pending. The remaining modular-helmet dependency is preserved in farm_supply/MODULAR_HELMET_REVIEW.json; attaching protective armor through DDA ablative pockets cannot be achieved by declaring an ordinary BN helmet as a container. Farm item/furniture behavior and complete site generation still require native validation.

## Historical connected eldercare layer

Shady Hills now preserves its complete 13-topic/two-EOC computer story. The nursing-home/retirement dependency graph preserves 42 additional source definitions and explicitly tracks 43 unresolved references (within the documented scan scope), including an upstream dangling legal-page topic. Medical evolution and civilian groups are not replaced with superficially similar BN content. Two closed support records, stocked-pond fish and nested spider webs, are embedded with stock BN mechanisms and portable-data guards; Windows runtime validation is pending. Whole sites remain uninstalled until terminal interactions, dependencies and generation are verified.

## Reuse-policy implementation

The 2026-10-18 counterpart policy now has 15 explicit mappings for eldercare sites. Adapted dependencies decrease from 42 definitions/43 unresolved references to 30/27 while retaining all source geometry and terminal stories. Ordinary medical zombies use BN nurses and BN evolution. Farm helmet/stone/carpet variants reuse stock BN content; its full normal and looted layouts, roofs and closed dependencies are now embedded pending Windows runtime validation. Group-level DDA loot containers were corrected to BN contents-group wrappers in both farm merchandise and karting cash registers. Native tests cover actual packaging and farm generation; no successful new Windows runtime result is claimed yet.

## Current verification reference

Windows a379269 / run 39328860166 supersedes the pending native statuses in the historical notes above. Core 73/11030 and optional-mod 10/2224 passed on both source and installed data, with a portable archive. Full farm, karting, small lighthouse, Grey Moose and optional eldercare generation are covered by their targeted tests. Full expanded Hub and the XEDRA church are not installed. See the layer audit for scope-specific evidence.
