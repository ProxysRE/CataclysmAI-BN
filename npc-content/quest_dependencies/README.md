# Typed quest-item dependencies

Roots: broken_kord, kord, casket74mag, 545_ap and nano_fabricator_encryption_code.

QUEST_ITEM_GRAPH.json contains 37 typed source definitions and 62 reference edges. No unresolved references remain among the fields handled by this resolver. The source archive is checksum-verified; BN_REFERENCE_SNAPSHOT.json records exact definitions from BN c621aaf42fa182473aad10feea2b55647704dcf1 and their source paths. Support definitions still require schema-specific review, as listed in the graph. This is not a complete package dependency audit.

Item, ASCII-art, material, flag, ammo type and item-category namespaces remain separate. Display text and pocket enum values are not guessed as references. NULL ammo is an enum sentinel. Parent items and magazine restrictions are traversed explicitly. Duplicate definitions in a namespace fail rather than choosing silently.

The two USB definitions are now included in the native patch with ordinary BN
item inheritance; see `USB_NATIVE_PORT.md`. Their native runtime check is pending.
The remainder of the graph is still prepared source data.

Run python quest_dependency_graph.py --output quest_dependencies and python check_quest_dependency_graph.py. ITEM_SCHEMA_REVIEW.json describes class inheritance and the remaining schema checks for each item. Source variants and pocket fields remain preserved. Only the separately generated USB slice is included in the native patch; its Windows validation is pending. Native variant/pocket/schema support and real item/mission loading must pass before release.
