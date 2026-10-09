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

## Dialogue adapter and native compatibility

The adapter retains all 55 topics and both missions. It expands 126 static EOC
calls with required-context and recursion checks; originals remain preserved.
Constant assignments use BN variables. All numeric reads and updates use a
bounded expression IR: BN's integer variable handlers otherwise truncate
fractional credit. 134 arithmetic occurrences now use the bridge, including
prices, timers, timestamps and variable existence checks.

All 24 item rewards, two dynamic payments and two dynamic affordability checks
now target native handlers. Item IDs may come from dialogue variables. Charge
rewards receive the exact requested amount; ordinary rewards load default
ammunition and drop nearby when the player lacks carrying capacity. Payments
validate the complete amount before removing items and transfer ownership to
the NPC. Invalid IDs, nonnumeric, fractional, negative and overflowing counts
are rejected. These handlers cover the options present in the pinned artisan
source; the adapter raises errors for other options instead of discarding them.

Run `python check_artisan_adapter.py` after source preparation/adaptation.
Run `python build_engine_patch.py --bn-source /path/to/pinned-bn` to restore
staging from the exact BN commit, rebuild the engine patch and update only
its workflow checksum. The Windows workflow formats touched files, builds both
the game and Catch tests, and runs `[dda_npc]` with real avatars and NPCs.
It retains the existing build when a newer checkpoint is pushed. It does not
publish a playable NPC package yet.

Locally verified: adapter regression checks; C++23 evaluator checks; item bridge
syntax against pinned BN headers; patch applies to the pinned base. Full native
reward/payment, fractional-credit and timer tests await Windows CI.

Four nested armor-selection switches now preserve DDA threshold semantics:
the last qualifying case in source order wins, including fractional thickness
values. Native tests cover below-threshold, exact fractional boundaries and
source order. Response-level boolean switches remain BN response switches.

Still required: the measurement activity, faction sharing/trust, shop consumption policy, typed dependency
closure, modern DDA item/mapgen schema adaptation, and full quest/location tests.
The generated dialogue is not yet an installable mod.
