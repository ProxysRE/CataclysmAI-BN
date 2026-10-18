# BN terminal records

Six read-only computer story graphs from the pinned DDA nursing home and retirement community are adapted to BN's existing computer security and uilist menus. All 72 original page texts, response labels, response order and destination IDs are retained. Back links and cycles are supported. Long records are folded and paginated; leaving an archive returns to the computer menu.

The source nursing-home legal-document link has no page definition. Its only added page says `ERROR: File unavailable.` and allows logoff. No legal story text is invented. The six source EOCs do nothing except open dialogue; the adapter rejects changes to that assumption and rejects non-string text or effect-bearing responses rather than silently discarding behavior.

`computer_archive.h` stores and validates records. Computer options carry an optional archive root; ordinary BN actions retain their existing dispatch and security checks. Archive options cannot also perform another computer action. Mapgen validates roots and links before copying records into a computer. Computer saves preserve records and option roots. Loading old JSON or legacy saves clears the new state and keeps ordinary behavior.

`data/json/dda_terminal_archives.json` contains six one-cell nested templates. They are reusable support definitions and native test fixtures, not world-spawned locations. The adapted eldercare candidate maps now contain these working terminal configurations; the whole sites still require their remaining dependencies and generation testing before installation.

The four modified BN source files are bundled with checksums and the pinned BN commit. The DDA story provenance remains in `regional_locations/`. The mapgen change is composed with the corpse-placement patch so both use one reviewed diff against pinned BN.

Checks: `check_terminal_archives.py`, `check_eldercare.py`, `check_native_patch_sources.py`, and `check_windows_package.py`. Native Catch tests cover source graph loading, save round trips, old-save defaults, exits, cycles, duplicate IDs, missing links and mixed-action rejection. The Windows workflow runs them before and after installation. Compilation and runtime remain unverified until that workflow passes; interactive pagination also needs an in-game visual check.
