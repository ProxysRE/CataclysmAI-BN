# DDA radio tower expansion for existing BN stations

This is a replacement of the two existing BN station maps and city-building registrations, not a new competing station variant. The six DDA tower mapgen IDs and one explicit BN-style OMT definition are added in dda_radio_station_towers.json. Each station gains the source alternating tower levels z=2..6.

The ground-floor buildings, computer objects, stock, toilets, furniture, frequencies and original roof ladders remain BN definitions. Only existing tower foundation cells are cleared, four relocated support poles and an access ladder are placed in pavement, and the tower footprint is added in previously empty roof cells. The first DDA tower moves (+10,-12); the second moves (-6,-8). Directly copying DDA coordinates would overlap BN buildings.

Existing BN roof utilities, roof palette, radio-tower encounters and their dependencies are reused. DDA encounter weights are retained at the tower tops. BN's existing tower visibility value 2 is retained instead of importing the unsupported DDA vision-level schema. New terrain definitions are explicit; no forward parent inheritance is required. The BN roof palette has no v ladder binding, so the top maps bind it explicitly.

prepare_radio_stations.py rebuilds replacements from checksummed pinned sources and the existing full location catalog source bundle. The Windows preflight compares every replaced/reused file and checks all core mapgen and OMT files for ID conflicts. The native patch synchronization guard checks both replacements, payload and native test. The portable installer verifier checks both installed maps and the new payload.

Static checks verify preservation of every unrelated city building, exact BN station fields outside the reviewed coordinates, source footprint bounds, aligned access on all seven levels and existing encounter IDs. Native tests request real generation for both variants in all four orientations, check ladder terrain and movement flags on all seven levels, and reload the generated map through the shared map buffer. This is not a cross-process world-save test.

Status: code and static checks prepared; native Windows compilation/generation, full world-save/reload, natural city placement and playtesting pending. Existing generated maps are not rewritten.
