# XEDRA and LIXA geometry staging

DDA c19e95bc96d27d8bef8e2e246a63cd4cd6f89974; BN c621aaf42fa182473aad10feea2b55647704dcf1. Six official source files are authenticated with SHA256. Source registrations and complete deferred content are archived. Shared roof palette comes from the existing authenticated archive.

| Site | Source special placements |
| --- | ---: |
| XEDRA Morgantown | 53 |
| XEDRA fishing shack | 6 |
| Physics laboratory LIXA | 41 |

26 world map definitions cover 50 own OMT. Morgantown includes the perimeter, rotated fence segments, forest interior, main site and road approach. Fishing-shack geometry includes three vertical levels and stock lake surroundings. LIXA includes the surface, road and guardhouse, roof, stairshafts at -1/-2, workfloor at -3, device at -4 and unfolded device space at -8.

A 27th mapgen definition preserves Morgantown's ruined tent: weighted canvas walls, canvas door, groundsheets and source random rotation are structural furniture. The source explicitly has no roof. The LIXA flat-space barrier line is preserved as structural furniture, including its coordinates; its nonstandard interaction remains a later-layer requirement. Typed reference audit covers this line in addition to ordinary glyph references.

25 raw typed obligations remain. They include special LIXA surfaces/shafts/panels, the flat-space barrier, XEDRA passcode door, metal roofs, regional forest terrain and external road definitions. No exact core/bundled-mod declaration collisions were found; semantic reuse and schema comparison remain required before integration.

The passcode door and source transforms remain intact in the archive; ordinary science cards are not substituted. The -8 device space has no fabricated stair connection to -4: access, unfolding, EOCs, traps and other events must be ported later. Device transformations, spawn updates, graffiti, items, monsters and interactions are kept outside the geometry shell.

Source rows and dimensions, reproducible extraction, hashes and Windows cp1252-default decoding were checked. All text reads/writes are explicit UTF-8. Specials have zero occurrences in staging. No native embedding, generation acceptance, player traversal claim or percentage credit. Run prepare_research_geometry.py --check.
