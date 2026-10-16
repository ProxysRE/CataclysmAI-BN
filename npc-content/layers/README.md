# Bulk community and location preparation

This layer stages eight communities together: Hub 01 (`robofac`), Godco,
campus library, militia lodge, bunker merchant, cabin chemist, lumbermill
and scrap trader. It is not an installable mod or a certified native package.

Run `python prepare_community_layers.py` from `npc-content` to reconstruct
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
