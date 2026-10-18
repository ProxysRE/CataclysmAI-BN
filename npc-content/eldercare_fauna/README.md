# Eldercare creature layer

Pinned DDA c19e95bc96d27d8bef8e2e246a63cd4cd6f89974 adapted against BN c621aaf42fa182473aad10feea2b55647704dcf1. SOURCE_MANIFEST.json authenticates the archived original definitions and relevant BN loaders. Build with prepare_eldercare_fauna.py; check with check_eldercare_fauna.py.

Thirteen definitions: six monsters, two weapon groups, one outfit group, three monster groups and one web emitter. No native AI changes. These definitions support the staged nursing-home/retirement maps; neither complete location is enabled by this layer.

| DDA role | BN implementation | Material differences |
| --- | --- | --- |
| Feral police officer | Existing pipe-feral AI, stock tonfa weapon group, police drops | No whistle or DDA weapon/parry actors; no inherited rock ammunition/throw attack |
| Feral spear survivor | Same BN weapon mechanism, stock knife spear, adapted source outfit | Weapon is dropped by BN separately; outfit excludes the original additional weapon draw. DDA reach/disarm behavior is not reproduced |
| Antlered mutant | Source health, speed, size, armor; adjacent gore actor and BN SMASH | SMASH approximates the source hoof knockback |
| Arthropod mutant | Source profile; adjacent stinger with standard BN poison, bite, grab and web emitter | No ranged stinger or organic-target condition; webs emitted periodically rather than source conditional spinneret |
| Camouflaged mutant | Source profile, BN camouflage flags, leap and bite | Source anatomy/weakpoints/dissection and newer AI systems omitted |
| Shelled mutant | Source slow, armored profile; BN pull, grab and tentacle attacks, slime trail | BN attack reach/timing and slime intensity differ; no source multi-stage drag chains or corpse cocoon |
| Juvenile cockroach | Stock giant cockroach nymph | Stock BN dimensions and statistics |
| Small cellar spider | Stock immature giant cellar spider | Stock BN dimensions and statistics |

GROUP_FERAL, GROUP_MUTANT_EVOLVED and GROUP_NURSING_HOME_LAB preserve source entry order, weights, pack sizes and cost multipliers, translating weight to freq. These three tables have no nested group or timed entries. Explicit freq_total retains source sums, including the evolved group's default-weight entry. Missing source default uses the highest-weight member; no arbitrary unrelated fallback. Existing medical zombies reuse BN nurses under WORK_POLICY.md.

Source damage arrays and armor are translated to supported BN fields; inherited experimental-mutant damage is explicitly replaced. DDA heat armor becomes BN fire armor. Newer mind/eating flags, anatomy, proficiencies, dissection and resurrection chains are not claimed as supported. Unique mutant upgrades are disabled so the inherited experimental-mutant evolution cannot overwrite their identity.

Validation: Python source/profile, schema, weights, identifier closure, collision and weapon-drop guards; embedded native loading/attack/weapon-group/spawn tests and installed package equality/rejection checks. Full Windows and installed native checks remain gates, not local evidence of runtime correctness. Manual combat balance and full-site generation remain pending.
