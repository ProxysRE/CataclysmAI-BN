# Windows run 39063548662 startup diagnosis

The executable compiled successfully. The completed job log shows JSON startup errors followed by a fatal error during overmap-special placement; the job eventually reached its 180-minute limit. This was not evidence that the test suite was still making progress.

Fixed in the current source:

- Karting cash groups used unsupported root `container-item`. They now use standard BN container items with `contents-group` wrappers. Farm packages use the same corrected translation.
- Two karting parking cells referenced missing `s_lot_no_sidewalk_south`. BN provides `s_lot` with `NO_ROTATE`; both cells now use that exact concrete ID. The old invalid ID caused the fatal error while rotating/placing the special. A static guard now checks every concrete karting/farm placement reference against BN definitions and inherited rotation flags (45 cells).
- The XEDRA field retained unsupported `concentration`, and its intensity-3 emitter exceeded the one-level BN field definition. Three identical BN visual levels now preserve the source emitter intensity, without the unsupported property.

The earlier fix already added test durations and 20-minute step limits. Native data loading, generation and installed-package validation must succeed on the corrected revision before claiming a playable build. Fast Python CI alone does not establish that result.
