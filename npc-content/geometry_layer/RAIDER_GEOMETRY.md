# Raider sites and deserter settlement: first-layer staging

Four source locations are staged together: drug lab, bandit drug lab, bandit work camp, and deserter city. The existing pinned location audit lists these as missing/expanded groups. The output declarations have no exact identifier collisions with pinned BN core or its bundled mods; this does not claim that every structural motif is unique to DDA.

Scope: 15 complete world-map definitions, 24 own OMT and 25 placed cells. Deserter city includes gate, park, and both four-level office sections. Two authenticated shared roof utilities retain structural terrain; solar equipment and other furnishing remain deferred. Source rows and all deferred fields are preserved separately.

`prepare_raider_geometry.py --check` verifies ten official pinned source files and the existing authenticated roof archive, expands palettes and inline terrain mappings, checks dimensions/registrations and reports typed closure. The complete source city_building registration is archived verbatim; the staged shell uses a zero-occurrence special registration solely as a future debug-preview candidate. Source population, loot and quests are excluded from this layer.

The only unresolved typed terrain is `t_embrasure_wood`; it must be compared to BN embrasures or ported before embedding. Native schema, generation, actual traversal and gameplay are not yet validated. No native patch or preview files are modified, no natural world placement is enabled, and no completion credit is awarded.
