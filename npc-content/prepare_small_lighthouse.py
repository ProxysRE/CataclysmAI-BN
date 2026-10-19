#!/usr/bin/env python3
"""Port the complete small island lighthouse using reviewed BN counterparts."""
import argparse
import copy
import hashlib
import json
import unicodedata
from collections import Counter
from pathlib import Path
from prepare_regional_locations import ROOT, build, index_entries, references, BUILTIN_IDS
from prepare_eldercare_assets import adapt_map, native_data as assets
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mods_cache
from bn_loot_containers import package_groups

PAYLOAD='data/json/dda_small_lighthouse.json'
ALIASES={
 't_stone_masonry_floor':'t_rock_floor',
 't_stone_masonry_floor_balcony':'t_rock_floor_no_roof',
 't_stone_masonry_wall_whitewashed':'t_concrete_wall',
 't_metal_roof_red':'t_metal_flat_roof',
 't_wall_lighthouse_lens':'t_wall_glass',
 't_door_lighthouse_lens_c':'t_door_glass_c',
 'f_lighthouse_light':'f_grid_floodlight_off',
 'SUS_trash_floor':'floor_trash',
 'tools_workshop':'tools_common',
 'instant_coffee':'roasted_coffee_bean',
 'solid_earth':'empty_rock',
}
CROSS={'f_machinery_old':'t_machinery_old','f_machinery_electronic':'t_machinery_electronic'}


def evidence():
    result=json.loads((ROOT/'small_lighthouse/SOURCE_EVIDENCE.json').read_text())
    assert result['pins']=={'bn':'c621aaf42fa182473aad10feea2b55647704dcf1','dda':'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'}
    files={}
    for name,record in result['files'].items():
        raw=record['text'].encode()
        assert hashlib.sha256(raw).hexdigest()==record['sha256']
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==record['blob_sha']
        files[name]=json.loads(record['text'])
    for game in ('bn','dda'):
        diesel=next(e for e in files[game+'/data/json/items/fuel.json'] if e.get('id')=='diesel')
        assert diesel['volume']=='200ml' and diesel['stack_size']==200
    assert files['dda/data/json/mapgen_palettes/roof_palette.json'][0]['terrain']['v']=='t_ladder_down'
    assert 'v' not in files['bn/data/json/mapgen_palettes/roof_palette.json'][0]['terrain']
    return files


def native_data():
    evidence()
    def walk(value):
        if isinstance(value,str):return ALIASES.get(value,value)
        if isinstance(value,list):return [walk(v) for v in value]
        if isinstance(value,dict):return {k:walk(v) for k,v in value.items()}
        return value
    result=[]
    for original in build()['small_lighthouse.json']:
        e=walk(copy.deepcopy(original))
        if e['type']=='mapgen':
            e=adapt_map(e)
            e['method']='json'
            o=e['object']
            for glyph, f in list(o.get('furniture',{}).items()):
                if isinstance(f,str) and f in CROSS:
                    del o['furniture'][glyph]
                    o.setdefault('terrain',{})[glyph]=CROSS[f]
            if any('v' in row for row in o['rows']):
                o['terrain']['v']='t_ladder_down'
        elif e['type']=='overmap_terrain':
            assert e.pop('copy-from')=='lighthouse_abstract'
            e.update(sym='0',color='yellow',see_cost=5)
        result.append(e)
    return package_groups(result)


def prepare(check=False):
    payload=native_data()
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    own=index_entries(payload)-BUILTIN_IDS
    refs=set()
    for e in payload:
        if e['type']=='mapgen':refs.update(references(e['object']))
        elif e['type']=='item_group':refs.update(references({'items':{'_':{'item':e}}}))
        elif e['type']=='overmap_special':
            refs.update(('overmap_location',loc) for loc in e.get('locations',[]))
            for cell in e['overmaps']:
                refs.update(('overmap_location',loc) for loc in cell.get('locations',[]))
                name=cell.get('overmap','')
                if name.endswith('_north'):name=name[:-6]
                refs.add(('overmap_terrain',name))
    missing=refs-core-own-index_entries(assets())
    assert not missing,sorted(missing)
    assert not own&core,sorted(own&core)
    mod_ids={(r['type'],r['id']) for r in mods_cache()['records']}
    assert not own&mod_ids,sorted(own&mod_ids)
    maps=[e for e in payload if e['type']=='mapgen']
    assert len(maps)==6
    for e in maps:
        rows=e['object']['rows']
        assert len(rows)==24
        assert {sum(not unicodedata.combining(c) for c in row) for row in rows}=={24}
    report={'native_embedded':True,'runtime_validated':False,'definitions':dict(Counter(e['type'] for e in payload)),
            'levels':[0,1,2,3,4,5],'aliases':ALIASES,'furniture_to_terrain':CROSS,
            'unresolved_refs':sorted(missing),'source_rows_preserved':True,
            'generator_reuse':'Existing four BN generator vehicle/nested assemblies; source weights retained',
            'roof_palette_fix':'DDA v explicitly binds t_ladder_down; stock BN roof palette has no v binding',
            'intentional_differences':['BN rock floors and concrete walls replace DDA masonry; appearance, destruction and loot follow BN',
              'BN glass walls/doors replace optical lens pieces; DDA lens-specific shard yields are not reproduced',
              'BN grid floodlight starts off; power supply, switching and brightness use BN behavior; no rotating beacon simulation is claimed',
              'Red metal roof uses stock metal roof; BN tools/refuse groups retain BN contents',
              'Source diesel 0..50000 charges retained: both games use 200 charges per 200 ml',
              'Instant coffee uses existing BN roasted coffee beans: dry coffee supply, different preparation and units',
              'Submerged solid-earth foundation uses BN empty_rock; source coordinates retained, material/excavation follow BN'],
            'remaining':['Native initialization and complete generation','Lake placement/boat access and manual traversal','Grid lighting and generator operation in game']}
    for path,data in {ROOT/'native/dda_small_lighthouse.json':payload,ROOT/'small_lighthouse/ADAPTATION_REPORT.json':report}.items():
        text=json.dumps(data,indent=2,ensure_ascii=True)+'\n'
        if check:assert path.read_text()==text,path
        else:path.parent.mkdir(exist_ok=True);path.write_text(text)
    print('PASS: complete six-level island lighthouse; typed dependencies and all-mod collision review; runtime pending')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
