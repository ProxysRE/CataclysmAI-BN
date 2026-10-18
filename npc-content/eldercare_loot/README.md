# Eldercare loot and pigeon lifecycle

This slice adds eleven native support definitions and closes the last five missing identifier references in the staged eldercare graph. It does not enable the complete nursing home or retirement community. The remaining 25 source candidates are creature and spawn-group definitions requiring BN AI/schema adaptation and complete generation testing. Existing native pond/web support is now counted as provided, avoiding duplicate definitions in a future location assembly.

## Staff possessions and clothing

The scientist personal-effects collection retains every source occurrence probability and the source order. Ordinary medication uses stock BN inhalers, eye drops, stimulants and other medicine, including its native dosage and packaging. Source prescription ranges become 1–10 charges of the matching BN medicine; no prescription EOCs or new drug system are introduced. BN eye drops substitute for the absent steroid variant. Phones use BN's `phones` group; memory cards and contacts use existing BN items. The scientist-wallet chance produces BN cash and science ID cards, without new banknotes, coins or wallet mechanics.

The absent identification lanyard is a wearable BN armor item retaining source identity, mass and volume. It contributes 150 ml to BN's normal clothing storage with zero encumbrance. BN does not gain a DDA pocket: card-shape restrictions, separate neck subparts, pocket weight limits and manual per-pocket storage are not implemented or claimed. Its existing BN armor flags are checked against the pinned identifier catalog.

Nursing-home clothes retain both source clothing distributions and the 50% slipper chance. Stock BN shirts and jeans are reused. Two DDA-only visual variant selectors are omitted; no duplicate striped-shirt or flag-pants items are created.

## Cigars and spear-feral drops

Opened cigar boxes use an existing BN medium cardboard box rather than adding a wooden container. BN cigars have five charges per normal stack; the source 0–25 individual cigars become 0–25 charges, not 25 full stacks. The existing box has enough space for the cigar supply, two sheets of paper and an optional pair of stock scissors. Scissors replace the absent cutter/punch at the original combined 50% chance. The source dedicated-tool identity and wooden-box material are adapted; no new smoking system is needed. Packaging uses the already reviewed BN `contents-group` mechanism.

Spear-feral drops retain the source collection, nested alternatives and probabilities. BN survivor clothing groups, loaded ballistic vest, limb guards, spear sling and common ammunition replace the absent variants. DDA damage arrays become BN `damage-min`/`damage-max`. These drops do not install the associated feral creature or its weapon attacks yet.

## Mutation ingredients

The refrigerator retains its source entry count, occurrence probabilities and quantity ranges. Twenty-two DDA-specific specimen items become inputs to the corresponding pinned BN mutation recipes. Each mapping is recorded in `PORT_REPORT.json` and checked against actual recipe components. Examples include fish, feathers, chitin, reptile scutes, animal blood concentrate and carrots. Unsupported animal categories use the nearest existing BN branch, rather than adding DDA's global specimen/mutation chemistry. Several specimen types therefore yield the same BN ingredient independently.

Liquid concentrate quantities use charges so they cannot become repeated full stacks. Shared meats, fats, eggs and water remain stock BN items. This is a functional BN laboratory refrigerator, with intentionally different biological sample identities and recipe mechanics.

## Pigeons

A new pigeon and squab reuse BN's crow and crow-chick implementations, retaining BN flight, animal AI, feeding and calendar behavior. Source adult identity, reproduction count (three eggs), reproduction timer (32) and chick growth time (ten days) are preserved through supported BN fields. Pigeon eggs inherit BN chicken-egg behavior with source-derived size/nutrition and nine-day spoilage. Their dedicated hatch group yields pigeon squabs, which mature into pigeons. No existing BN crow, chicken, egg group or global wildlife population is modified.

## Validation

Python guards check all new references and native-payload collisions, all 22 recipe mappings, staff/clothing probabilities, cargo-safe cigar quantities and the complete pigeon reference cycle. Full Windows preflight compares archived BN files against the pinned checkout. Native tests sample real generated loot, verify container volumes and lanyard storage, and inspect loaded bird reproduction, hatch-group results and growth targets. Package verification rejects missing or altered loot data.

Passing these static guards is not a runtime result. Windows compilation and tests before/after installation, actual egg hatching over time, and full-site generation remain pending for this slice.
