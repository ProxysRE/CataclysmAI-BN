#!/usr/bin/env python3
"""Guard full-site geometry and references beyond the earlier dependency slice."""
import copy
import json
from prepare_eldercare_maps import ROOT, FOLDER, SITES, payloads, geometry, schema_refs, candidate_lua, LUA_MARKER, prepare
from prepare_civilians import mod_sources

prepare(check=True)
source = json.loads((ROOT / 'eldercare/ADAPTED_LOCATIONS.json').read_text())['locations']
payload = payloads()
report = json.loads((ROOT / 'eldercare/MAP_ADAPTATION_REPORT.json').read_text())
assert report['installed'] is False and report['activation_ready'] is False
sh=next(e for e in payload['nursing_home'] if e.get('id')=='nursing_home_sh')
assert 'GLOBALLY_UNIQUE' in sh['flags'] and 'UNIQUE' not in sh['flags']
assert len(sum(payload.values(), [])) == 71
assert sum(e['type']=='mapgen' for es in payload.values() for e in es) == 32
assert sum(r['geometry']['mapgen_tiles'] for r in report['sites'].values()) == 190
assert sum(len(r['geometry']['constraint_only_cells']) for r in report['sites'].values()) == 3
for site in SITES:
    assert len(source[site]) == len(payload[site])
    for before, after in zip(source[site], payload[site]):
        assert before['type'] == after['type']
        if before['type'] == 'mapgen':
            # Preserve every floor/roof/basement row, map position, random
            # wall parameter and terminal story graph through conversion.
            for key in ('rows','parameters','place_computers','mapgensize'):
                assert before['object'].get(key) == after['object'].get(key), (site,key)
            # Shared palette repair may add source solar chunks to the local nested map.
            for key,value in before['object'].get('nested',{}).items():
                assert after['object']['nested'][key]==value
            for key in ('om_terrain','nested_mapgen_id'):
                assert before.get(key) == after.get(key)
        if before['type']=='overmap_special':
            assert [c['point'] for c in before['overmaps']] == [c['point'] for c in after['overmaps']]
            assert before.get('occurrences') == after.get('occurrences')
            assert before.get('city_distance') == after.get('city_distance')
            assert [c['point'] for c in before['connections']] == [c['point'] for c in after['connections']]
    altered=copy.deepcopy(payload[site])
    special=next(e for e in altered if e['type']=='overmap_special')
    special['overmaps'].append(copy.deepcopy(special['overmaps'][0]))
    try: geometry(altered)
    except AssertionError: pass
    else: raise AssertionError('Duplicate special coordinate accepted')
    altered=copy.deepcopy(payload[site])
    mapped=next(e for e in altered if e['type']=='mapgen' and 'rows' in e['object'])
    mapped['object']['rows'][0]+=' '
    try: geometry(altered)
    except AssertionError: pass
    else: raise AssertionError('Invalid multi-OMT geometry accepted')
# Each previously uncovered typed position must surface its missing provider.
for field, kind, value in (
    ('parameters','terrain',{'wall':{'type':'ter_str_id','default':{'distribution':[['missing_wall',1]]}}}),
    ('liquids','item',{'x':{'liquid':'missing_liquid','amount':1}}),
    ('place_loot','item_group',[{'group':'missing_loot','x':1,'y':1,'chance':100}]),
    ('monster','MONSTER',{'x':{'monster':'missing_person','chance':100}})):
    refs=schema_refs([{'type':'mapgen','object':{field:value}}])
    target={'terrain':'missing_wall','item':'missing_liquid','item_group':'missing_loot','MONSTER':'missing_person'}[kind]
    assert (kind,target) in refs,(field,refs)
assert ('overmap_terrain_abstract','missing_parent') in schema_refs([{'type':'overmap_terrain','copy-from':'missing_parent'}])
from prepare_civilians import lua_payload
original=lua_payload().replace(LUA_MARKER,'',1)
lua=candidate_lua()
assert lua.count(LUA_MARKER)==1 and lua.replace(LUA_MARKER,'',1)==original
assert 'OtMatchType.CONTAINS, omt_pos' in original
assert lua.index('for _, prefix in ipairs(NPC_TERRAINS)') < lua.index('local size = map:get_map_size()')
for entries in payload.values():
    for e in entries:
        if e['type']=='overmap_terrain':
            assert all(n.startswith(SITES) for n in (e['id'] if isinstance(e['id'],list) else [e['id']]))
# Population exclusions must ship atomically with the complete optional maps.
from prepare_civilians import patch_sections
assert 'nursing_home' in patch_sections() and 'retirement_community' in patch_sections()
print('PASS: 71 full-site declarations / 32 mapgen definitions / 190 custom OMT tiles; source geometry/parameters/stories preserved; extended reference and rotation guards; three frontage constraints retained for native bridge validation')

# Source-shared glyphs that BN palettes do not define must be explicit locally.
from bn_shared_palettes import repair, native_support, sources as palette_sources
assert repair({'rows':['v1'],'palettes':['roof_palette']})['terrain']['v']=='t_ladder_down'
assert repair({'rows':['v1'],'palettes':['roof_palette']})['nested']['1']['chunks']==[['residential_6kW_solar',31],['residential_7kW_solar',63],['residential_8kW_solar',31],['null',873]]
assert repair({'rows':['<'],'palettes':['sewers']})['terrain']['<']=='t_ladder_up'
assert repair({'rows':['v'],'palettes':['roof_palette'],'terrain':{'v':'t_ladder_up'}})['terrain']['v']=='t_ladder_up'
original_solar=[e for e in palette_sources()['dda/nested_chunks_roof.json'] if e.get('nested_mapgen_id','').startswith(('residential_6kW_solar','residential_7kW_solar','residential_8kW_solar'))]
import copy
expected_solar=copy.deepcopy(original_solar)
for e in expected_solar:
    obj=e['object']
    if 'ERASE_ITEMS_BEFORE_PLACING_TERRAIN' in obj.get('flags',[]):
        obj['flags'].remove('ERASE_ITEMS_BEFORE_PLACING_TERRAIN')
        if not obj['flags']:obj.pop('flags')
        obj['remove_all']={glyph:{} for glyph in obj['terrain']}
assert [{k:v for k,v in e.items() if k!='method'} for e in native_support()]==expected_solar
assert sum('remove_all' in e['object'] for e in native_support())==4
print('PASS: shared roof/sewer glyph repair, native BN solar hardware, exact nine source nested chunks and spawn weights')
