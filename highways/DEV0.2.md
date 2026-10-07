# Highway DEV0.2: grade separation preview

Applies after the tested DEV0.1 foundation on BN c621aaf42fa182473aad10feea2b55647704dcf1.

North/south highways pass above east/west highways at their 2x2 crossing. Both
carriageways ascend together before the crossing and descend together after it.
The lower highway retains its 15-square carriageways and closed central median.

Selected local-road crossings pass beneath the highway. Crossings separated by
up to three overmap squares share one elevated segment. The first eligible local
crossing in each 24-square district remains an at-grade access point. Other
crossings remain at grade where there is no safe approach space. An approach
never replaces a retained local road. Dedicated interchange exit ramps are not
implemented in this preview; the highway's approaches change its elevation.

All raised sections begin and end within their overmap. Water and existing
upper-level specials block elevation. Paired water crossings now reserve a flat
bridge for both highway halves and cannot turn into a surface local intersection.
Longer raised water bridges and highway routing around towns remain future work.

Mapgens reuse BN's vehicle ramp terrain and concrete bridge deck terrain. New
IDs are additive: DEV0.1 IDs remain available for existing saves. Generated
terrain is not retroactively replaced. Test in a new world with BN_HIGHWAYS on,
spacing 3, or in previously ungenerated territory. Keep world options unchanged.

Validation:

- `python utilities/highway/check_mapgen.py`: original foundation geometry.
- `python utilities/highway/check_overpasses.py`: all 32 new mapgens, lane widths,
  medians, paired slopes, unobstructed lower roads and rotated geometry.
- `g++ -std=c++23 utilities/highway/check_elevation.cpp -o check_elevation`:
  standalone planner checks across 10,000 reproducible layouts and the original
  test save's crossing coordinates.
- Build the game and `cata_test-tiles`, then run `[highway],[vehicle][ramp]`.
  Native tests explicitly enable real mapgen and drive a motorcycle over the
  generated approaches in both directions for all four carriageway templates.
