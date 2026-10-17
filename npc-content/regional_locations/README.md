# Bulk regional location transfer layer

Five complete source site groups are preserved at the project's pinned DDA revision. These files are **source staging candidates, not installed directly**. The separate karting adaptation is prepared for native validation; the other four groups remain staging. See the native integration checkpoint below.

| Group | Mapgen definitions | Terrain slots | Source placements |
| --- | ---: | ---: | --- |
| Small island lighthouse | 6 | 6 | lighthouse_island_small |
| Large karting circuit | 3 | 27 | o_karting_l |
| Farm supply, normal and looted | 4 | 12 | Farm Supply Store / Looted |
| Nursing home, variants and underground complex | 10 | 66 | nursing_home / nursing_home_sh |
| Retirement community, wings, park and sewers | 22 | 124 | retirement_community |

45 mapgen definitions comprise 38 terrain mapgens and seven nested templates; 235 slots include multiple elevations and alternate variants. This is not 235 newly installed buildings. Source placement rules and terrain declarations are included; additional stock cells referenced by placements are not duplicated as new content.

The nursing-home source includes all 59 computer dialogue topics and four EOCs. The karting candidate includes the actual source `go_kart` definition; other vehicles from its source file are excluded. The small lighthouse was already present in earlier source staging; this layer brings its full geometry and dependency accounting into the common pipeline, not a second native copy.

## Reproduction

Run `python npc-content/prepare_regional_locations.py --check` and `python npc-content/check_regional_locations.py`. The checks reconstruct the checksummed source bundle, rebuild all candidates and compare source rows, terrain matrices, rotations and explicit placements. They do not establish BN runtime compatibility.

Site-local palettes are expanded into mapgen objects, in source order, preserving dictionary overrides and accumulated placements. Shared palettes remain explicit dependencies. Scoped parameters, region terrain, furniture mechanics, ramps, computers, nested references, vehicle parts and placement connection syntax still require BN adaptation. Source EOC and dialogue definitions are retained unchanged; their presence is not an implemented engine bridge.

`--bn-source <pinned-BN-checkout> --report <file>` adds a full core JSON **ID audit**. CI uploads the report. The scanner covers explicit mapgen reference positions listed in the script, not every transitive reference in dialogues, effects, vehicles or item groups. Matching BN IDs require semantic review; unresolved IDs under a scanned namespace are obligations, not proof of total content absence. In particular, vehicle group versus vehicle identity must be resolved before installation.

## Next integration gates

- Resolve shared palettes and nested maps without replacing existing BN definitions globally.
- Close equipment, monster, vehicle and computer-script dependencies, including the nursing-home laboratory content.
- Use BN counterparts where equivalent; port source definitions and engine support where needed. Do not replace working machinery with decorative objects.
- Adapt numeric vision, road connections, scoped parameters and region aliases using the established BN loaders.
- Enable each coherent site only after native load, generation, vertical-connection and placement tests pass.

## Native integration checkpoint

The karting circuit now has a separate BN adaptation in `prepare_karting.py` and `native/dda_karting_circuit.json`. See `karting/PORT_REPORT.json` for the compatibility limits. Its native build/runtime result is pending. This folder continues to preserve source staging candidates; the other four groups are not enabled.

The dependency audit also accepts `--native-payload npc-content/native/dda_karting_circuit.json`. It records common port-provided groups separately from stock BN definitions, so future farm-shop cash loot can reuse the adapted cash register groups. The user requested stock BN currency only: all imported cash uses existing `money_bundle`; DDA denominations and coin/banknote groups are not installed.
