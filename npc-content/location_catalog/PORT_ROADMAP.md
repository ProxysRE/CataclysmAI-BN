# Accepted location port roadmap

Accepted by the user on 2026-10-17: all 38 confirmed missing-location/variant groups and all 13 partial/older-version groups in MISSING_AND_PARTIAL.md are project goals. These are groups, not a count of individual map files or buildings. PORT_TARGETS.json preserves every accepted source identity and its intended operation. Acceptance does not claim implementation or runtime validation.

Three unresolved renamed-layout groups remain under comparison. They are not discarded: confirm the actual difference and merge missing content without creating duplicate BN sites. Existing NPC, service, camp, pocket and highway work remains in scope.

## Delivery order

1. Finish already started communities and their connected sites: Hub 01, Isolated Road and the exhibition, Godco, campus, militia and island prison.
2. Expand to further communities and linked complexes, including Exodii, Balthazar, deserters and the limnological station.
3. Extend existing BN sites: refugee center, Alcatraz, FEMA, farms and the reviewed urban/tower/ship variants.
4. Port independent overworld locations in batches sharing compatible mapgen and dependency patterns. These may proceed alongside earlier packages when their dependencies are ready.
5. Port otherworld locations with the real dimension, travel and event mechanisms they require. Do not ship them as disconnected or nonfunctional maps.

Order is adaptive; it does not require every earlier group to finish before independent work can proceed.

## Definition of a location package

Include the source maps/floors, generation, inhabitants, dialogue, factions, quests, connected quest sites and all missing transitive dependencies. Reuse BN items, monsters and mechanics when appropriate. Add native support where source behavior cannot otherwise work. An NPC-owned shop must retain its actual services and mission links; an underground complex must have working access.

A completed package must pass native data loading, generation/navigation checks, applicable quest and save/reload tests, Windows compilation and installed-data verification. Report each gate separately.

## Current farm-store integration checkpoint

Both source layouts and roofs remain non-installed candidates. Merchandise uses BN resources, battery capacities, glues and stock money. A reusable native corpse mapgen action now supports explicit placements and palette bindings; species/age/null-group tests are included in the Windows suite, with results pending. The remaining modular-helmet dependency is preserved in farm_supply/MODULAR_HELMET_REVIEW.json; attaching protective armor through DDA ablative pockets cannot be achieved by declaring an ordinary BN helmet as a container. Farm item/furniture behavior and complete site generation still require native validation.

## Connected eldercare layer

Shady Hills now preserves its complete 13-topic/two-EOC computer story. The nursing-home/retirement dependency graph preserves 42 additional source definitions and explicitly tracks 43 unresolved references (within the documented scan scope), including an upstream dangling legal-page topic. Medical evolution and civilian groups are not replaced with superficially similar BN content. Two closed support records, stocked-pond fish and nested spider webs, are embedded with stock BN mechanisms and portable-data guards; Windows runtime validation is pending. Whole sites remain uninstalled until terminal interactions, dependencies and generation are verified.
