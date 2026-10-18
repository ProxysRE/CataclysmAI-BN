# Eldercare creature layer

Pinned DDA c19e95bc96d27d8bef8e2e246a63cd4cd6f89974 adapted against BN c621aaf42fa182473aad10feea2b55647704dcf1. SOURCE_MANIFEST.json authenticates the archived original definitions and relevant BN loaders. Build with prepare_eldercare_fauna.py; check with check_eldercare_fauna.py.

Sixteen definitions: eight monsters, two weapon groups, one outfit group, four monster groups and one web emitter. No native AI changes. These definitions support the staged nursing-home/retirement maps; neither complete location is enabled by this layer.

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


## Cellar-spider extension

The two unique cellar spiders inherit the existing BN cellar spider, retaining its faction, material, harvest and basic behavior. The mother keeps source speed 85, aggression -15, morale 10, removes HARDTOSHOOT and adds STUMBLES. Source death spell death_spider_cellar_mom summons 3..8 spiders within radius 2 from GROUP_SPIDER_MOM_SUMMON (67/33 source age variants). Under the approved counterpart policy those age variants both use BN's immature cellar spider. The existing BN on_death/spawn_mon_near hook releases six immature spiders within radius 2. Six is a fixed approximation, not the original random range or age mix. No new engine death handler or magic dependency is introduced.

The warehouse spider resolves source proportional values to hp 420, volume 542500 ml, weight 203750 g, speed 120 and attack cost 120. Source armor and melee skill/dice are preserved on the existing BN spider body. BN GRAB and a supported adjacent bite with stock poison replace conditional grab/drag chains and the newer painful-venom effect. DDA limb weakpoints, maiming-triggered leg detachment spells and corpse cocoons remain unsupported; no placeholder IDs are installed for them.

GROUP_SPIDER_BASEMENT preserves all five entries, weights, default, source age windows and total 90; days are converted to numeric BN hours (24 per day). Existing BN MONSTER_UPGRADE_FACTOR still scales these windows at load time. Inactive weight goes to the source's juvenile fallback, following BN selection semantics. BN requires turn strictly after starts and before ends; exact boundary turns are therefore subject to existing BN rules. Before the first eligible window, only the fallback is returned. Complete-site generation remains disabled.

New native tests exercise actual maternal death spawning on an empty passable map and early/late group selection. These tests must still pass source and installed Windows runs; their presence is not runtime validation.
