# Rural church block: ordinary church and XEDRA investigation

## Native ordinary rural church

The patch adds a complete new DDA location: parking, main church, basement, steeple and steeple roof, spanning z=-1..2. All four source mapgen layouts and the five source placement records are preserved. Both basement stair connections are retained; steeple access aligns exactly. A real computer object uses BN's existing `toll` action. Natural generation follows the original ordinary church occurrence, distance and road-connection rules; the redundant legacy terrain connection member is removed for BN strict loading.

Existing BN church locations and global palettes are unchanged. The DDA church palette bindings used by this building are inlined into its deferred mapgen. No palette is registered from a root-level payload before BN terrain/furniture factories load. BN's existing cathedral palette supplies basement furniture and loot; this intentionally uses BN supplies and food rules, rather than silently replacing the global cathedral palette with DDA's newer item groups. DDA's original cathedral palette is preserved for review in the source bundle.

Adaptations: DDA white wooden wall -> existing BN white wall (`t_wall_w`); soil -> `t_dirt`; scoped linoleum colour in both fill_ter and terrain bindings -> the source's explicit gray fallback; new OMT vision labels -> BN numeric see_cost 2. These are compatibility choices, not claims that the two terrain systems behave identically.

Native tests cover ground/upper and ground/basement stairs and the actual bell computer object. Local geometry, preservation and packaging checks passed; Windows native execution, natural placement, bell activation and player traversal remain pending. The fast workflow also scans the complete pinned BN JSON tree for typed ID collisions and missing terrain, furniture, item group, vehicle group and monster group dependencies.

## XEDRA rural church

The complete source maps, placement, field-agent worn group and equipment dependency review are staged, not installed. The preserved source comprises the fortified parking/camp, paranormal church interior, basement, steeple and roof. No NPC or mission definition is present in these two mapgen sources; the field agent in this scene is a corpse and equipment group.

Eighteen available-source equipment definitions and 162 reference edges are retained, including both powered suit states, casual suit transforms and glowing string. The review distinguishes unresolved typed references from proven absences in BN. It is not a complete dependency closure.

Blocking work remains: the glowing mass's ranged pull and grab strength, twisting-mass dust field, powered multi-subtype armor and immunity semantics, remaining corpse/battery/mask dependencies, and review of the source tent chunk versus BN's existing chunk. The DDA placement policy of 20..100 occurrences plus GLOBALLY_UNIQUE also needs a BN-specific review. None of these mechanics is replaced by a generic monster, inert protective suit or empty corpse.

Source pins and byte checksums are in SOURCE_MANIFEST.json. Raw shared files are preserved as compressed parts; preparation scripts import only selected definitions. Run check_rural_churches.py to reconstruct and verify the package.

BN already has a RANGED_PULL action, but it has range 3 and damage-based pull distance, while this DDA monster requests range 5 and a weight-ratio pull. BN_RANGED_PULL_REVIEW.json preserves the pinned native function and exact differences. The existing BN implementation is the reuse candidate; a direct action-name substitution would change gameplay. The source dust field is also preserved: short-lived luminous particles with no explicit damage effects.

Update: xedra_creature now prepares the actual creature, exact source field/emitter and inert string for the native build. Configurable BN ranged pull replaces the earlier fixed-range limitation. Windows validation is pending; grab lifecycle/AI differences and protective equipment are still explicit blockers for enabling the complete XEDRA location. See ../xedra_creature/README.md.

Activity suit normal/casual states now have a BN-native adaptation in ../xedra_gear. The powered respirator and S02a suit remain staged.

Windows run 39052531145 compiled successfully but failed data initialization: eager root palette bindings, unconverted basement fill_ter parameter and a deprecated terrain road-connection member. All three have prepared fixes and regression checks; Windows revalidation is pending.
