# Camp engine boundary

Verified against official DDA c19e95bc96d27d8bef8e2e246a63cd4cd6f89974 and BN c621aaf42fa182473aad10feea2b55647704dcf1.

DDA overmap_special.cpp reads `camp` and `camp_name`. During placement, overmap_special_fixed.cpp rotates the cell coordinate, converts it to an absolute overmap coordinate and forces z=0. It calls map::add_camp, retrieves the actual camp from overmap_buffer, assigns its faction and translated name, then calls define_camp with `faction_base_bare_bones_NPC_camp_0`. Failed lookup emits a diagnostic; it does not fabricate a replacement.

BN's pinned src/overmap/overmap.cpp has no corresponding camp registration fields or calls. This requires restoring the camp object, map registration, overmap persistence/cache access and the NPC camp definition, rather than merely loading camp metadata. Keep the prison camp at its original cell [0,1,0], owned by prisoners, named Holdouts.

The native patch now preserves `limited_area_claim` in faction templates, refreshing a faction from its template and save/load. Absent legacy-save fields reset it to false. A save round-trip regression covers true and the legacy reset. This is data compatibility only: territory/ownership consumers and camp behavior are still pending.

Food model compatibility remains unresolved. DDA factions load timestamped calorie/vitamin stocks through fac_food_supply; BN requires an integer food_supply and interprets that integer in population-day calculations. Do not replace the source vitamin ledger with an invented scalar. The original prison faction data remains intact in staging, which is not yet ready for a native full-package load.
