# Large-site geometry: platform, stadium and skyscraper

Pinned DDA c19e95bc96d27d8bef8e2e246a63cd4cd6f89974; BN c621aaf42fa182473aad10feea2b55647704dcf1. New source files are preserved verbatim with SHA256; reused house/roof palettes and rooms are authenticated against their existing pinned manifests. Standalone staging only, not installed native content.

| Site | Source placements | Source z levels |
| --- | ---: | --- |
| Football stadium | 145 | 0 through +5 |
| Office skyscraper | 44 | -1 through +9 |
| Oil platform | 204 | -9 through +7 |

32 world-map definitions cover 307 distinct own OMT. The source room/roof graph preserves 291 nested definitions with 189 identities, including weighted alternatives and shared residential rooms. All rows, dimensions, coordinates and source nesting weights survive. Original city registrations and later furniture, loot, actors and events remain in LARGE_SITES_LATER_LAYERS.json and the authenticated archives. No empty buildings are added to normal worlds.

Physical adaptation closes 31 initial typed obligations. BN counterparts supply ordinary carpets, roofs, wall construction and truss supports. Four concrete terrains preserve the inactive drilling machinery, surface/submerged drill strings and salt-water cube. Steel component tiers reuse BN steel_lump/steel_chunk; pipe_fittings drops use pipe with the same source counts. Salt water uses the complete BN water-cube terrain plus native SALT_WATER and ordinary collection; DDA collection temperature is excluded. Unsupported OCEAN overmap flags are archived, not replaced with a misleading supported flag.

Two source greenhouse variants place their roofs with nested z=+1, which pinned BN does not support. Their offsets remain intact and explicitly block native integration of the affected nested graph. They must not generate a roof on the same floor as the greenhouse walls. Separately, BN has no ocean overmap terrains/placement predicates: platform source ocean_surface/ocean_water_cube/ocean_bed context needs an explicit BN habitat adaptation before loading a preview. No global ocean system is claimed or planned by this staging.

Local checks cover exact source placements, all 291 weighted nested variants, complete custom terrain fields, supported overmap flags, collision/reference closure, ordinary BN salt-water collection declaration and retention of both roof-offset blockers. Runtime loading, generated floors, access and destruction remain unverified. No native patch change or progress credit. Run python npc-content/check_large_site_geometry.py.
