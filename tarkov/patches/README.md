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
