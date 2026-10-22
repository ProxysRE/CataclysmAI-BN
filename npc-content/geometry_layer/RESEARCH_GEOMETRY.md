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

## Physical adaptation prepared

The separate adapter now produces 19 concrete terrains and one structural furniture definition, with zero unresolved typed references. Ordinary ground, regional vegetation and components reuse reviewed BN identifiers. BN metal flat roof retains the metal material; red paint is lost. The source concrete roof uses BN reinforced-concrete flooring without an additional roof. Generic metal wall mechanics replace corrugated metal, and straight BN road context replaces forest-road context. Each change is listed in the adaptation report.

Special device surfaces, shafts, luminous carpet, four reader types and the XEDRA passcode door retain complete source physical definitions under isolated IDs. The three-state wall destruction cycle, thresholds, coverage, movement, roof links and light values are preserved. BN wire/steel_chunk replace DDA metal component tiers in deconstruction. The road abstract is expanded from the authenticated catalog, retaining the compatible BN generic_transportation parent. Generated road_ns is justified by the pinned BN road LINEAR declaration.

DDA actions, shooting objects, emissions, cutting tools and unsupported display connections are archived. Reader and ledge examination are disabled in the geometry candidate; scientific-card or ordinary-elevator behavior is not substituted. Existing GOES_DOWN markers do not certify source pseudo-ledge behavior. Component transitions and all source item references are checked, including the three-state destruction cycle.

This closes static references, not native loading, combat or traversal acceptance. No native preview or engine-patch change is included in this preparation step. Run adapt_research_geometry.py --check.

## Opt-in native preview prepared

Morgantown, the three-floor fishing shack and every LIXA source placement are now embedded in DDA_Geometry_Preview. All source natural registrations remain archived; preview occurrences are zero. The fishing-shack upper floors use the same isolated air-only BN placement predicate as the pottery cottage. Predecessor maps remove ambient items only on source terrain-painted cells.

The native fixture includes 2,383 deterministic terrain expectations, with directional coordinate rotation, and all 16 cells of the LIXA structural furniture barrier. The preview totals 29 layout cases and 823 source-special placements (plus four helicopter context cells). A separate audit checks C++ fixture coordinates against payload registrations before compilation. Source/installed native generation is pending. Physical reader/shaft surfaces do not implement passcodes, pseudo-ledge traversal, unfolding or device events. No invented access joins the -4 and -8 regions, and no additional progress percentage is claimed.

## Automatic roof compatibility fix (2026-10-23)

Windows run 39829689355 compiled and passed the 73 core /11,030 assertions and 10 optional-mod /2,224 assertions. Geometry initialization rejected five LIXA roof links: t_strconc_floor_no_roof is a walkable BN floor, but its bash definition does not allow bashing from below. It is therefore not a valid automatic roof provider under the pinned BN terrain checker. Installed suites and packaging were not reached.

Those five automatic links now use the existing BN t_flat_roof, with its stock destruction behavior. Explicit walkable concrete-roof surfaces keep their previous reinforced-concrete floor counterpart. The three-state LIXA wall destruction cycle, wall thresholds, source rows, terrain IDs and device placement are unchanged. Authenticated BN roof definitions support a precompile check of every custom preview terrain: a referenced roof must have no further roof and must permit bash_below. Regression probes reject the old floor provider and recursive roof chains. Windows source/installed rerun remains required.
