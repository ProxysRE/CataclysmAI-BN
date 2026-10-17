# Existing-location expansion

The source bundle preserves 25 pinned BN/DDA files with SHA256 and Git blob identities. `prepare_location_expansion.py` reconstructs reproducible replacements; `check_location_expansion.py --bn-source <checkout>` rejects source drift before applying the native patch.

## Nuclear station: a BN location, not a new import

The nine main floor layouts (-1 through +7) have identical row geometry. BN deliberately uses its own grid generators and train. The native patch adds only the 24 DDA river-bank cells at x=2..13, y=8..9, z=0. It retains all 684 existing special cells, road connections, occurrence limits, flags, palettes and mapgen. The result has 708 cells. DDA-only hazmat roof IDs and constraint-only placements are deferred, not invented or dropped without a record. The report includes semantic differences for all 12 corresponding files.

This uses stock BN rotating river terrain and stock special generation. No new engine behavior or second nuclear special is introduced. Existing generated terrain is not rewritten. Natural generation and Windows regression for this revision are pending.

## Hub 01: complete replacement candidate, not installed

The candidate merges DDA geometry at matching coordinates, retains the existing BN special ID and generation policy, and expands 69 placements to 102. It has 33 additions and two changed placements; there are no BN-only placements in these pins. Five exact DDA mapgen/palette/terrain files accompany the candidate. They are raw source awaiting adaptation, not a runnable mod.

The new -1 level is a security foyer/control area; the source already has deeper residential, research and technical levels. NPC definitions, missing loot and furniture, elevators, stairs, schema compatibility and mapgen tests must be reconciled as one coherent package. The candidate is deliberately outside the native patch and portable installer. Its `installable` and `native_patch` markers stay false.

A source or geometry change fails the guard and requires review. The package verifier checks the installed nuclear replacement, so CMake cannot quietly ship the old special.
