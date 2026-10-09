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
