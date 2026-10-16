# Lighthouse community for BN

Status: Windows checkpoint 962aeb067147586280ed44514099bc18e391c242 passed run 38803907775: 20 native test cases, 798 assertions. The loader initializes successfully. This is a tested development checkpoint, not a certified playable release.

## Included

The native patch loads 41 actual definitions: four NPC templates, seven missions, 26 topic definitions, a class, shop group, fisherman_family faction and survivor map update. It augments one matching BN shore-dock layout with the original DDA 25:75 encounter weights and the 1x1 fisherman spawn chunk, preserving all five BN dock definitions.

Tests cover actual template/mission loading, follow-up links, cleanup and repair conditions, NPC timers/counters, dynamic line branches, additive BN topic loading, engineer expertise, faction ledger save compatibility, survivor placement, canoe/light update payloads and family dialogue outcomes.

## Remaining release gates

A complete quest walkthrough must still verify start/end callbacks, actual family rescue and turn-in, natural dock generation, and saving/reloading across the quest chain. The isolated boat/light payload tests verify modifications, not the complete mission routing. Full Windows packaging remains pending.

## BN compatibility

Use the existing BN lighthouse maps, house_04_basement rescue destination, engineering traits/groups, canoe and t_floor_olight. Reference snapshots preserve their pinned definitions; do not install competing DDA copies. The larger source/staging collection includes small lighthouse and camp data for later review, outside the currently validated native package.

Faction ledgers preserve 64-bit calories, vitamins and expiry. Existing BN stock text/color reads their calories; no new consumption or aging simulation is enabled. Camp consumers are deferred until needed by functioning restored camps.

Place the community JSON under data/json/npcs. Loading it from the root JSON directory constructs NPCs before options, enchantments and terrain are ready, causing initialization errors even when later assertions pass.

## Reproduction and evidence

Run prepare_lighthouse.py, check_lighthouse_links.py, check_lighthouse_encounter.py and build_lighthouse_native.py from npc-content. Rebuild the native patch using build_engine_patch.py with the pinned BN source checkout. Source selections and aliases are recorded in SOURCE_MANIFEST.json.

VALIDATION.json records the exact successful commit, run and artifact hashes. Run check_validated_checkpoint.py to check that the current native patch and community data still match that evidence. After changes, passing static checks alone does not renew native validation.

Official pins: DDA c19e95bc96d27d8bef8e2e246a63cd4cd6f89974; BN c621aaf42fa182473aad10feea2b55647704dcf1. Upstream credits and CC-BY-SA-3.0 apply to preserved DDA content.

Pending lifecycle extension: native tests now assign the actual cleanup, boat and repair missions and execute their real start/end callbacks through mission::assign and wrap_up. Boat coverage includes 249/250 nails, mission save/load, resource consumption, route-based canoe creation and follow-up ID. Cleanup covers NPC-owned counter initialization, completion at seven and post-turn-in cleanup. Repair covers the ready-to-yes flag transition, z=5 light placement and survivor timestamp. Real survivor NPC serialization also checks identity, faction, topic and timer/counter variables. These are pending tests, not additional passing evidence; VALIDATION.json continues to identify the earlier successful artifact.

Family rescue compatibility: the adapted mission explicitly sets target search `z: -1`. Pinned BN's mission target finder otherwise searches the player's current layer, so a surface conversation cannot locate the existing `house_04_basement`. This is a mission-specific data adjustment; global BN search behavior is preserved. The source `MGOAL_ASSASSINATE` remains unchanged: it detects the targeted mother's death, while successful rescue is completed explicitly by dialogue.

The pending native rescue test assigns the actual mission from the surface, verifies its underground target and both spawned family members, runs their first-meeting effects twice to check the sentinel, and executes their arrival responses at the lighthouse. It checks that both protection missions close, both safe flags are set, and the father's success response completes the family mission and exposes the boat follow-up. This fixture moves NPCs to the destination; pathfinding and a manual escort remain release checks.

Run 38915686091 compiled successfully but failed native rescue tests: stock BN's `npc_at_om_location` tried to instantiate an unrotated `oter_id("lighthouse_ground")`. Ported conditions now use the actual OMT's type ID, matching DDA's orientation-independent check without changing the stock BN condition. Camp location sentinels remain explicitly unsupported. A four-orientation regression was added. Test fixtures also reset avatar missions between cases and unregister rescued NPCs even on assertion failure; the previous failed rescue contaminated later dialogue expectations. Replacement Windows validation is pending.
