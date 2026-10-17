# XEDRA clothing states and respirator dependency closure

## Native activity suit

Two source identities are added as BN ARMOR items, preserving names, descriptions and both transform actions. The normal suit inherits the existing BN Hub 01 environmental suit. The casual state inherits that new suit, covers only legs and feet, and removes RAINPROOF, GAS_PROOF, RAD_PROOF and ELECTRIC_IMMUNE as the DDA casual parent does. Switching back restores full coverage/seals through the normal type.

The existing Hub suit is not changed or duplicated. Both states deliberately use its BN material, protection, storage, weight and encumbrance rules. DDA's newer Kevlar/steel/thermoplastic sub-bodypart armor model and two 250 ml pockets are preserved in the original sources, not silently claimed as implemented. This adaptation follows the established BN equipment balance; it is not DDA armor-stat parity.

Native tests convert a real item both ways, check body coverage and all four seals, and check instance variable preservation. Actual UI activation and wearing/cache behavior remain field tests. Windows compilation/runtime validation is pending. Full pinned BN item scanning rejects either ID collision, verifies the exact Hub parent and checks the existing belt/mask visual and battery reuse candidates.

## Powered respirator and S02a suit

The complete PAPR mask, blower on/off states, filter canister, filter-charge ammunition, ammunition types and battery source definitions are preserved. The typed traversal now follows tool_ammo, default magazines, ammunition default charges, transforms and native mask/blower actions, without treating pocket-local names as global item IDs.

The PAPR belt has two magazine wells, one for the battery and one for the filter. The mask only protects with an active, supplied blower and prepared mask. PAPR_MASK_ACTIVATE, PAPR_MASK and PAPR_BLOWER are native DDA consumers, not cosmetic flags. A one-ammo BN tool or renamed ordinary gas mask cannot represent this faithfully. The multi-resource item/reload/consumption bridge remains required, along with testing environmental protection on a worn mask. The powered S02a armor also retains its separate protection and immunity blockers.

These sources are staged, not installed as inert or permanently protective substitutes. The XEDRA church remains disabled until the corpse equipment and remaining behavior are implemented. Reports distinguish unresolved source references from proven missing BN definitions. Existing ordinary BN gas masks and batteries are unchanged.

Run check_xedra_gear.py for source/state validation. Shared raw files are compressed and checksummed in SOURCE.part*; only the two reviewed clothing definitions enter the native payload.
