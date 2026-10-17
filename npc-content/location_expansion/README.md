# Existing-location expansion

The source bundle preserves 25 pinned BN/DDA files with SHA256 and Git blob identities. `prepare_location_expansion.py` reconstructs reproducible replacements; `check_location_expansion.py --bn-source <checkout>` rejects source drift before applying the native patch.

## Nuclear station: a BN location, not a new import

The nine main floor layouts (-1 through +7) have identical row geometry. BN deliberately uses its own grid generators and train. The native patch adds only the 24 DDA river-bank cells at x=2..13, y=8..9, z=0. It retains all 684 existing special cells, road connections, occurrence limits, flags, palettes and mapgen. The result has 708 cells. DDA-only hazmat roof IDs and constraint-only placements are deferred, not invented or dropped without a record. The report includes semantic differences for all 12 corresponding files.

This uses stock BN rotating river terrain and stock special generation. No new engine behavior or second nuclear special is introduced. Existing generated terrain is not rewritten. Natural generation and Windows regression for this revision are pending.

## Hub 01: complete replacement candidate, not installed

The candidate merges DDA geometry at matching coordinates, retains the existing BN special ID and generation policy, and expands 69 placements to 102. It has 33 additions and two changed placements; there are no BN-only placements in these pins. Five exact DDA mapgen/palette/terrain files accompany the candidate. They are raw source awaiting adaptation, not a runnable mod.

The new -1 level is a security foyer/control area; the source already has deeper residential, research and technical levels. NPC definitions, missing loot and furniture, elevators, stairs, schema compatibility and mapgen tests must be reconciled as one coherent package. The candidate is deliberately outside the native patch and portable installer. Its `installable` and `native_patch` markers stay false.

A source or geometry change fails the guard and requires review. The package verifier checks the installed nuclear replacement, so CMake cannot quietly ship the old special.

## Hub access projection

`audit_hub_access.py` projects all static multi-OMT maps into one coordinate system, including negative origins and maps reused on multiple floors. It resolves the robofachq palette and explicit terrain overrides. `HUB_ACCESS_REPORT.json` lists all projected controls, stairs, ramps and omitted map slots. This is a static map audit, not native generation validation.

Ten additional pinned source files are preserved in ACCESS_SOURCES with manifest hashes and verified upstream Git blob identities. BN elevator transport should be retained. Its existing Lua hook can deny access but cannot choose a directional destination. Mapping the DDA restricted panels to an ordinary BN elevator is explicitly blocked. All six directional controls have a nearby shaft at their required destination. Four stair endpoints still have no opposite stair within the projected destination OMT; external maps and generation need review. The other 24 of 28 endpoints have a candidate under stock BN lookup rules.

## Native elevator access bridge

The native patch now adds the exact source hidden ancillary trait, mutual exclusion with the existing BN marshal trait, and two terrain definitions materializing the exact pinned BN elevator-control properties. Registered up/down handlers require the credential and choose only the adjacent floor. They reuse the existing BN elevator path, including the Lua permission hook and item/creature/vehicle transfer. The ordinary elevator menu is preserved for existing public controls. Fixed-floor travel refuses an empty source platform or a destination containing any non-elevator terrain. This deliberately retains BN platform transport rather than DDA single-actor teleport. No generic EOC interpreter is introduced for these panels.

Windows compilation and native policy/binding regressions are pending for this revision. Full-map generation and actual elevator travel with cargo/companions still require runtime tests. This bridge does not install the expanded Hub maps or mark the entire Hub port complete.

The first native run compiled successfully but the panel-registration test found missing terrain IDs. Terrain copy-from definitions in the root JSON were encountered before their parent file; this BN loader did not resolve them later. The payload now materializes every pinned parent field, changing only ID, looks_like and examine handler. The full source comparison prevents drift. This avoids load-order dependencies and leaves the global loader unchanged. Native rerun is pending.
