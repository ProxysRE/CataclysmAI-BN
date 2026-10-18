# Shared 5.45 mm casing

The full bundled-mod scan found item 545_casing in pinned BN Exotic Ammo. It is exactly equal, as parsed JSON, to native/dda_545_casing.json. The port already needs this item for exhibition-related content without forcing Exotic Ammo to be enabled.

Reuse strategy: keep that unchanged BN definition as the shared core item; remove only its original declaration from data/mods/exotic_ammo/generic/casing.json. All ten other mod casing definitions remain unchanged. Existing Exotic Ammo references resolve the same ID, statistics and inheritance from core. No renamed second item and no forced optional-mod dependency.

SOURCE_MANIFEST.json authenticates the official original file; native preflight compares the pristine pinned checkout. prepare_shared_casing.py verifies exact identity and builds the removal diff. The global collision guard accepts this provider-specific promotion only if both the core payload and exact removal patch are present. Packaging validates the modified mod file and rejects stale duplicates. The existing 545 property test is tagged for both core and Civilians+Exotic Ammo source/installed runs. New native combination validation remains pending.
