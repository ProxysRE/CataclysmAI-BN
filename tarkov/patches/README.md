# Engine patches for the pinned BN baseline

Baseline: 554950f3635f50ddd1d32c6e1b6e2bdee9842bd6.

0001 restores saved pocket bounds to the destination dimension's mapbuffer before
load_map binds the reality bubble to it. The previous m.get_mapbuffer() selects the
old dimension on a cold load. The unchanged three-process regression verifies all
six boundary faces before continuing the raid and cleanup.

install_into_bn.py applies this production patch with and without --tests. Rebuild
the game after installation. The test-driver changes remain test-only. Save format
is unchanged. Patch application is checked against the exact pinned source. Linux runtime
validation passed in run 39511333415 at project commit
da9189db992697e2f45349420c1512a59a8f1e9c; Windows UI validation is pending. A passing same-process reload does not cover this defect.


0009 adds Npc:avoid_immediate_danger(), called after the NPC cache refresh.
It executes only an immediate field/explosive response and returns a reason,
without re-entering the general NPC selector. Used before project search/combat
dispatch; the search deadline and attempt budget remain untouched.
Application against pinned sources is checked; native results are recorded in
docs/VERIFICATION.md. This does not expose a general tactical planner.


0010 records anonymous coarse hearing events for lua_ai=TRKV_PATROL before
vanilla source-identity lookup. The existing sound pipeline still determines
audibility. A saved Creature value carries dimension/time/4x4-region/floor/kind;
Lua owns deduplication and bounded investigation. Vanilla classes are unchanged.
Native results and limitations are tracked in docs/VERIFICATION.md.


0011 adds Npc:choose_area_entry(minimum, maximum), a bounded read-only route
query for inclusive same-floor areas up to 4x4. It returns a safe unoccupied
reachable endpoint without changing NPC.path or moves. Hearing owns the plain
selected point and retries under the existing search budget. Native results
are tracked in docs/VERIFICATION.md.


0012 adds a bounded read-only visible-target standoff position evaluator.
The trained-rifle Lua pilot owns the saved intention, timeout and cooldown;
BN still executes movement, shooting and reload. This is a local spacing move,
not a cover/flanking planner. Native results are tracked in VERIFICATION.md.


0012 also accepts an optional third boolean for short firing-lane recovery
at visible-target range 4-12. It requires a blocked current geometric shot
and returns a reachable clear alternative. The saved goal kind selects the
validation policy. Both modes reject dangerous fields along the planned route.
This does not replace BN's spread/friendly-fire checks.
