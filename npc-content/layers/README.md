# Bulk community and location preparation

This layer stages eight communities together: Hub 01 (`robofac`), Godco,
campus library, militia lodge, bunker merchant, cabin chemist, lumbermill
and scrap trader. It is not an installable mod or a certified native package.

Run `python select_location_dependencies.py` and `python audit_location_layers.py`
from `npc-content` to select related shared definitions and compare placements.
Then run `python prepare_community_layers.py` to reconstruct
the exact upstream files and generate adapted staging plus a detailed report.
Run `python check_community_layers.py` to verify preservation and determinism.
Only Python's standard library and the adjacent existing adapter are required.

`SOURCE_BUNDLE.json.gz.base64` contains exact original text from both pinned
repositories. `SOURCE_MANIFEST.json` records repository, commit and Git blob
hash for every file. Extraction verifies the bundle and every Git blob before
processing. Source comments and credits remain intact (CC-BY-SA-3.0).

The first batch includes 135 DDA files (92 NPC-content files and 43 location
files) and 34 BN reference files. Location selection follows verified file
names; shared overmap-special files and all transitive dependencies are not
included automatically. This is intentionally an incomplete BN baseline.

The converter applies existing dialogue transformations per definition,
inlines supported EOC calls, and sets mapgen's JSON method. If a definition
cannot be adapted, its original is preserved and its reason is reported.
It does not delete a quest or substitute an empty response to get past errors.
Successful conversion alone does not certify unknown keys or DDA map schemas.

`LAYER_SUMMARY.json` gives counts and common blockers. Regenerated
`LAYER_REPORT.json` additionally records definition-level blockers, overlapping
BN IDs, selected typed references and their providers. External references
mean "outside the selected sources/baseline", not "absent from BN".
Item, terrain-symbol, trait, inheritance and implicit engine dependencies need
separate closure; the selected-reference report is not a full dependency graph.

No batch definitions are inserted into the native patch. Promotion requires
reviewing shared-ID merges, dependency closure, native load and gameplay tests.
Hub 01's existing BN characters and Godco content must be preserved during
merging. Full raw/staged trees and detailed reports are reproducible from the
bundle rather than duplicated in version control.

## Linked-location expansion

The expanded source bundle contains 214 exact pinned files (160 DDA, 54 BN).
Current staging selects 1,767 definitions from 158 DDA files: the original
eight communities, directly related maps, and 109 definitions selected from
shared files. Selection follows typed references, inheritance, OMT-to-mapgen
links and the reverse link from a community map to its overmap special.
Cardinal direction suffixes resolve only when the corresponding base ID is
actually indexed; multi-OMT map grids expose every tile in the index.

Fourteen placement layouts are audited, including New England Church Retreat,
Hub 01, the campus variants, militia lodge, occupied chemical lab, occupied
scrap yard, occupied lumbermill and the bunker merchant site. Selected map
coverage includes the Hub's radio tower, ventilation shaft and microlab
connectors, plus the quest-linked Exodii warehouse. Some generic terrain and
subway generators remain outside the selected catalog.

`LOCATION_SUMMARY.json` records exact DDA/BN layout counts, floor ranges,
coordinate differences, camp metadata and map coverage gaps. Placement-only
constraints without an `overmap` field are preserved and reported separately;
they are not mistaken for generated terrain tiles. Detailed graph edges and
selected-source indices are regenerated in `LOCATION_LINK_REPORT.json`.

The Hub comparison is 100 explicit DDA terrain cells versus 69 in pinned BN.
BN already has underground layers; the source DDA layout additionally contains
z=-1. These are placement-data facts, not a certified generated world.

Known blocked definitions now number 68 in this expanded batch. This includes
new EOC declarations requiring native lifecycle support, so the number is not
directly comparable with the earlier 63 blockers in the smaller batch. Item,
monster, palette and native schema closure remains incomplete. No bulk data
has been silently promoted into the native game package.

Run `python check_location_layers.py` and `python check_community_layers.py`
after source/selector changes. They check selective extraction, source
preservation, placement coordinates, real BN comparisons and determinism.

## Existing BN locations are merge targets

Run `python check_location_merge_plan.py` to compare IDs and mapgen contents
against BN, including files whose paths differ from DDA. The baseline now
includes all 12 JSON files in BN's overmap_special directory, plus the occupied
lumbermill and chemical laboratory maps. External definition locations and
unselected mapgen files still require review; absence from this selected map
baseline does not authorize adding a new definition.

Six sites are explicit merge targets: Lumbermill, Occupied Lumbermill,
Occupied Chem Lab, Occupied Scrap Yard, the bunker merchant site and Hub 01.
Their original occurrence must survive. Eight other layouts remain new-site
candidates pending native and full identity checks; none is installable by
this planner. Alternate BN names sharing dedicated map IDs become review
candidates instead of being treated as new sites automatically.

Mapgen comparisons preserve complete BN variant sets, including when a DDA
variant already matches one of them. Current output has seven matching source
variants to retain and 77 comparisons requiring review of existing variants.
The chemical-lab roof matches; the occupied lumbermill's rows, NPC placement
and other sections differ, so NPC coordinates cannot be copied blindly.

`LOCATION_MERGE_SUMMARY.json` preserves review targets and representative
differences. The complete per-map variant plan is regenerated as
`LOCATION_MERGE_PLAN.json`. Duplicate-prone additions are checked in fast CI.
