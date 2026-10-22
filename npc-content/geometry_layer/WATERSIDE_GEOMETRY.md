# Waterside geometry staging

Pinned DDA c19e95bc96d27d8bef8e2e246a63cd4cd6f89974 and BN c621aaf42fa182473aad10feea2b55647704dcf1. Source hashes are in waterside_sources/SOURCE_MANIFEST.json; domestic and roof palettes reuse authenticated archives.

| Site | Special placements |
| --- | ---: |
| Pottery cottage | 8 |
| Hot springs | 1 |
| Sunken helicopter | 10 |

Eleven own OMT and eight mapgen definitions preserve multilevel layouts. Some special placements use stock surrounding river/lake OMT. The nether lake-bed entry only retains its predecessor; its inhabitant belongs to a later layer. Loot-only glyphs on predecessor maps use null furniture to preserve the underlying lake floor. White linoleum uses the source fallback, matching the existing gray-fallback policy. Both color variation and source flags remain archived.

29 raw typed references remain, including generated directional river identity, unavailable wall colors, helicopter materials and hot water. Exact core/bundled-mod declaration overlaps are zero; this does not prove semantic uniqueness. Hot-water behavior and wreck terrain must be compared against BN before integration.

Native schema, generation, player traversal and later content are unvalidated. Occurrences are zero in candidates. Source registrations are preserved verbatim. Run prepare_waterside_geometry.py --check. No percentage credit.

The cottage firepit_5x5_2 nested fragment requires source geometry review before native integration; its placement is retained in the later-layer archive.

## Adaptation prepared

`adapt_waterside_geometry.py` closes all typed terrain references. Sixteen concrete wreck terrain definitions reuse complete BN metal-floor, junk-floor, metal-wall, half-wall and window parents. Source underwater flags and presentation are retained. Quarterpanel bash quantities use BN steel_chunk; source DDA window shoot schema is archived while the stock BN window ranged behavior remains. Same-material BN walls replace unsupported paint colors.

The firepit nested fragment paints tree trunks; it is now expanded from the authenticated garden palette, isolated and retained in geometry. Seating, fire ring and stockpile remain later-layer content.

A seventeenth concrete terrain retains hot-water movement, water flags and heat_radiation=1. BN does not load DDA liquid_source/min_temp. The source temperature field is archived but intentionally excluded by user decision. The ordinary BN water_source action supplies stock untreated water; no collection-temperature feature is planned.

The adaptation report includes 148 deterministic underwater/navigation expectations, with random-rotation invariance filtering. river_north is explicitly classified as a generated BN river identity. Zero typed obligations does not imply successful native schema loading or game generation. No native patch was changed in this preparation step. Run the adapter with --check.

User scope decision (2026-10-22): do not port DDA collected-water temperature. Stock BN water collection is enabled and thermal collection is not a release gate. Waterside input and output use explicit UTF-8; the old Windows cp1252 row-width failure is reproduced and the corrected extractor passes under a simulated cp1252 default.

## BN overmap classification

DDA's generic WATER flag on hot_springs is unavailable in pinned BN. It is archived without a replacement classification; local water terrain and collection are preserved. LAKE and RIVER have distinct BN semantics and are not substituted. The complete preview's overmap flags are checked against the authenticated BN overmap.h registry before compilation.
