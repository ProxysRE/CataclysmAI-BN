# Farm supply transfer candidate

Complete **non-installed candidate** for the normal and looted DDA farm stores, their common roof and fence damage. It is not embedded in the native patch or ready for a playable package.

The conversion preserves all source 48x48 rows and explicit placements, including the source corpse placement. Twenty merchandise/material groups, three dismantlable construction stacks, six item adapters, red industrial carpet and a one-cell damage template are prepared. See `PORT_REPORT.json` for the detailed differences from DDA.

Stock BN ATM terrain, electrical minifreezers, camping gear, food/trash groups, common ammunition, steel wire, cloth, glues, batteries and cash-register providers are reused. The three source rock items use BN rock/armor-independent item mechanics; the riding helmet and rotary tool use the existing BN bicycle-helmet and angle-grinder models. These are candidates requiring native behavior checks. No new currency is introduced.

BN material charges replace source resource counts to avoid thousands of full ammo stacks. Supply groups use existing 15 L canvas bags and the source quantities; battery packets use stock cells at their actual 50/100/500 capacities in a stock 3 L box. Dismantling and bash yields are retained where compatible, with damage converted to BN's representation and capped at 4. Runtime container-generation tests are still required.

Run `prepare_farm_supply.py --check` and `check_farm_supply.py`. For a complete pinned BN checkout, use `prepare_farm_supply.py --check --bn-source <checkout> --audit --report <file>`. Audit mode reports unresolved references without claiming dependency closure. CI also checks the full BN identifier cache in `dependency_catalog/`.

The remaining direct reference is `helmet_bike_modified`: DDA uses an armor pocket/container for optional chin guard and visor. An ordinary BN helmet cannot receive those as container contents. The native patch now registers `place_corpses` and palette `corpses`, using BN corpse items and monster groups. `CORPSE_SOURCE_REVIEW.json` records the source comparison; native tests cover species, age/clamping and null groups. Windows runtime results are pending. Resolve modular armor, validate new item/furniture behavior, and add native load, actual generation and roof tests before enabling the site.
