# First native quest-item dependency slice

Two definitions are included in the native patch at
`data/json/items/dda_quest_usb.json`:

- `usb_drive_nano`, inheriting the existing BN `usb_drive`;
- `nano_fabricator_encryption_code`, inheriting `usb_drive_nano`.

The only source-schema change is DDA `ITEM` to BN `GENERIC`. Every other source
field is preserved. Both definitions have no pockets, variants or new use action.
Their ordinary item properties, inventory behavior, condition checks and saving
are handled by BN's existing item system.

Before the patch is applied, Windows CI scans the entire pinned BN core item
directory for both new IDs and checks the original USB parent against the reviewed
snapshot. An existing ID requires merging and stops the build. The native test
checks inherited weight/volume and the stock `u_has_item` condition: an ordinary
USB does not count as the licensing USB.

The archive verifier also requires these exact installed definitions. Local
conversion, preflight guard fixtures and archive tests pass. Actual full-catalog
preflight and native loading are pending the new Windows run.

The remaining exhibition weapon dependencies are not installed by this slice.
In particular, pinned BN lacks the DDA 5.45x39 files. Kord requires a proper ammo,
magazine and gun-data adaptation, including DDA barrel damage and variant data.
Those source fields remain preserved in the graph rather than silently discarded.
