# Urban geometry staging

Pinned DDA: `c19e95bc96d27d8bef8e2e246a63cd4cd6f89974`.
BN reference: `c621aaf42fa182473aad10feea2b55647704dcf1`.

| Location | Own overmap cells |
| --- | ---: |
| Large police department | 30 |
| Textile mill museum | 18 |
| Supermarket | 18 |

14 world map definitions and three structural roof utilities preserve source rows. Source southern-wing rotations, vertical levels and two supermarket road-frontage constraints remain archived. City registrations are retained verbatim separately; staged special candidates have zero occurrences.

The extractor separates furnishings, loot, inhabitants and interactions. Exact declaration checks found no core or bundled-mod collisions; this does not imply that BN lacks similar police stations or shops.

## Remaining before native integration

22 raw terrain references need BN adaptation, primarily parameterized wall colors and a crosswalk. The police gym nested fragment also paints a carpet tile: its complete authenticated source is archived and explicitly deferred, rather than treated as furnishing alone. Its palettes must be resolved before embedding. Source roof infrastructure and merchandise nests remain later-layer content; three terrain-bearing roof utility chunks are retained.

This is source staging, not a playable completion claim. Not embedded in the native preview or current Windows patch. Schema/loading, generation, stairs and access checks remain required. No first-layer percentage credit is added.

Run `python npc-content/prepare_urban_geometry.py --check` to verify source hashes, row dimensions, exact declarations and reproducible extraction.
