# Windows run 39063548662 startup diagnosis

The executable compiled successfully. The completed job log shows JSON startup errors followed by a fatal error during overmap-special placement; the job eventually reached its 180-minute limit. This was not evidence that the test suite was still making progress.

Fixed in the current source:

- Karting cash groups used unsupported root `container-item`. They now use standard BN container items with `contents-group` wrappers. Farm packages use the same corrected translation.
- Two karting parking cells referenced missing `s_lot_no_sidewalk_south`. BN provides `s_lot` with `NO_ROTATE`; both cells now use that exact concrete ID. The old invalid ID caused the fatal error while rotating/placing the special. A static guard now checks every concrete karting/farm placement reference against BN definitions and inherited rotation flags (45 cells).
- The XEDRA field retained unsupported `concentration`, and its intensity-3 emitter exceeded the one-level BN field definition. Three identical BN visual levels now preserve the source emitter intensity, without the unsupported property.

The earlier fix already added test durations and 20-minute step limits. Native data loading, generation and installed-package validation must succeed on the corrected revision before claiming a playable build. Fast Python CI alone does not establish that result.


## Windows run 39077993956: test compilation

The build stopped while compiling dda_radio_stations_test.cpp. Pinned BN item_contents exposes all_items_top() and num_item_stacks(), rather than range iteration and size(). Map item stacks yield item pointers. Adapted the container and corpse assertions to those interfaces and dereferenced the pointers. Patch application was checked against the pinned source. Native execution and installed-package validation remain pending the next Windows run.


## Windows run 39120054313: loading farm and eldercare support

The game and tests compiled successfully. Native execution then reported the DDA-only overmap field `travel_cost_type: roof` in the farm shop and aborted on the web field's intensity array `[1, 3]`. The farm adapter removes only that unsupported roof category, retaining BN's inherited overmap behavior and all source geometry. The mapgen field action now uses existing BN `jmapgen_int` loading and per-placement sampling, so scalar/default intensities remain unchanged and source ranges need no fixed-value substitution. Both changes are included in the composed mapgen patch and guarded by Python checks. The next Windows run must confirm startup and native/installed tests.
