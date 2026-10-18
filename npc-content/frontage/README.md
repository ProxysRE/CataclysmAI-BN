# Fixed-special placement constraints

Pinned DDA source separates two effects of a fixed-special cell: required_locations includes all cells, while place only changes a cell when its terrain is not NULL_ID. Three eldercare frontage cells use only point/locations, intentionally constraining placement without assigning terrain.

The pinned BN fixed-special implementation already retains the full constraints and applies rotation in can_place_special, but its placement path writes every cell's terrain. prepare_frontage.py adds the missing DDA behavior to that existing class. No special-specific placement algorithm or invented road tile is added.

Changes are confined to fixed_overmap_special_data:

- Ignore only null terrain in the terrain-validity check. Unknown nonempty terrain IDs still trigger the existing error; duplicate coordinates and empty/invalid locations retain their checks.
- Keep required_locations exactly unchanged, including constraint-only cells.
- Skip null terrain before placement, occupied-tile recording and blob expansion.
- Filter null terrain out of all_terrains (used for mapgen parameter finalization) and map preview, since it is not a generated or drawn tile.

The connection and rotation systems remain BN's existing mechanisms. Source special road coordinates/from hints are not deleted or replaced. The native test uses the public overmap::can_place_special and place_special APIs for all four rotations: water at the constraint-only cell rejects placement; field allows it; the assigned cell changes to forest; the frontage stays field and is absent from the occupied-tile result. A second test captures expected errors for unknown terrain, duplicate point and invalid location. Test overmaps are heap-allocated for Windows stack limits.

Source bundle includes the complete pinned BN overmap.cpp/public special header and DDA overmap_special_fixed.cpp/overmap_special.cpp. SHA256 guards reconstruct it; the Windows workflow compares the pristine BN files before applying the patch. DDA's other unrelated systems and vector/preview APIs are not copied wholesale.

This bridge is prepared, not native-validated yet. The complete eldercare maps remain candidate files; their initialization, full mapgen, stair/elevator alignment, source population counts and installed behavior still need validation before world placement is enabled.

The source audit also confirmed that BN already has GLOBALLY_UNIQUE world tracking and rejection. Elder-care candidates now preserve that flag rather than unnecessarily weakening it to UNIQUE. The prior map-layer description was too conservative on this point and is superseded.
