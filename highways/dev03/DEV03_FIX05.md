# DEV0.3 fix05

Fixes the strict JSON initialization errors from run 37957572859 while preserving
DDA highway behavior. Adds the missing field/railings terrain dependencies,
explicit road connections, nested flag conditions, special priorities and
valid trumpet bridge neighbor IDs. Predecessor-only mapgens load palette metadata
without adding or changing their ASCII rows.

The complete-generation test now clears cached overmaps because clear_all_state
only clears local map state. A separate test preserves intentional termination
against existing BN neighbors that have no highway endpoint. Tests also cover
flags versus flags_any and loaded dependency flags/priorities.

Locally passed: patch application on the post-fix04 baseline; all nine pinned
DDA geometry hashes; foundation and overpass lane/median/ramp checks; assembled
highway dependency scan; native flag helper syntax.

The workflow formats changed C++, builds both the Windows game and tests, then
runs the highway/ramp suite. Packaging only runs after native tests pass.
Until then this checkpoint is not a playable DEV0.3 release.
