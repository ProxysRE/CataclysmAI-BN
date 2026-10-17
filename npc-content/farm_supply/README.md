# Farm supply transfer candidate

This is a complete **non-installed candidate** for the normal and looted DDA farm stores, their common roof and fence damage. It is not embedded in the native patch and is not ready for a playable package.

The conversion preserves all 48x48 source rows and placements, including currently unsupported corpse placement. It prepares nine material/supply groups, three dismantlable construction stacks, the source wooden pallet, red industrial carpet and a one-cell damage template. Stock BN ATM terrain, electrical minifreezer behavior, food/trash groups, canvas bags, flint and native cash-register providers are reused. No new currency is introduced.

BN material charges replace source resource counts to avoid spawning thousands of full ammo stacks. The bag groups use existing 15 L canvas bags: cement 2800 charges, sand 2500, soil 3, quicklime 1200; the barrel group uses 6000 quicklime charges. These amounts still require actual container-generation tests. Dismantling and bash yields are preserved where compatible; damage ranges are converted to BN's representation and capped at 4.

Run `prepare_farm_supply.py --check` and `check_farm_supply.py`. For a full pinned BN checkout, use `prepare_farm_supply.py --check --bn-source <checkout> --audit --report <file>`. Audit mode reports missing references and collisions without pretending that dependency closure has passed. The CI artifact includes this report alongside the five-site source audit.

Before native integration, resolve all inline merchandise groups and monster groups, implement or adapt the source corpse placement using an appropriate BN mechanism, validate furniture flags/drops, then add native load, actual generation, roof and container tests. See `PORT_REPORT.json` for the exact adaptation limits. Archived DDA fridge/trash definitions are references for comparison; their expanded packaging systems are not installed by this candidate.
