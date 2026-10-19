#!/usr/bin/env python3
"""Check complete yard geometry, per-container choices and support transitions."""
import copy
import json
from adapt_container_yards import adapt, prepare, ALIASES, support_sources, FOLDER
from prepare_container_yards import candidate, required

prepare(check=True)
payload,support,changes=adapt()
original=candidate()
maps={e.get('nested_mapgen_id'):e for e in payload if e.get('nested_mapgen_id')}
assert len(changes['implicit_one_cell_rows_added'])==119
for name in changes['implicit_one_cell_rows_added']:
    obj=maps[name]['object']
    assert obj['rows']==[' '] and obj['terrain'][' ']=='t_null'
for a,b in zip(original,payload):
    assert a['type']==b['type']
    if a['type']=='mapgen':
        for field in ('rows','place_npcs','npcs','faction_owner'):
            if field in a['object']:assert a['object'][field]==b['object'][field],field
        assert a.get('om_terrain')==b.get('om_terrain')
        assert a.get('nested_mapgen_id')==b.get('nested_mapgen_id')
        if 'parameters' in a['object']:assert a['object']['parameters']==b['object']['parameters']
    elif a['type']=='overmap_special':assert a==b
assert {n for n in maps if n.startswith('shipping_container_')}=={e['nested_mapgen_id'] for e in original if e.get('nested_mapgen_id','').startswith('shipping_container_')}
# Keep all appliance probability mass and the empty outcome when changing the
# generator branch from furniture into a functioning one-cell BN vehicle.
source=next(e for e in original if e.get('nested_mapgen_id')=='shipping_container_appliances_1x1')['object']['furniture'][' ']
chunks=maps['shipping_container_appliances_1x1']['object']['nested'][' ']['chunks']
assert [w for n,w in source]==[w for n,w in chunks]
aliases={s:t for (k,s),(t,r) in ALIASES.items()}
for (src,w),(target,weight) in zip(source,chunks):
    assert w==weight
    if src=='f_null':assert target=='null'
    elif src=='f_diesel_generator':assert target=='dda_eldercare_generator_diesel'
    else:assert maps[target]['object']['furniture'][' ']==aliases.get(src,src)
assert maps['shipping_container_diesel_generator_1x1']['object']['nested'][' ']['chunks']==[['dda_eldercare_generator_diesel',90],['null',10]]
support_by_id={e['id']:e for e in support}
assert len(support_by_id)==23
assert support_by_id['f_pallet_belted']['bash']['furn_set']=='f_pallet_belted_open'
assert support_by_id['f_pallet_belted']['examine_action']=='none'
for material in ('pipe','plank'):
    medium=support_by_id[f'f_{material}_stack_mid']
    for field in ('bash','deconstruct'):assert medium[field]['furn_set']==f'f_{material}_stack_short'
assert len([e for e in support if e['type']=='terrain'])==16
# Directional references normalize only against declarations in the payload.
assert ('overmap_terrain','container_yard_inland_base_1') in required(original)
assert ('overmap_terrain','container_yard_inland_base_1_south') not in required(original)
# Glyph-based NPCs were missed by the former scanner. The boss remains a real
# dependency, never silently replaced by an ordinary bandit.
assert ('npc','hells_raiders_boss') in required(original)
report=json.loads((FOLDER/'ADAPTATION_REPORT.json').read_text())
assert report['native_embedded'] is False and report['runtime_validated'] is False
assert report['unresolved_count']==42 and not report['support_unresolved']
assert ('item_group','banknotes') in set(map(tuple,report['unresolved_typed_references']))
print('PASS: all source cargo/geometry retained; 119 BN-explicit one-cell layouts; weighted appliance vehicles; 23 closed support declarations; NPC/currency blockers remain explicit')
