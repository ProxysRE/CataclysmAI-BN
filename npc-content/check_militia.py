#!/usr/bin/env python3
"""Guard the first complete militia community promotion and its BN reuse."""
import copy
from collections import Counter
from prepare_militia import selected,native_data,prepare,ITEM_ALIASES,GROUP_ALIASES,ROOT
from prepare_regional_locations import expand
from prepare_civilians import lua_payload, MILITIA_EXCLUSION,mod_sources

prepare(check=True)
source,_=selected()
payload=native_data()
assert Counter(e['type'] for e in payload)=={'npc':2,'npc_class':2,'talk_topic':9,'item_group':1,'mapgen':5,'overmap_terrain':1,'overmap_special':1,'faction':1}
original_maps=[e for e in source if e['type']=='mapgen']
palettes={e['id']:e for e in source if e['type']=='palette'}
maps=[e for e in payload if e['type']=='mapgen']
for before,after in zip(original_maps,maps):
    assert before['om_terrain']==after['om_terrain']
    expanded=expand(before['object'],palettes)
    for key in ('rows','place_npcs','faction_owner'):
        assert expanded.get(key)==after['object'].get(key),key
    grid=after['om_terrain'];rows=after['object']['rows']
    assert len(rows)==24*len(grid)
    assert {len(row) for row in rows}=={len(grid[0])*24}
assert sum(len(row) for e in maps for row in e['om_terrain'])==24
sp=next(e for e in payload if e['type']=='overmap_special')
assert len(sp['overmaps'])==24 and 'GLOBALLY_UNIQUE' in sp['flags']
assert len({tuple(c['point']) for c in sp['overmaps']})==24
npcs={e['id']:e for e in payload if e['type']=='npc'}
assert npcs['MILITIA_MERCHANT']['mission']==3
assert npcs['MILITIA_GUARD1']['mission']==8
assert {e['faction'] for e in npcs.values()}=={'GM_militia_faction'}
assert not any(e['type']=='mission_definition' for e in source), 'Do not invent militia quests'
assert {e['id'] for e in source if e['type']=='talk_topic'}=={e['id'] for e in payload if e['type']=='talk_topic'}
assert lua_payload().replace(MILITIA_EXCLUSION,'',1)==mod_sources()['main.lua']
assert '"GMLODGE"' in lua_payload()
assert not {'case_cigar','goggles_chem','sneakers_steel'} & {e.get('id') for e in payload if isinstance(e.get('id'),str)}
print('PASS: two source NPC roles, nine dialogue topics, seven fixed NPC placements, five full mapgen layouts / 24 OMT cells, faction ownership and atomic Civilians exclusion; no invented missions/items')
