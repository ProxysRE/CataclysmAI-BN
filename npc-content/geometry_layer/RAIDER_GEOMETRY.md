# Raider sites and deserter settlement: first-layer staging

Four source locations are staged together: drug lab, bandit drug lab, bandit work camp, and deserter city. The existing pinned location audit lists these as missing/expanded groups. The output declarations have no exact identifier collisions with pinned BN core or its bundled mods; this does not claim that every structural motif is unique to DDA.

Scope: 15 complete world-map definitions, 24 own OMT and 25 placed cells. Deserter city includes gate, park, and both four-level office sections. Two authenticated shared roof utilities retain structural terrain; solar equipment and other furnishing remain deferred. Source rows and all deferred fields are preserved separately.

`prepare_raider_geometry.py --check` verifies ten official pinned source files and the existing authenticated roof archive, expands palettes and inline terrain mappings, checks dimensions/registrations and reports typed closure. The complete source city_building registration is archived verbatim; the staged shell uses a zero-occurrence special registration solely as a future debug-preview candidate. Source population, loot and quests are excluded from this layer.

The only unresolved typed terrain is `t_embrasure_wood`; it must be compared to BN embrasures or ported before embedding. Native schema, generation, actual traversal and gameplay are not yet validated. No native patch or preview files are modified, no natural world placement is enabled, and no completion credit is awarded.

## Wooden embrasure adaptation

`adapt_raider_geometry.py --check` now closes the raw terrain obligation using two complete, isolated source definitions: the intact wood embrasure and its widened opening. Coverage 90/60, movement 0/4, material flags, source bash thresholds and item quantities are retained. BN wall connectivity flags replace source connection groups; BN flat roof substitutes for the source wood roof, and dust/splinter hit/destruction field emission is deferred explicitly. Typed references close against the pinned core and bundled-mod inventories.

The adaptation is not embedded. Native schema/generation, combat cover, mounted shooting, reach attacks, fire and traversal after damage remain unverified. No completion credit is added.

## Isolated native preview

The four staged sites are now embedded in the explicit optional geometry preview. Their original OMT and special identities are namespaced; natural occurrences remain zero. The common fixture has 20 cases /638 placements. Raider navigation and embrasure positions have exact terrain expectations, while every own cell is checked for non-null terrain and absence of content loot. The widened wall state loads as a support terrain but requires separate damage/traversal/combat testing. Source and installed Windows generation are pending.
