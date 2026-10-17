# Connected eldercare locations

The nursing home and Shady Hills retirement community are still **non-installed location candidates**. Their complete source maps remain in `regional_locations/`. The retirement candidate now includes all 13 computer topics and both dialogue-opening EOCs, alongside the nursing home's existing 59 topics and four EOCs. Story links, messages and corporate-project clues are preserved from the pinned DDA sources.

`SOURCE_CANDIDATES.json` collects 42 additional definitions reached from both sites: inhabitants, civilian and medical evolution groups, clothing/drop groups and nested mapgen. These are preserved source definitions, not a schema-compatible mod. The report exposes 43 remaining references under its stated scan scope. Matching BN IDs are marked for semantic review; they are not proof of equivalent behavior. Attack implementations, every item field and runtime compatibility are outside this graph's coverage.

The pinned nursing-home source contains a response to `COMP_NURSING_HOME_LEGAL` without defining that topic. This remains an explicit source defect. No invented legal page has been added. Computer `eocs`/`open_dialogue` still need an actual BN terminal interaction bridge before either site's story can work in game.

The original medical chain remains archived for provenance. Under the user policy of 2026-10-18, the adapted locations use the stock BN medical zombie (`mon_zombie_nurse`) with its own attacks, loot and nurse/surgeon evolution, rather than importing DDA's separate medical progression. Recursive living-civilian groups, timed disappearance and unmatched mutation branches still require adaptation. Do not flatten nested groups by multiplying weights without accounting for default spawns, pack sizes and time conditions.

## Native support included in the patch

Only two independently closed definitions are installed in `data/json/dda_eldercare_support.json`:

- `GROUP_STOCKED_POND`: source fish weights, conditions, costs and pack ranges translated to BN's `name`/`freq` schema, with an explicit total of 345 and DDA's inferred rainbow-trout fallback. It reuses four stock BN fish species and BN spawn behavior. A native test draws valid species and pack sizes at four times of day. It does not port DDA fish statistics or population ecology.
- `spider_webs`: the exact source one-cell nested web field, using BN's existing field action, with a JSON method declaration. Data loading is tested by the native suite; actual retirement-community field placement awaits site integration.

These support records do not enable the locations. Their Windows compilation and runtime results must be checked separately from the passing Python guards. Portable packaging rejects missing or altered support data.

Run `prepare_eldercare.py --check` and `check_eldercare.py`. Full-checkout verification uses `--bn-source`; fast CI verifies new support IDs and references against the complete pinned BN JSON with `--bn-data`. Sources are bundled with pins and SHA256 checksums; no new currency is introduced.

## Counterpart review

`ADAPTED_LOCATIONS.json` contains both complete locations and their revised dependency layer. Fifteen explicit mappings in `bn_counterparts.py` reuse BN medical zombies, exercise equipment, lockers, clothing, soil and household loot. This reduces the selected source dependency definitions from 42 to 30 and unresolved references from 43 to 27 in the documented graph. All map rows and computer story definitions remain unchanged. The raw source layer is preserved separately and is not a requirement to implement superseded variants. Neither whole site is installed yet.
