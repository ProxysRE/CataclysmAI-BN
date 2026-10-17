# Farm supply store port

The complete normal and looted 2x2 shops, shared 2x2 roof and nested fence destruction are embedded as `native/dda_farm_supply.json` in the engine patch. **Windows loading, generation and installed-package results remain pending.** `CANDIDATE.json` is the identical generated review copy, not a separate mod to install.

All 48x48 source rows, corpse placement, ladders, road connections and damage layouts are preserved. The port supplies 20 merchandise/material groups, nine internal packaging helpers, three dismantlable construction stacks, three distinct new items (pallet, heavy anvil rock and rotary tool), and a one-cell bash template. BN ATM banking, powered minifreezers, food, tools, ammunition, glues, wire, batteries and money are reused.

Under the 2026-10-18 counterpart policy, riding/modular bike helmet loot uses stock `helmet_bike`; flaking rock/flint use stock `rock`; red industrial carpet uses existing industrial carpet. Source modular attachments remain archived, but are no longer required implementations for this shop. BN item properties remain intact.

BN does not read root `container-item` on item groups. Each packaged group now creates a guaranteed container with `contents-group` referencing a separate contents definition. This packs the entire selected set together. The same correction applies to karting cash registers. Resource amounts use charges instead of repeated full stacks. Stock food volumes were checked: 50 cattle-fodder portions x 250 ml and 60 bird-food portions x 50 ml each fit a 15 L sack.

The rotary tool uses the BN angle-grinder battery model, six source quality levels and 175000 mW draw. The heavy rock retains anvil quality. Stack drops retain source quantities with BN damage bounds. See `PORT_REPORT.json` for differences.

Native tests cover eight ground quadrants, roofs, ladders, the looted-shop corpse, actual packaging/capacity, cement charges and tool qualities/power. Packaging rejects altered or missing farm data. Python checks do not replace native runtime results.

Run `prepare_farm_supply.py --check`, `check_farm_supply.py` and `bn_loot_containers.py`. For a full pinned checkout, `prepare_farm_supply.py --check --bn-source <checkout> --report <file>` strictly checks direct references and collisions. Pins, source archives and the full BN ID cache remain authoritative.
