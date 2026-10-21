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
