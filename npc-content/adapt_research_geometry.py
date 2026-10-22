#!/usr/bin/env python3
"""Adapt physical XEDRA/LIXA shells; preserve source interactions separately."""
import argparse,copy,hashlib,json
from prepare_research_geometry import prepare as stage,SOURCE
from prepare_geometry_layer import ROOT,OUT
from prepare_regional_locations import index_entries,BUILTIN_IDS
from prepare_container_yards import required
from compare_location_catalog import read_sources
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache

def prepare(check=False):
    stage(check=True)
    m=json.loads((SOURCE/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    files={}
    for path,digest in m['files'].items():
        raw=(SOURCE/path).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,path
        files[path]=json.loads(raw)
    support=[e for e in files['data/json/furniture_and_terrain/LIXA_furniture_and_terrain.json']if e.get('type')=='terrain'or e.get('id')=='f_LIXA_unfold_barrier']
    support+= [e for e in files['data/json/mapgen/xedra_fishing_shack.json']if e.get('type')=='terrain']
    aliases={e['id']:'dda_geo_research_'+e['id']for e in support}
    counterparts={'t_carpet_concrete_green':'t_carpet_green','t_metal_roof':'t_metal_flat_roof','t_metal_roof_red':'t_metal_flat_roof','t_concrete_roof':'t_strconc_floor_no_roof','t_wall_metal_corrugated':'t_wall_metal','t_region_shrub_forest':'t_region_shrub','t_region_tree_forest':'t_region_tree','rural_road_forest_ns':'road_ns','lc_wire':'wire','mc_steel_chunk':'steel_chunk'}
    aliases.update(counterparts)
    def rename(v):
        if isinstance(v,str):return aliases.get(v,v)
        if isinstance(v,list):return [rename(x)for x in v]
        if isinstance(v,dict):return {k:rename(x)for k,x in v.items()}
        return v
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    for source,target in counterparts.items():
        if source=='rural_road_forest_ns':continue
        kind='item'if source in ('lc_wire','mc_steel_chunk')else 'terrain'
        assert (kind,target)in core,(kind,target)
    deferred=[];physical=[]
    for original in support:
        e=copy.deepcopy(original)
        for key in ('connect_groups','rotates_to','shoot','emissions','oxytorch','examine_action'):
            if key in e:deferred.append({'source':e['id'],'field':key,'value':e.pop(key)})
        if 'connects_to'in e and e['connects_to']!='WALL':
            deferred.append({'source':e['id'],'field':'connects_to','value':e.pop('connects_to')})
        if e.get('connects_to')=='WALL':
            # BN uses the wall flag for native line connection.
            e['flags']=list(dict.fromkeys(e.get('flags',[])+['CONNECT_TO_WALL']))
        if original.get('examine_action'):e['examine_action']='none'
        assert 'copy-from'not in e
        assert {'name','description','symbol','color'}<=e.keys(),e['id']
        assert ('move_cost'if e['type']=='terrain'else 'move_cost_mod')in e
        physical.append(rename(e))
    entries=rename(json.loads((OUT/'RESEARCH_SHELLS.json').read_text(encoding='utf-8')))+physical
    catalog,_=read_sources()
    road=next(e for path,text in catalog.items()if path.startswith('bn/')for e in json.loads(text)if e.get('type')=='overmap_terrain'and e.get('id')=='road')
    assert 'LINEAR'in road['flags']
    abstract=next(e for path,text in catalog.items()if path.startswith('dda/')for e in json.loads(text)if e.get('abstract')=='road_abstract')
    expanded=[]
    for e in entries:
        if e.get('copy-from')=='road_abstract':
            deferred.append({'source':e['id'],'source_overmap_abstract':abstract})
            base={k:copy.deepcopy(v)for k,v in abstract.items()if k not in ('abstract','vision_levels','travel_cost_type')}
            base.update({k:v for k,v in e.items()if k!='copy-from'})
            if isinstance(base.get('see_cost'),str):
                assert base['see_cost']=='none';base['see_cost']=0
            expanded.append(base)
        else:expanded.append(e)
    entries=expanded;own=index_entries(entries)
    for e in entries:
        if e['type']=='mapgen' and e['object'].get('predecessor_mapgen') and e['object'].get('rows'):
            e['object']['remove_all']={g:{} for g,t in e['object'].get('terrain',{}).items() if t!='t_null'}
    # looks_like is optional presentation, not a license to invent field IDs.
    for e in physical:
        key=(e['type'],e.get('looks_like',''))
        if 'looks_like'in e and key not in own|core:
            deferred.append({'source':e['id'],'field':'looks_like','value':e.pop('looks_like')})
    set_refs={(a.get('point',a.get('line',a.get('square'))),a['id'])for e in entries if e['type']=='mapgen'for a in e['object'].get('set',[])if 'id'in a}
    generated={('overmap_terrain','road_ns')}
    missing=sorted((required(entries)|set_refs)-own-core-generated)
    for e in physical:
        if e.get('roof'):assert ('terrain',e['roof'])in own|core,e['roof']
        for key in ('bash','deconstruct'):
            if key not in e:continue
            assert ('terrain',e[key]['ter_set'])in own|core|BUILTIN_IDS,e['id']
            for item in e[key].get('items',[]):assert ('item',item['item'])in core,item
    mods={(e['type'],e['id'])for e in mod_cache()['records']}
    assert not (own-BUILTIN_IDS)&(core|mods)
    assert not missing,missing
    walls={e['id']:e for e in physical}
    for source,target in [('t_lixa_wall','t_folded_wall'),('t_folded_wall','t_unfolded_wall'),('t_unfolded_wall','t_lixa_wall')]:
        assert walls[aliases[source]]['bash']['ter_set']==aliases[target]
    navigation={};furniture_points={}
    for e in entries:
        if e['type']!='mapgen' or 'om_terrain' not in e:continue
        omt=e['om_terrain'];matrix=[[omt]] if isinstance(omt,str) else [omt] if isinstance(omt[0],str) else omt
        obj=e['object'];assert obj.get('rotation',0)==0,(omt,obj.get('rotation'))
        for y,row in enumerate(obj.get('rows',[])):
            for x,g in enumerate(row):
                t=obj.get('terrain',{}).get(g)
                if isinstance(t,str) and (t.startswith('dda_geo_research_') or 'stairs' in t or 'ladder' in t):
                    navigation.setdefault(matrix[y//24][x//24],[]).append({'x':x%24,'y':y%24,'terrain':t})
        for a in obj.get('set',[]):
            if a.get('line')!='furniture' or not a['id'].startswith('dda_geo_research_'):continue
            assert a['y']==a['y2'],a
            for x in range(a['x'],a['x2']+1):
                y=a['y']
                furniture_points.setdefault(matrix[y//24][x//24],[]).append({'x':x%24,'y':y%24,'terrain':a['id'],'furniture':True})
    report={'status':'research_geometry_adapted_not_installed','native_embedded':False,'runtime_validated':False,
      'new_physical_definitions':dict(__import__('collections').Counter(e['type']for e in physical)),
      'aliases':aliases,'unresolved_typed_refs':missing,'generated_external_omt':['road_ns'],
      'navigation':navigation,'navigation_points':sum(map(len,navigation.values())),
      'structural_furniture_points':furniture_points,
      'deferred_source_fields':deferred,
      'preserved':['Source rows, special placements and ruined tent weights','LIXA wall destruction cycle with source thresholds','Source movement, coverage, flags, light and shaft markers','Source physical barrier line and XEDRA locked door geometry'],
      'adaptations':['BN green carpet replaces industrial concrete-backed carpet','BN metal flat roof replaces source metal roofs; red paint is lost; BN reinforced-concrete floor without roof supplies concrete roof geometry','BN generic metal wall replaces corrugated wall; durability differs','BN regional shrub/tree selectors replace forest-specific selectors','BN straight road replaces source forest road; surroundings differ','Source precision metal component tiers reuse BN wire/steel_chunk','DDA shooting, emissions, tools, EOC actions and unsupported display connections remain archived'],
      'remaining':['Native schema and source/installed generation','Special shafts, device access/unfolding and interactions','Combat, demolition, light and actor traversal acceptance'],
      'limits':['No native embedding or percentage credit','Shaft GOES_DOWN markers do not certify their source pseudo-ledge behavior','Reader examination disabled; ordinary science-card behavior not substituted']}
    for name,value in [('RESEARCH_ADAPTED_SHELL.json',entries),('RESEARCH_ADAPTATION_REPORT.json',report)]:
        text=json.dumps(value,indent=2,ensure_ascii=True)+'\n';p=OUT/name
        if check:assert p.read_text(encoding='utf-8')==text,p
        else:p.write_text(text,encoding='utf-8')
    print('Research physical definitions prepared; native schema and special-device behavior pending')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
