#!/usr/bin/env python3
"""Adapt the complete yard infrastructure without enabling unfinished cargo."""
import argparse
import base64
import copy
import gzip
import hashlib
import json
from collections import Counter
from prepare_container_yards import ROOT, FOLDER, candidate, required
from prepare_regional_locations import index_entries, BUILTIN_IDS
from prepare_farm_supply import adapt_drop
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache, added_core_declarations
from bn_counterparts import MAPPINGS

ALIASES={
 ('furniture','f_display_freezer'):('f_glass_freezer_off','Stock BN display freezer, initially switched off; BN grid interaction and capacity.'),
 ('furniture','f_display_fridge'):('f_glass_fridge_off','Stock BN display refrigerator, initially switched off.'),
 ('furniture','f_glass_fridge_double'):('f_glass_fridge_off','Stock BN glass refrigerator; use its capacity rather than a new double-door appliance.'),
 ('furniture','f_heavy_duty_freezer'):('f_freezer_industrial_off','Stock BN industrial freezer, initially switched off.'),
 ('furniture','f_heavy_duty_fridge'):('f_fridge_off','Stock BN refrigerator; industrial size and power draw are approximated.'),
 ('furniture','f_training_dummy_light'):('f_punching_bag','Stock BN unarmed-training interaction; no DDA weapon-specific training pseudo-items.'),
 ('furniture','f_training_dummy_heavy'):('f_punching_bag','Stock BN unarmed-training interaction; no separate armored dummy.'),
 ('furniture','f_archery_target_bale'):('f_target','Stock BN shooting target; steel ballistic behavior replaces soft hay.'),
 ('furniture','f_archery_target_box'):('f_target','Stock BN shooting target; steel ballistic behavior replaces a soft cardboard target.'),
 ('furniture','f_exam_chair'):('f_chair','Stock BN seat; medical appearance and fixed overhead lamp are approximated.'),
 ('furniture','f_portable_stove'):('f_woodstove','Stock BN contained-fire stove and cooking interaction; not a foldable item.'),
 ('furniture','f_vending_c_off'):('f_vending_c','Stock closed BN vending cabinet, including its ordinary access rules.'),
 ('furniture','f_water_heater_family'):('f_water_heater','Stock BN water tank and keg interaction; stock capacity.'),
 ('item_group','SUS_fridge_partial_empty'):('SUS_fridge','Stock BN household refrigerator supplies; source sparsity is approximated.'),
 ('vehicle','forklift_vehicles'):('forklift','Stock BN forklift prototype; source map chance and orientation retained.'),
}
# Reuse previously source-reviewed approximate counterparts as well.
for key in [('furniture','f_ergometer_mechanical'),('furniture','f_treadmill_mechanical'),('item_group','SUS_trash_trashcan')]:
    ALIASES[key]=MAPPINGS[key]


def support_sources():
    m=json.loads((FOLDER/'SUPPORT_SOURCE_MANIFEST.json').read_text())
    assert m['pins']=={'bn':'c621aaf42fa182473aad10feea2b55647704dcf1','dda':'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'}
    raw=gzip.decompress(base64.b64decode(''.join((FOLDER/p).read_text() for p in m['parts']),validate=True))
    assert hashlib.sha256(raw).hexdigest()==m['bundle_sha256']
    files=json.loads(raw);assert set(files)==set(m['files'])
    for p,s in files.items():
        b=s.encode();r=m['files'][p]
        assert hashlib.sha256(b).hexdigest()==r['sha256']
        assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['blob_sha']
    return {p:json.loads(s) for p,s in files.items()}


def support_data():
    files=support_sources()
    wallpath='data/json/furniture_and_terrain/terrain-walls.json'
    walls=files['dda/'+wallpath]
    assert any(e.get('id')=='t_wall_metal' for e in files['bn/'+wallpath])
    result=[]
    for original in walls:
        n=original.get('id','')
        if n=='t_wall_metal_corrugated' or n.startswith('t_wall_metal_shipping_container'):
            e=copy.deepcopy(original)
            if n in ('t_wall_metal_corrugated','t_wall_metal_shipping_container'):
                # Keep BN's metal-wall mechanics and its supported cutting API.
                e={'type':'terrain','id':n,'copy-from':'t_wall_metal',
                   'name':e['name'],'description':e['description'],'symbol':'#','color':e.get('color','light_gray')}
            result.append(e)
    wanted={'f_pallet_belted','f_pallet_belted_open','f_pallet_brick_adobe',
            'f_pipe_stack_short','f_pipe_stack_mid','f_plank_stack_short','f_plank_stack_mid'}
    for p,entries in files.items():
        if not p.startswith('dda/'):continue
        for original in entries:
            if original.get('id') not in wanted:continue
            e=adapt_drop(copy.deepcopy(original))
            e.pop('mass',None)  # BN uses the preserved required_str field.
            e['flags']=list(dict.fromkeys('SHORT' if f=='SMALL_HIDE' else f for f in e['flags']))
            if e.get('examine_action')=='locked_object':
                # Avoid BN crate callbacks that transform into a different crate.
                # The source pallet opens through bash; dismantling is retained.
                e['examine_action']='none'
            result.append(e)
    assert len(result)==23
    return result


