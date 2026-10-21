# Urban geometry staging

Pinned DDA: `c19e95bc96d27d8bef8e2e246a63cd4cd6f89974`.
BN reference: `c621aaf42fa182473aad10feea2b55647704dcf1`.

| Location | Own overmap cells |
| --- | ---: |
| Large police department | 30 |
| Textile mill museum | 18 |
| Supermarket | 18 |

14 world map definitions, three structural roof utilities and the police gym overlay preserve source rows. Source southern-wing rotations, vertical levels and two supermarket road-frontage constraints remain archived. City registrations are retained verbatim separately; staged special candidates have zero occurrences.

The extractor separates furnishings, loot, inhabitants and interactions. Exact declaration checks found no core or bundled-mod collisions; this does not imply that BN lacks similar police stations or shops.

## Remaining before native integration

Of 22 raw missing terrain references, 21 wall paint variants now reuse existing BN walls of the same construction (domestic, concrete, solid concrete, reinforced concrete). This intentionally loses unavailable paint colors and adopts BN material mechanics; it does not replace reinforced concrete with a domestic wall. Every conversion and reference count is recorded. The crosswalk `t_zebra` remains unresolved pending a supported pavement/marking choice.

The police gym overlay is now expanded from authenticated domestic/carpet palettes and retained as a namespaced structural nested chunk, including its carpet terrain and placement. Gym furniture and loot remain deferred. Source roof infrastructure and merchandise nests remain later-layer content; three terrain-bearing roof utility chunks are retained.

This is source staging, not a playable completion claim. Not embedded in the native preview or current Windows patch. Schema/loading, generation, stairs and access checks remain required. No first-layer percentage credit is added.

Run `python npc-content/prepare_urban_geometry.py --check` to verify source hashes, row dimensions, exact declarations and reproducible extraction.

## Adapted crossing

`adapt_urban_geometry.py` now produces a separate adapted shell with zero unresolved typed references. The isolated white pedestrian crossing copies the complete authenticated BN pavement definition and source DDA presentation. BN pavement connections and dirt after destruction replace DDA zebra grouping and null destruction terrain. Source files and differences are recorded in `urban_adaptation_sources` and `URBAN_ADAPTATION_REPORT.json`. Run the adapter with `--check`. Native preview embedding, parameter loading and generation remain pending.
