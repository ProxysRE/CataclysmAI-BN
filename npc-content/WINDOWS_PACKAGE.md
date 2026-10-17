# Portable NPC development build

After compilation and native tests pass, the Windows workflow runs BN's own
`cmake --install` rules into an isolated `CBN_DDA_NPC_DEV` directory. It then runs
the native NPC tests again with that directory as the current working directory,
using a separate temporary user directory.

`package_windows_npc.py` verifies the installed Windows executable, Russian
translations, graphics/shader directories, the exact lighthouse payload and the
reviewed chemist map. It does not assemble the game's data with a separate copy
list. The archive receives an explicit scope/readme and a build manifest containing
the source commit, patch checksum and file checksums.

The workflow uploads `CBN-DDA-NPC-Windows-x64`, containing the portable ZIP and its
SHA256 checksum, only after the preceding checks succeed. Artifact retention is
30 days. This artifact is an experimental playable package, not a certification
of the entire quest campaign. Most staged DDA communities and the separate highway
branch are not part of its installed payload.

The packaging path itself has local archive/provenance and rejection tests. Its
first real Windows install/test/archive run is pending; no download artifact is
claimed until that run succeeds.