def adapt():
    result=copy.deepcopy(candidate());support=support_data()
    aliases={n:v[0] for (kind,n),v in ALIASES.items()}
    def walk(v):
        if isinstance(v,str):return aliases.get(v,v)
        if isinstance(v,list):return [walk(x) for x in v]
        if isinstance(v,dict):return {k:walk(x) for k,x in v.items()}
        return v
    wrappers=[];implicit=[];clearing=[]
    for i,original in enumerate(result):
        e=walk(original);result[i]=e
        if e['type']=='mapgen':
            obj=e['object']
            if 'ALLOW_TERRAIN_UNDER_OTHER_DATA' in obj.get('flags',[]):
                # BN already retains underlying objects unless the new terrain
                # is a wall or explicit ERASE_ALL is requested.
                obj['flags'].remove('ALLOW_TERRAIN_UNDER_OTHER_DATA')
                if not obj['flags']:obj.pop('flags')
                clearing.append(e.get('nested_mapgen_id',e.get('om_terrain')))
            if 'rows' not in obj and obj.get('mapgensize')==[1,1] and any(k in obj for k in ('furniture','item','items','monsters')):
                # DDA accepts an implicit one-cell palette. BN only applies
                # glyph mappings when rows is present; t_null is a no-op.
                obj['rows']=[' '];obj.setdefault('terrain',{})[' ']='t_null'
                implicit.append(e['nested_mapgen_id'])
            for glyph,value in list(obj.get('furniture',{}).items()):
                choices=value if isinstance(value,list) else [[value,1]]
                if not any(isinstance(v,list) and v[0]=='f_diesel_generator' for v in choices):continue
                # A furniture/vehicle weighted mixture needs one nested choice
                # per source outcome, keeping all weights (including empty).
                del obj['furniture'][glyph]
                chunks=[]
                for j,(name,weight) in enumerate(choices):
                    if name=='f_diesel_generator':chunk='dda_eldercare_generator_diesel'
                    elif name=='f_null':chunk='null'
                    else:
                        chunk=f'dda_container_yard_appliance_{len(wrappers):02d}'
                        wrappers.append({'type':'mapgen','method':'json','nested_mapgen_id':chunk,
                                         'object':{'mapgensize':[1,1],'rows':[' '],
                                                   'terrain':{' ':'t_null'},'furniture':{' ':name}}})
                    chunks.append([chunk,weight])
                assert glyph not in obj.get('nested',{})
                obj.setdefault('nested',{})[glyph]={'chunks':chunks}
        elif e['type']=='overmap_terrain':
            e.pop('vision_levels',None);assert e['see_cost']=='medium';e['see_cost']=2
    result+=wrappers
    return result,support,{'implicit_one_cell_rows_added':implicit,'native_default_clearing_used':clearing,'generator_furniture_to_nested':True,'appliance_wrappers':len(wrappers)}


def prepare(check=False):
    payload,support,changes=adapt()
    files=support_sources()
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    port=added_core_declarations((ROOT/'artisan_engine.patch').read_text())
    own=index_entries(payload+support)-BUILTIN_IDS
    mods={(e['type'],e['id']) for e in mod_cache()['records']}
    assert not own&core and not own&mods and not own&port
    bn_furniture={e.get('id') for p,entries in files.items() if p.startswith('bn/') for e in entries if e.get('type')=='furniture'}
    for (kind,n),(target,reason) in ALIASES.items():
        assert (kind,target) in core and reason,(kind,n,target)
        if kind=='furniture':assert target in bn_furniture,target
    missing=required(payload)-core-port-own
    # Support closure includes bash/deconstruction transitions, inherited walls
    # and ordinary drop items. It never treats a different namespace as a match.
    support_refs=set()
    def refs(v):
        if isinstance(v,list):
            for x in v:refs(x)
        elif isinstance(v,dict):
            for key,kind in [('item','item'),('group','item_group'),('furn_set','furniture'),('ter_set','terrain')]:
                if isinstance(v.get(key),str):support_refs.add((kind,v[key]))
            for x in v.values():refs(x)
    for e in support:
        if 'copy-from' in e:support_refs.add((e['type'],e['copy-from']))
        refs(e)
    support_missing=support_refs-core-port-own
    assert not support_missing,sorted(support_missing)
    report={'status':'BN_infrastructure_adapted_cargo_dependencies_still_block_installation',
            'native_embedded':False,'runtime_validated':False,'definitions':dict(Counter(e['type'] for e in payload+support)),
            'support_definitions':len(support),'aliases':[{'type':k,'source':s,'target':t,'reason':r} for (k,s),(t,r) in sorted(ALIASES.items())],
            **changes,'unresolved_typed_references':sorted(missing),'unresolved_count':len(missing),
            'support_unresolved':sorted(support_missing),'core_id_overlaps':sorted(own&core),'bundled_mod_id_overlaps':sorted(own&mods),
            'remaining':['Close cargo item/group and slime dependencies with BN-safe quantities and currency',
                         'Native load/generation and complete cargo branch exercise before installation',
                         'Natural placement, all rotations, stairs, bandit population/ownership and manual traversal'],
            'differences':['Colored container walls inherit stock BN metal wall strength, cutting and salvage; source colors and per-container choice weights retained',
                           'Source sealed pallets retain bash/open and dismantle transitions; no unsupported mass or locked-object callback',
                           'Medium/short material stacks retain the source two-stage salvage amounts',
                           'Source medium vision becomes numeric BN see_cost 2; source overmap geometry unchanged'],
            'reference_scope':'Explicit typed leaves and support drops/transitions; not a full transitive schema/runtime proof'}
    for name,data in [('ADAPTED_LOCATIONS.json',payload),('SUPPORT_DEFINITIONS.json',support),('ADAPTATION_REPORT.json',report)]:
        text=json.dumps(data,indent=2,ensure_ascii=True)+'\n';path=FOLDER/name
        if check:assert path.read_text()==text,path
        else:path.write_text(text)
    print('PASS: container-yard infrastructure:',len(support),'support definitions;',len(ALIASES),'counterparts;',len(changes['implicit_one_cell_rows_added']),'one-cell cargo layouts activated;',len(missing),'remaining typed dependencies; not installed')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
