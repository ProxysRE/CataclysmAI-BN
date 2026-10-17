# Demilled Kord quest prop

`broken_kord` is projected to a normal BN `GENERIC` item. Its ID, description,
materials, mission/trade/repair flags, mass and volume remain from the source.
It does not acquire gun slots, ammo or firing behavior. Native validation is pending.

The source has exactly one presentation variant with the same ID. The adapter uses
that variant's model name, retaining the base name and complete variant object in
`QUEST_PROP_PORT_REPORT.json`. Multiple variants or variant fields other than
ID/name/description are rejected. BN does not gain DDA's gun-name option.

The source item length is retained in the report. BN continues to use its existing
volume model; no DDA length/pocket behavior is claimed. The tile fallback changes
from the not-yet-ported Kord to the existing BN AKM (`ak47`), without redefining
that weapon. Price `2 kUSD 500 USD` becomes the equivalent `2500 USD`.

Source behavior was checked in pinned DDA
[item.cpp](https://github.com/CleverRaven/Cataclysm-DDA/blob/c19e95bc96d27d8bef8e2e246a63cd4cd6f89974/src/item.cpp):
`select_itype_variant` selects a weighted variant on construction, while variant
name visibility depends on `SHOW_GUN_VARIANTS`. This is an explicit fixed-name
projection for BN, not an implementation of the variant subsystem.

The full BN item catalog is checked before patch application: a conflicting
`broken_kord` ID stops the build, and the stock rifle fallback must exist. A native
test checks that the prop is not a firearm and satisfies stock item conditions.

Three legacy gun fault references resolve to actual existing BN fault definitions
in `data/json/items/gun/faults_gun.json`. They are not installed a second time.
`check_reused_bn_definitions.py` verifies every selected BN support definition by
namespace, ID and complete JSON content, preventing a same-named item from being
mistaken for a fault or other support type.

The working Kord, live ammunition and magazines remain outside the native payload.
Its DDA mechanical-fault, barrel-damage and pocket data still require adaptation.
