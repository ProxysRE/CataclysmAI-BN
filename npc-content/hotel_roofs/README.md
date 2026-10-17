# Hotel technical-enclosure roof caps

Status: prepared and checked; not yet installed in the native patch or validated in Windows generation.

The pinned DDA `hotel_tower.json` adds a z=5 cap over two technical enclosures on the main roof. This is not a fifth occupied storey. BN already has the occupied floors and the two enclosures, including stair and generator contents.

The candidate keeps all 16 BN hotel mapgen entries unchanged. It reuses DDA cap rows exactly (60 occupied cells in a 72×24 map), BN `roof_palette`, and BN `generic_city_building` inheritance. Three new terrain IDs serve all three existing hotel variants; no second hotel registration is added.

DDA places the southern roof row at overmap y=2, while BN places it at y=3 because of its forecourt. Additions are anchored to the existing BN roof terrain IDs rather than copied at DDA coordinates. Each variant gains three placements at z=5, including the empty middle map needed by the shared 3-wide mapgen layout.

`python npc-content/check_hotel_roofs.py` reconstructs candidates from pinned, checksummed sources, checks every nonempty cap cell against its BN support below, preserves every old placement and other location, and verifies composition with the radio station city candidate.

Next: compose the shared city-file edit into the native patch and validate real map generation before marking the package playable. Natural generation and player traversal have not been tested. Existing generated worlds will not be rewritten.
