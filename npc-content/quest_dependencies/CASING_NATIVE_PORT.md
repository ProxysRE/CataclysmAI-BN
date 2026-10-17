# 5.45x39 casing and expanded weapon dependency graph

`545_casing` is included in the native patch as a BN `GENERIC` item. All source
fields are retained; only the item-schema discriminator changes. It inherits the
existing BN abstract `casing` and uses the existing `9mm_casing` visual fallback.
No stock casing, item category or material is redefined. Native loading is pending.

The baseline snapshot records the exact pinned BN casing parent, 9mm casing and
spare-parts category. Windows preflight scans all BN item files for a conflicting
5.45 casing ID and verifies both parent and visual fallback definitions.

The typed resolver now follows ammunition casings/linkage, gun faults, weapon
categories, gunmod targets and magazine adaptors. Its source graph grows from
37 definitions / 62 edges to 48 / 76. These three legacy faults are reused from existing BN data
at `items/gun/faults_gun.json`, without adding new native definitions:

- `fault_gun_blackpowder`
- `fault_gun_chamber_spent`
- `fault_gun_dirt`

The typed references now resolve against the pinned BN baseline. The other DDA
fault definitions still require schema/consumer review. The graph is not a complete item-system audit.

The live 5.45 ammo, magazines and Kord remain uninstalled. DDA-specific barrel
damage, item variants and weapon base fields are preserved for review. This slice
does not substitute 5.56 ammunition or assert equivalent ballistics.

BN reference source:
[generic/casing.json](https://github.com/cataclysmbn/Cataclysm-BN/blob/c621aaf42fa182473aad10feea2b55647704dcf1/data/json/items/generic/casing.json).
