# Abandoned shopping plaza: additive DDA roofs

Status: native patch prepared; Windows generation validation pending.

Reuses the existing BN `shopping_plaza` registration and all twelve existing ground placements. The original BN shoppingplaza palette, mapgen, furniture, loot and monster generation are unchanged. Seven DDA roof terrain placements are added at z=1; two source mapgen blocks are preserved exactly, with their original null cells and roof_palette reference. There is no new invented staircase or quest.

Every nonempty roof cell was checked against BN's actual ground rows: all lie over building walls, floor, doors, windows or the existing entrance paving. None cover parking or vegetation. The roof palette and generic_city_building definition are reused from BN. No new mechanics are required.

prepare_tower_expansions.py composes the radio, hotel and plaza changes into a single city catalogue patch. check_shopping_plaza.py checks both source Git blob hashes, footprint support, exact source geometry, preservation of other city records and retention of earlier expansions. Native tests generate each of the seven roof sections; their Windows execution is pending. The portable package verifier checks the exact payload.

This does not rewrite already generated maps. Natural city placement and player traversal have not been tested.
