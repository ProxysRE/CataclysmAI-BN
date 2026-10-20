#!/usr/bin/env python3
"""Separate initial Godco geometry from quest-driven construction and content."""
import argparse,copy,json
from collections import Counter
from prepare_geometry_layer import ROOT,OUT,prepare as prepare_shells
from prepare_community_layers import read_bundle,ROOT as COMMUNITY_ROOT
from prepare_container_yards import required
from prepare_regional_locations import index_entries,BUILTIN_IDS
from compare_location_catalog import read_sources
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mods_cache
from audit_hub_access import matrix


def prepare(check=False):
    prepare_shells(check=True)
    source=json.loads((OUT/'SHELLS.json').read_text())['godco_base']
    utility_aliases={n:'dda_geo_godco_'+n for n in ('roof_4x4_utility','roof_4x4_utility_1')}
    def rename_utility(v):
        if isinstance(v,str):return utility_aliases.get(v,v)
        if isinstance(v,list):return [rename_utility(x)for x in v]
        if isinstance(v,dict):return {k:rename_utility(x)for k,x in v.items()}
        return v
    entries=rename_utility(copy.deepcopy(source));deferred=[]
    for e in entries:
        if e['type']=='overmap_terrain':
            for k in ('travel_cost_type',):
                if k in e:deferred.append({'ids':e['id'],'field':k,'value':e.pop(k)})
        if e['type']=='overmap_special' and 'priority'in e:
            deferred.append({'id':e['id'],'field':'priority','value':e.pop('priority')})
        if e['type']=='mapgen' and 'om_terrain'in e:
            if e['object'].get('predecessor_mapgen')=='forest':
                e['object']['remove_all']={c:{}for c,t in e['object']['terrain'].items()if t!='t_null'}
            slots=matrix(e);assert len(e['object']['rows'])==24*len(slots)
            assert all(len(row)==24*len(slots[0])for row in e['object']['rows'])
    catalog,_=read_sources();agri='bn/data/json/overmap/overmap_terrain/overmap_terrain_agricultural.json'
    declared=json.loads(catalog[agri])
    road=next(e for e in declared if e.get('id')=='rural_road_forest')
    parent=next(e for e in declared if e.get('abstract')==road['copy-from'])
    assert not {'LINEAR','NO_ROTATE'}&set(parent.get('flags',[])) and 'copy-from'not in parent
    for e in entries:
        if e['type']=='overmap_special':
            for cell in e['overmaps']:
                if cell.get('overmap')=='rural_road_forest_ns':cell['overmap']='rural_road_forest_north'
    generated={('overmap_terrain','rural_road_forest_north')}
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    own=index_entries(entries);missing=required(entries)-own-core-generated
    assert not missing,sorted(missing)
    bundle=read_bundle(COMMUNITY_ROOT)
    updates=json.loads(bundle['dda/data/json/mapgen/godco/mapgen_updates.json'])
    nested=json.loads(bundle['dda/data/json/mapgen/godco/nested.json'])
    constructions=[];vertical=[]
    for e in nested:
        o=e['object'];name=e['nested_mapgen_id']
        structural=bool(o.get('terrain')) or any(x.get('point')=='terrain'or x.get('line')=='terrain'or x.get('square')=='terrain'for x in o.get('set',[]))
        furniture=o.get('furniture',{})
        constructions.append({'id':name,'has_explicit_terrain_geometry':structural,'furniture_requires_separate_review':furniture,'source_fields':list(o)})
        for p in o.get('place_nested',[]):
            if p.get('z',0):vertical.append({'source':name,'placement':p,'status':'blocked_by_BN_2D_nested_placement'})
    assert len(vertical)==3
    assert {v['source']for v in vertical}=={'darryl_coop','eddie_food_storage','godco_permanent_trader_predatory'}
    for a,b in zip(source,entries):
        if a['type']=='mapgen':
            expected=rename_utility(a['object'])
            if expected.get('predecessor_mapgen')=='forest':expected['remove_all']={c:{}for c,t in expected['terrain'].items()if t!='t_null'}
            assert expected==b['object']
    mods={(r['type'],r['id'])for r in mods_cache()['records']}
    report={'status':'initial_geometry_candidate_not_installed','native_embedded':False,'runtime_validated':False,
      'definitions':dict(Counter(e['type']for e in entries)),'world_maps':sum(e['type']=='mapgen' and 'om_terrain'in e for e in entries),'structural_nested_maps':sum(e['type']=='mapgen' and 'nested_mapgen_id'in e for e in entries), 'own_omt':len([n for t,n in own if t=='overmap_terrain']),
      'placed_cells':sum('overmap'in c for e in entries if e['type']=='overmap_special'for c in e['overmaps']),
      'constraint_records':sum('overmap'not in c for e in entries if e['type']=='overmap_special'for c in e['overmaps']),
      'unresolved_typed_refs':sorted(missing),'schema_fields_deferred':deferred,
      'entry_path_clearing':'BN remove_all only on non-null terrain glyphs; untouched predecessor forest retained',
      'road_counterpart':{'source_id':'rural_road_forest_ns','target_id':'rural_road_forest_north','reason':'BN rural road is regular rotatable terrain, not LINEAR; north retains the vertical dirt-road orientation'},
      'generated_BN_terrain':{'id':'rural_road_forest_north','source_file':agri,'declaration':road,'parent':parent},
      'shared_utility_aliases':utility_aliases,
      'core_id_overlaps':sorted((own-BUILTIN_IDS)&core),'bundled_mod_id_overlaps':sorted((own-BUILTIN_IDS)&mods),
      'construction_scope':{'update_definitions':len(updates),'updates':[{'id':e.get('update_mapgen_id'),'source_fields':list(e['object']),'nested_placements':e['object'].get('place_nested',[])}for e in updates],'nested_definitions':len(nested),'nested_review':constructions,'cross_z_blockers':vertical,'all_updates_and_nested_retained_in_authenticated_bundle':True},
      'remaining':['Native initial-site loading and generation','Separate terrain geometry from structural furniture in construction chunks','Adapt all three cross-z roofs before enabling related quest updates','Later-layer population/loot/furniture/quest mechanics remain deferred'],
      'limits':['Initial site only; not all later quest-built structures','Two shared roof utility terrain layouts are retained; overlay furniture glyphs become f_null while preserving underlying roof terrain and source rows','No existing BN or bundled mod location overwritten']}
    for name,value in [('GODCO_ADAPTED_BASE.json',entries),('GODCO_GEOMETRY_REPORT.json',report)]:
        text=json.dumps(value,indent=2,ensure_ascii=True)+'\n';p=OUT/name
        if check:assert p.read_text()==text,p
        else:p.write_text(text)
    print('Godco initial geometry: five maps; typed closure and source dimensions verified; three future construction roof blockers retained')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
