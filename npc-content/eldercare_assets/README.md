# Eldercare infrastructure and laboratory records

This slice adds 33 support definitions to `data/json/dda_eldercare_assets.json` and connects them to the staged nursing-home and retirement-community maps. It does not enable either whole location. Static dependency closure is separate from schema, creature AI, generation and runtime validation.

## Reused BN objects

| DDA reference | BN adaptation |
| --- | --- |
| Family water heater | Stock `f_water_heater`, including its keg interaction and BN capacity |
| Pedestrian crossing | Stock marked pavement `t_pavement_y`; appearance follows BN |
| Glassless barred window | Stock transparent metal bars `t_bars` |
| Hardware refuse | Stock `hardware_trash` |
| Feral police loot | Stock `mon_zombie_cop_death_drops`; BN police equipment and probabilities |
| Furniture consoles | Stock `t_console` / `t_console_broken` terrain at the same glyph positions |
| Low hedge furniture | Stock shrub terrain, with BN movement and plant behavior |
| Saline sizes | The stock BN saline item in its normal small bottle; no DDA infusion/EOC subsystem |

The medical cart uses BN's wheeled vehicle table, which already provides a 20 L cargo surface and workbench. A second cargo box is deliberately omitted because it would compete with the table at the same mount. The small hospital bed uses BN bed, frame and wheel parts. Both retain the one-cell DDA footprint; replacing the small bed with BN's two-cell hospital bed would intrude on adjacent room tiles.

The cargo van reuses BN's camper-van hull with six cargo bays and normal BN driving parts. Its occupied coordinates match DDA's cargo van. The existing BN cube van is wider, so blindly aliasing it would risk blocking the source parking layout. Driver/passenger equipment, body parts and powertrain remain BN implementations. Loot uses a BN car kit and source road-map chance; DDA heater/cooler systems are not imported.

## Backup power and walls

Source generator choices remain 25 broken : 5 diesel : 5 military diesel : 5 gasoline. Broken machines use stock BN generator terrain. Each working alternative is a compact one-cell vehicle built from stock BN frame, fuel tank, storage battery, engine, 7.5 kW generator and electronic controls. These are usable BN machines with ordinary vehicle fuel, damage and cable behavior, not decorative copies of appliances. Their output and storage use BN values rather than DDA's generator ratings; installation, starting and connection in the actual location still need runtime verification. This slice does not automatically wire a location-wide power grid.

The wall palette is inlined into the deferred mapgen to avoid BN's eager palette-ID resolution. Existing BN mapgen parameters retain per-special wall selection, source material choices, all weights, fallbacks and graffiti odds. Missing wall paint colors use BN's white wall or the same unpainted structural material. Source map rows and special placement are unchanged.

## Laboratory and household loot

Four source groups are retained: common and rare mutation books, hoarder clutter and laboratory files. All mutation recipe books already exist in BN, so their native recipes and mechanics are reused with the exact source selection weights. Hoarder clutter uses existing BN household groups. No new currency or denominations are added.

Nine laboratory notes/protocols inherit BN's verified `survnote` paper template, keeping its literacy requirement and snippet rendering. All 60 associated DDA text records, text IDs and category assignments are preserved exactly. They contain no EOC-driven interactions. These are new readable objects because their original documents are absent in BN, rather than substitutes that discard their story content.

## Checks and remaining scope

`check_eldercare_assets.py` checks footprints, generator odds, wall weights, exact laboratory prose and BN identifier closure. Full source preflight checks archived BN files against the pinned checkout; fast CI rejects snippet-category collisions against all pinned BN snippets. Native tests cover actual vehicle-part installation, generated readable notes, laboratory loot, recipe books and packaged saline. Package verification rejects missing or altered asset data.

The staged dependency graph has five unresolved references: pigeon eggs, scientist personal effects, opened cigar boxes, spear-feral drops and mutagen-ingredient refrigerator loot. That is an identifier count under the documented graph scope, not five remaining tasks until playability: the staged civilian/mutation branches, schemas and complete world generation still require adaptation. Windows compilation, native/installed tests and in-game interaction remain pending for this slice.
