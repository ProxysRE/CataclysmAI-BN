# DDA NPC locations for Bright Nights

Work in progress. This directory is not an installable mod or a playable release.

## First package: Isolated Road

Preserves Cody Miller, Jay Ruckers, all 55 dialogue definitions, both missions,
five EOCs, merchant inventory groups, mapgen, terrain, faction, and location
placement. Dialogue branches have not been removed to conceal missing features.

Run `python prepare_isolated_road.py --output staging` to restore the source
and generate initial BN map definitions. Source checksums are verified before
extraction. Mapgen rows remain unchanged; mandatory BN method fields and terrain
ID expansion are applied. Native loading and gameplay validation remain pending.

`ISOLATED_ROAD_AUDIT.json` records initial dependencies. Its item-reference
scan is conservative and includes item-group references; apparent missing IDs
are candidates for review, not confirmed missing items. `TALK_DONE` is an
engine-defined terminal topic. No unsupported dialogue effects are discarded.

## Planned packages

1. Isolated Road, weapon exhibition, associated quest items and services.
2. Island prison community.
3. Lighthouse family.
4. Militia lodge, campus library, bunker trader.
5. Godco community.
6. Hub 01 characters, missions and connected locations.
7. Refugee center, Tacoma ranch and Isherwood additions.
8. Scrap yard, lumbermill, chemist and homeless-camp differences.
9. Exodii and their dependent mechanics.

Each package needs dependency closure, BN data-loader verification, native
NPC and mission tests, and a Windows build before it is called playable.
Existing BN NPC content must be preserved when overlapping definitions differ.

## Provenance

Pinned upstream versions and the payload digest are in `SOURCE_MANIFEST.json`.
DDA JSON retains upstream authorship and CC-BY-SA 3.0 licensing. The payload
is gzip compressed and base64 encoded to make the source checkpoint portable.

## Dependency policy

Missing DDA locations, items, characters, missions and engine behavior are part of the port scope, including transitive dependencies. Do not replace them with stubs or remove their dialogue branches. The dependency checkpoint includes original quest items and scrap-trader route definitions. It is a conservative candidate set, not a mod load list.

`adapt_dialogue.py` translates constant string equality to BN variable conditions and converts NPC shopkeeper fields. It preserves unresolved math/EOC effects and reports them. Native validation remains pending.

## Dialogue adapter progress

Pinned BN condition.cpp, npctalk.cpp and npc_class.cpp were inspected. Static EOC calls are inlined with required-context and recursion checks. Constant arithmetic uses an AST allowlist, never eval. Assignments, integer comparisons and integer adjustments use BN variables. Fractional comparisons and timers remain unresolved rather than being truncated. Ammo exchange coefficients and ceil rounding, consumption-before-credit order and weapon cleanup-before-selection were checked. Upstream EOC definitions remain in the source checkpoint; generated dialogue replaces them with their expanded actions. Item consumption is already supported by this BN version. Remaining features include dynamic item awards, variable arithmetic, timers, faction relations and shop consumption policy.
